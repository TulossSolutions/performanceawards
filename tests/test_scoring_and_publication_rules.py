import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.core.management import call_command

from apps.football.models import PlayerFixtureMetric, Position, Season
from apps.rankings.models import RankingSnapshot
from apps.rankings.services.publish import publish
from apps.rankings.services.queries import latest_snapshot
from apps.scoring.models import PlayerSeasonScore, ScoringFormula
from apps.scoring.services.calculate import _aggregate, recompute_scores
from apps.scoring.services.elo import rebuild_elo
from apps.scoring.services.formulas import validate_formula

pytestmark=pytest.mark.django_db

class Metrics:
    def __init__(self,items): self.items=items
    def all(self): return self.items

def row(minutes,context,**metrics):
    items=[]
    for key,value in metrics.items():
        if isinstance(value,tuple): items.append(SimpleNamespace(metric_key=key,is_available=True,value=None,numerator=Decimal(value[0]),denominator=Decimal(value[1])))
        else: items.append(SimpleNamespace(metric_key=key,is_available=True,value=Decimal(value),numerator=None,denominator=None))
    return SimpleNamespace(minutes=minutes,context_factor=Decimal(context),metrics=Metrics(items),position=Position.FWD)

def metric(source,aggregation="COUNT_PER90",context=True): return {"source":source,"aggregation":aggregation,"context_adjust":context}

def active_formula():
    with open("scoring_formulas/v1.json",encoding="utf8") as handle: config=json.load(handle)
    return ScoringFormula.objects.create(version="1.0",name="V1",config=config,checksum_sha256=validate_formula(config),is_active=True)

def pipeline():
    call_command("seed_demo_data",verbosity=0); season=Season.objects.get(is_current=True); formula=active_formula(); cutoff=datetime(2026,9,30,23,59,59,tzinfo=timezone.utc); rebuild_elo(season); recompute_scores(season,formula,cutoff); return season,formula,cutoff

def test_positive_count_uses_context_and_per90():
    assert _aggregate([row(90,"1.10",goals=1)],metric("goals"))==Decimal("1.10")

def test_negative_count_is_not_softened_by_context():
    assert abs(_aggregate([row(90,"1.10",errors=1)],metric("errors","NEGATIVE_COUNT_PER90",False))-Decimal("1"))<Decimal("1e-20")

def test_rates_sum_numerators_and_denominators():
    rows=[row(90,"1",passes=(8,10)),row(90,"1",passes=(1,2))]
    assert _aggregate(rows,metric("passes","RATE",False))==Decimal("0.75")

def test_zero_rate_denominator_is_unavailable():
    assert _aggregate([row(90,"1",passes=(0,0))],metric("passes","RATE",False)) is None

def test_eligibility_availability_and_breakdown_are_persisted():
    season,formula,cutoff=pipeline(); scores=PlayerSeasonScore.objects.filter(season=season,formula=formula,as_of=cutoff)
    assert scores.filter(eligible=True).exists()
    assert all(Decimal("0")<=score.availability_score<=Decimal("100") for score in scores)
    assert all(abs(sum(Decimal(str(x["effective_weight"])) for x in score.metric_breakdown.values() if x["active"])-1)<Decimal(".00001") for score in scores)

def test_publication_movement_and_new_behavior():
    season,formula,cutoff=pipeline(); first=publish(season,formula,cutoff); next_cutoff=cutoff+timedelta(days=7)
    for score in PlayerSeasonScore.objects.filter(as_of=cutoff):
        score.pk=None; score.as_of=next_cutoff; score.save()
    leading=PlayerSeasonScore.objects.filter(as_of=next_cutoff,position=Position.FWD,eligible=True).order_by("final_score").first(); leading.final_score=Decimal("100"); leading.performance_score=Decimal("100"); leading.save()
    second=publish(season,formula,next_cutoff); moved=second.entries.get(player=leading.player)
    assert moved.previous_rank is not None and moved.movement==moved.previous_rank-moved.rank
    assert first.entries.count()==second.entries.count()

def test_failed_publication_leaves_no_partial_snapshot():
    season,formula,cutoff=pipeline(); PlayerSeasonScore.objects.all().delete()
    with pytest.raises(ValueError): publish(season,formula,cutoff)
    assert not RankingSnapshot.objects.filter(cutoff_at=cutoff).exists()

def test_latest_public_snapshot_selection():
    season,formula,cutoff=pipeline(); first=publish(season,formula,cutoff); later=RankingSnapshot.objects.create(season=season,formula=formula,published_at=cutoff+timedelta(days=7),cutoff_at=cutoff+timedelta(days=7),is_public=True)
    assert latest_snapshot(season)==later and latest_snapshot(season)!=first

def test_recalculation_is_deterministic():
    season,formula,cutoff=pipeline(); first=list(PlayerSeasonScore.objects.filter(as_of=cutoff).order_by("player_id").values_list("final_score",flat=True)); recompute_scores(season,formula,cutoff); second=list(PlayerSeasonScore.objects.filter(as_of=cutoff).order_by("player_id").values_list("final_score",flat=True)); assert first==second

def test_all_four_cohorts_publish():
    season,formula,cutoff=pipeline(); snapshot=publish(season,formula,cutoff); assert set(snapshot.entries.values_list("position",flat=True))=={Position.GK,Position.DEF,Position.MID,Position.FWD}

def test_first_snapshot_entries_are_new_and_order_is_deterministic():
    season,formula,cutoff=pipeline(); snapshot=publish(season,formula,cutoff); entries=list(snapshot.entries.filter(position=Position.FWD).order_by("rank"))
    assert all(x.previous_rank is None and x.movement is None for x in entries)
    assert [x.score for x in entries]==sorted([x.score for x in entries],reverse=True)

def test_low_coverage_disables_metric_and_renormalizes_weights():
    season,formula,cutoff=pipeline(); PlayerFixtureMetric.objects.filter(metric_key="goals").update(is_available=False); recompute_scores(season,formula,cutoff); score=PlayerSeasonScore.objects.filter(as_of=cutoff,position=Position.FWD).first()
    assert not score.coverage_breakdown["goals_per90"]["active"]
    assert score.metric_breakdown["goals_per90"]["effective_weight"]==0
    assert abs(sum(x["effective_weight"] for x in score.metric_breakdown.values() if x["active"])-1)<0.00001
