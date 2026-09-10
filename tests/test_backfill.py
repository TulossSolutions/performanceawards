from datetime import date,datetime,timezone
from unittest.mock import Mock,patch
import pytest
from apps.football.models import Competition,CompetitionSeason,Fixture,Season
from apps.ingestion.providers.base import ProviderFixture,ProviderTeam
from apps.ingestion.services.sync import backfill_fixtures_chronologically

pytestmark=pytest.mark.django_db

@patch("apps.ingestion.services.sync.ingest_fixture_bundle")
def test_backfill_interleaves_competitions_chronologically(ingest):
    season=Season.objects.create(name="2024/25",slug="2024-25",starts_on=date(2024,8,1),ends_on=date(2025,5,31))
    competitions=[]
    for provider_id in ("39","140"):
        competition=Competition.objects.create(provider="api_football",provider_id=provider_id,name=f"League {provider_id}",slug=f"league-{provider_id}",country_code="ENG",is_tracked=True)
        competitions.append(CompetitionSeason.objects.create(competition=competition,season=season,provider_season_id=f"{provider_id}:2024"))
    home=ProviderTeam("1","Home"); away=ProviderTeam("2","Away")
    late=ProviderFixture("20","39:2024",home,away,datetime(2024,8,20,tzinfo=timezone.utc),Fixture.Status.FINISHED,raw_payload={"fixture":{"id":20}})
    early=ProviderFixture("10","140:2024",home,away,datetime(2024,8,10,tzinfo=timezone.utc),Fixture.Status.FINISHED,raw_payload={"fixture":{"id":10}})
    provider=Mock(provider_name="api_football")
    provider.list_fixtures.side_effect=[[late],[early]]
    provider.get_fixture_details.side_effect=lambda fixture: Mock(fixture=fixture)
    result=backfill_fixtures_chronologically(provider,season,date(2024,8,1),date(2025,5,31))
    assert [call.args[0].fixture.id for call in ingest.call_args_list] == ["10","20"]
    assert result["imported"] == 2
    assert result["remaining"] == 0
