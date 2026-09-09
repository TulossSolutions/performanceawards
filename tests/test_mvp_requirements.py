import json
from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError
from django.test import Client, override_settings

from apps.football.models import Competition, CompetitionSeason, Fixture, PlayerFixtureMetric, Season, TeamEloSnapshot
from apps.ingestion.providers.base import ProviderFixture, ProviderFixtureBundle, ProviderMetric, ProviderParticipation, ProviderPlayer, ProviderTeam
from apps.ingestion.providers.api_football import ApiFootballProvider
from apps.ingestion.services.sync import ingest_fixture_bundle
from apps.ingestion.models import StatsBombBacktestPayload
from apps.ingestion.statsbomb import StatsBombImporter
from apps.rankings.models import RankingSnapshot
from apps.scoring.models import ScoringFormula
from apps.scoring.services.elo import rebuild_elo
from apps.scoring.services.formulas import validate_formula

pytestmark = pytest.mark.django_db

def formula_config():
    with open("scoring_formulas/v1.json", encoding="utf8") as handle: return json.load(handle)

def domain():
    season=Season.objects.create(name="2026/27",slug="test",starts_on=date(2026,8,1),ends_on=date(2027,5,31),is_current=True)
    competition=Competition.objects.create(provider="mock",provider_id="c1",name="League",slug="league",competition_type=Competition.Type.DOMESTIC_LEAGUE,is_tracked=True)
    cs=CompetitionSeason.objects.create(competition=competition,season=season,provider_season_id="s1")
    return season,cs

def bundle(goals=1):
    home=ProviderTeam("h","Home"); away=ProviderTeam("a","Away")
    fixture=ProviderFixture("f1","s1",home,away,datetime(2026,8,2,tzinfo=timezone.utc),"FINISHED",2,0)
    row=ProviderParticipation(ProviderPlayer("p1","Player One","FWD"),"h","a","FWD",True,90,(ProviderMetric("goals",Decimal(goals)),))
    return ProviderFixtureBundle(fixture,(row,),{"data":{"id":"f1","season_id":"s1"}})

def test_uniqueness_constraints():
    domain()
    with pytest.raises(IntegrityError): Season.objects.create(name="Duplicate",slug="test",starts_on=date(2026,8,1),ends_on=date(2027,5,31))

def test_only_one_current_season_validation():
    domain(); second=Season(name="Other",slug="other",starts_on=date(2027,8,1),ends_on=date(2028,5,31),is_current=True)
    with pytest.raises(ValidationError): second.full_clean()

def test_ingestion_is_idempotent_and_applies_correction():
    _,cs=domain(); ingest_fixture_bundle(bundle(1),cs); ingest_fixture_bundle(bundle(2),cs)
    assert Fixture.objects.count()==1
    assert PlayerFixtureMetric.objects.get(metric_key="goals").value==2
    assert Fixture.objects.get().playerfixture_set.count()==1

def test_failed_second_fixture_transaction_preserves_first():
    _,cs=domain(); first=bundle(1); ingest_fixture_bundle(first,cs)
    bad_row=replace(first.participations[0],opponent_id="missing")
    broken=ProviderFixtureBundle(replace(first.fixture,id="f2"),(bad_row,),{"data":{"id":"f2","season_id":"s1"}})
    with pytest.raises(KeyError): ingest_fixture_bundle(broken,cs)
    assert Fixture.objects.filter(provider_id="f1").exists()
    assert not Fixture.objects.filter(provider_id="f2").exists()

