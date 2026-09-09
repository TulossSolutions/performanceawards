import json
from datetime import datetime, timezone
import pytest
from django.core.management import call_command
from django.test import Client
from apps.football.models import Position, Season
from apps.scoring.models import ScoringFormula
from apps.scoring.services.calculate import recompute_scores
from apps.scoring.services.elo import rebuild_elo
from apps.rankings.services.publish import publish
from apps.scoring.services.formulas import validate_formula

pytestmark = pytest.mark.django_db

@pytest.fixture
def pipeline():
    call_command("seed_demo_data", verbosity=0)
    with open("scoring_formulas/v1.json", encoding="utf8") as handle: config = json.load(handle)
    formula = ScoringFormula.objects.create(version="1.0", name="V1", config=config, checksum_sha256=validate_formula(config), is_active=True)
    season = Season.objects.get(is_current=True)
    cutoff = datetime(2026, 9, 30, 23, 59, 59, tzinfo=timezone.utc)
    assert rebuild_elo(season) == 24
    scores = recompute_scores(season, formula, cutoff)
    return publish(season, formula, cutoff), scores

def test_full_pipeline_has_four_cohorts_and_breakdown(pipeline):
    snapshot, scores = pipeline
    snapshot.season.refresh_from_db()
    assert snapshot.season.is_published is True
    assert set(snapshot.entries.values_list("position", flat=True)) == {Position.GK, Position.DEF, Position.MID, Position.FWD}
    assert all(score.metric_breakdown for score in scores)

def test_public_pages_and_htmx(pipeline):
    client = Client()
    urls = ["/", "/rankings/attackers/", "/rankings/midfielders/", "/rankings/defenders/", "/rankings/goalkeepers/", "/players/demo-player-1/", "/compare/?a=demo-player-1&b=demo-player-2", "/methodology/", "/methodology/changelog/", "/seasons/2026-27/", "/healthz/", "/sitemap.xml"]
    assert all(client.get(url).status_code == 200 for url in urls)
    fragment = client.get("/rankings/attackers/", HTTP_HX_REQUEST="true")
    assert b"<html" not in fragment.content
    assert b'hx-push-url="true"' in fragment.content

def test_publish_is_immutable_without_force(pipeline):
    snapshot, _ = pipeline
    with pytest.raises(ValueError): publish(snapshot.season, snapshot.formula, snapshot.cutoff_at)
