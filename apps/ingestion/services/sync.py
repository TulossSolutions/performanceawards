import hashlib
import json
import logging
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from apps.football.models import CompetitionSeason, Fixture, Player, PlayerFixture, PlayerFixtureMetric, PlayerTeamSeason, Team, TeamCompetitionSeason
from apps.ingestion.models import RawProviderPayload
from apps.ingestion.providers.positions import normalize_position

logger=logging.getLogger(__name__)

@transaction.atomic
def ingest_fixture_bundle(bundle, competition_season, provider="mock", request_path="", retain_raw=True):
    if retain_raw:
        raw=json.dumps(bundle.raw_payload,sort_keys=True,separators=(",",":"),default=str).encode()
        RawProviderPayload.objects.create(provider=provider,resource_type="fixture",provider_resource_id=bundle.fixture.id,request_path=request_path,payload=bundle.raw_payload,payload_sha256=hashlib.sha256(raw).hexdigest(),http_status=200)
    teams={}
    for data in (bundle.fixture.home_team,bundle.fixture.away_team):
        teams[data.id],_=Team.objects.update_or_create(provider=provider,provider_id=data.id,defaults={"name":data.name,"slug":slugify(data.name),"short_name":data.short_name,"country_code":data.country_code,"logo_url":data.logo_url})
    fixture,_=Fixture.objects.update_or_create(provider=provider,provider_id=bundle.fixture.id,defaults={"competition_season":competition_season,"home_team":teams[bundle.fixture.home_team.id],"away_team":teams[bundle.fixture.away_team.id],"starts_at":bundle.fixture.starts_at,"status":bundle.fixture.status,"home_score":bundle.fixture.home_score,"away_score":bundle.fixture.away_score,"stage_name":bundle.fixture.stage_name,"round_name":bundle.fixture.round_name})
    for row in bundle.participations:
        player,created=Player.objects.get_or_create(provider=provider,provider_id=row.player.id,defaults={"name":row.player.name,"slug":"","first_name":row.player.first_name,"last_name":row.player.last_name,"common_name":row.player.common_name,"birth_date":row.player.birth_date,"image_url":row.player.image_url,"height_cm":row.player.height_cm,"primary_position":normalize_position(row.position,row.player.detailed_position),"detailed_position":row.player.detailed_position})
        if not created and player.primary_position=="UNKNOWN": player.primary_position=normalize_position(row.position,row.player.detailed_position,player.primary_position); player.save(update_fields=["primary_position","updated_at"])
        participation,_=PlayerFixture.objects.update_or_create(fixture=fixture,player=player,defaults={"team":teams[row.team_id],"opponent":teams[row.opponent_id],"position":normalize_position(row.position,row.player.detailed_position,player.primary_position),"started":row.started,"minutes":row.minutes})
        for metric in row.metrics:
            PlayerFixtureMetric.objects.update_or_create(player_fixture=participation,metric_key=metric.key,defaults={"value":metric.value,"numerator":metric.numerator,"denominator":metric.denominator,"is_available":metric.available,"source_type_id":metric.source_type_id})
    fixture.stats_ingested_at=timezone.now(); fixture.save(update_fields=["stats_ingested_at","updated_at"]); return fixture

def sync_reference(provider,season):
    logger.info("reference_sync_start provider=%s season=%s",provider.provider_name,season.slug)
    count={"competitions":0,"teams":0,"players":0}
    provider_name=provider.provider_name
    for competition in season.competitionseason_set.filter(competition__is_tracked=True,competition__provider=provider_name).select_related("competition"):
        if not competition.provider_season_id:
            candidates=provider.list_seasons(competition.competition.provider_id)
            match=next((x for x in candidates if x.name==season.name or (x.starts_on==season.starts_on and x.ends_on==season.ends_on)),None)
            if not match: raise ValueError(f"No provider season matches {competition.competition.name} {season.name}")
            competition.provider_season_id=match.id; competition.save(update_fields=["provider_season_id"])
        count["competitions"]+=1
        for team_data in provider.list_teams(competition.provider_season_id):
            team,_=Team.objects.update_or_create(provider=provider_name,provider_id=team_data.id,defaults={"name":team_data.name,"slug":slugify(team_data.name),"short_name":team_data.short_name,"country_code":team_data.country_code,"logo_url":team_data.logo_url}); TeamCompetitionSeason.objects.update_or_create(team=team,competition_season=competition,defaults={"active":True}); count["teams"]+=1
            for player_data in provider.list_players(team_data.id,competition.provider_season_id):
                player,_=Player.objects.update_or_create(provider=provider_name,provider_id=player_data.id,defaults={"name":player_data.name,"first_name":player_data.first_name,"last_name":player_data.last_name,"common_name":player_data.common_name,"birth_date":player_data.birth_date,"image_url":player_data.image_url,"height_cm":player_data.height_cm,"primary_position":normalize_position(player_data.position,player_data.detailed_position),"detailed_position":player_data.detailed_position})
                PlayerTeamSeason.objects.get_or_create(player=player,team=team,season=season,competition_season=competition); count["players"]+=1
    logger.info("reference_sync_complete provider=%s season=%s counts=%s",provider.provider_name,season.slug,count); return count

def sync_fixtures(provider,season,start,end,unseen_only=False):
    logger.info("fixture_sync_start provider=%s season=%s start=%s end=%s",provider.provider_name,season.slug,start,end)
    imported=0; failures=[]; provider_name=provider.provider_name
    for competition in season.competitionseason_set.filter(is_active=True,competition__is_tracked=True,competition__provider=provider_name):
        if not competition.provider_season_id: raise ValueError(f"Missing provider season ID for {competition.competition.name}")
        for fixture in provider.list_fixtures(competition.provider_season_id,start,end):
            if fixture.status != Fixture.Status.FINISHED:
                continue
            if unseen_only and Fixture.objects.filter(provider=provider_name,provider_id=fixture.id,stats_ingested_at__isnull=False).exists():
                continue
            try:
                bundle=provider.get_fixture_details(fixture.id)
                ingest_fixture_bundle(bundle,competition,provider_name,f"fixtures/{fixture.id};fixtures/players?fixture={fixture.id}"); imported+=1
            except Exception as exc:
                logger.exception("fixture_sync_failure provider=%s fixture=%s",provider_name,fixture.id)
                failures.append((fixture.id,str(exc)))
    logger.info("fixture_sync_complete provider=%s season=%s imported=%s failures=%s",provider_name,season.slug,imported,len(failures)); return imported,failures

def replay_fixture(provider,provider_fixture_id):
    saved=RawProviderPayload.objects.filter(provider=provider.provider_name,resource_type="fixture",provider_resource_id=provider_fixture_id).order_by("-received_at").first()
    if not saved: raise ValueError("No saved fixture payload found")
    if provider.provider_name == "api_football":
        league=(saved.payload["fixture"].get("league") or {})
        season_id=f"{league['id']}:{league['season']}"
    else:
        season_id=str((saved.payload.get("data") or saved.payload)["season_id"])
    competition=CompetitionSeason.objects.get(provider_season_id=season_id,competition__provider=provider.provider_name)
    return ingest_fixture_bundle(provider.normalize_fixture(saved.payload),competition,provider.provider_name,saved.request_path,retain_raw=False)