@override_settings(API_FOOTBALL_KEY="token")
def test_api_football_normalizes_known_ignores_unknown_and_preserves_zero():
    payload={"fixture":{"fixture":{"id":1,"date":"2026-08-01T12:00:00+00:00","status":{"short":"FT"}},"league":{"id":39,"season":2026,"round":"Regular Season - 1"},"teams":{"home":{"id":10,"name":"Home"},"away":{"id":20,"name":"Away"}},"goals":{"home":1,"away":0}},"players":{"response":[{"team":{"id":10},"players":[{"player":{"id":30,"name":"A Player"},"statistics":[{"games":{"minutes":90,"position":"F","substitute":False},"goals":{"total":0,"assists":None},"shots":{"total":2,"on":1},"passes":{"total":10,"key":0,"accuracy":"80%"},"unknown":{"value":7}}]}]}]}}
    result=ApiFootballProvider().normalize_fixture(payload)
    assert result.fixture.status=="FINISHED" and result.fixture.away_score==0
    assert result.participations[0].minutes==90
    metrics={x.key:x.value for x in result.participations[0].metrics}
    assert metrics["goals"]==Decimal("0") and metrics["key_passes"]==Decimal("0") and "unknown" not in metrics
    assert metrics["accurate_passes"]==Decimal("8")

def test_formula_unknown_metric_rejected():
    config=formula_config(); config["positions"]["FWD"]["metrics"][0]["key"]="invented"
    with pytest.raises(ValueError,match="Unknown metric"): validate_formula(config)

def test_published_formula_is_immutable():
    season,_=domain(); config=formula_config(); formula=ScoringFormula.objects.create(version="1.0",name="V1",config=config,checksum_sha256=validate_formula(config)); RankingSnapshot.objects.create(season=season,formula=formula,published_at=datetime.now(timezone.utc),cutoff_at=datetime(2026,9,1,tzinfo=timezone.utc),is_public=True)
    formula.config={};
    with pytest.raises(ValidationError): formula.save()

def test_elo_rebuild_is_repeatable_and_persists_pre_match_context():
    call_command("seed_demo_data",verbosity=0); season=Season.objects.get(is_current=True); rebuild_elo(season); first=list(TeamEloSnapshot.objects.order_by("fixture_id","team_id").values_list("rating_before","rating_after")); rebuild_elo(season); second=list(TeamEloSnapshot.objects.order_by("fixture_id","team_id").values_list("rating_before","rating_after"))
    assert first==second
    assert all(value is not None for value in season.competitionseason_set.first().fixture_set.first().playerfixture_set.values_list("opponent_elo_before",flat=True))

def test_winner_rises_and_loser_falls():
    call_command("seed_demo_data",verbosity=0); season=Season.objects.get(is_current=True); rebuild_elo(season)
    decisive=Fixture.objects.filter(home_score__gt=0,away_score=0).first(); rows=TeamEloSnapshot.objects.filter(fixture=decisive)
    assert any(x.rating_after>x.rating_before for x in rows) and any(x.rating_after<x.rating_before for x in rows)

def test_search_requires_two_characters_and_limits_results():
    call_command("seed_demo_data",verbosity=0); client=Client()
    assert b"Demo Player" not in client.get("/players/search/?q=D").content
    assert client.get("/players/search/?q=Demo").content.count(b"<li>")<=10

def test_methodology_reads_active_formula():
    config=formula_config(); config["positions"]["FWD"]["metrics"][0]["label"]="Verified dynamic label"
    ScoringFormula.objects.create(version="1.0",name="V1",config=config,checksum_sha256=validate_formula(config),is_active=True)
    assert b"Verified dynamic label" in Client().get("/methodology/").content

def test_ranking_cold_query_budget(django_assert_num_queries):
    call_command("seed_demo_data",verbosity=0)
    with django_assert_num_queries(15, exact=False): Client().get("/rankings/attackers/")

def test_unknown_player_and_season_are_404():
    client=Client(); assert client.get("/players/missing/").status_code==404; assert client.get("/seasons/missing/").status_code==404

def test_statsbomb_import_is_isolated_and_idempotent(tmp_path):
    data=tmp_path / "data"; data.mkdir(); (data / "competitions.json").write_text('[{"competition_id": 1}]',encoding="utf-8")
    importer=StatsBombImporter()
    assert importer.import_path(data)==1 and importer.import_path(data)==1
    assert StatsBombBacktestPayload.objects.count()==1
    assert Fixture.objects.count()==0 and RankingSnapshot.objects.count()==0
