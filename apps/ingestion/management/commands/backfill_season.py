from datetime import datetime,time,timezone
from django.conf import settings
from django.core.management.base import BaseCommand,CommandError
from django.utils import timezone as django_timezone
from django.utils.dateparse import parse_date
from apps.core.services import application_lock,resolve_season
from apps.ingestion.models import ProviderSyncState
from apps.ingestion.providers import get_provider
from apps.ingestion.services.sync import backfill_fixtures_chronologically
from apps.rankings.models import RankingSnapshot
from apps.rankings.services.publish import publish
from apps.scoring.models import ScoringFormula
from apps.scoring.services.calculate import recompute_scores
from apps.scoring.services.elo import rebuild_elo

class Command(BaseCommand):
    help="Backfill one season chronologically within an explicit provider request budget."
    def add_arguments(self,p):
        p.add_argument("--season",required=True)
        p.add_argument("--from",dest="from_date",required=True)
        p.add_argument("--to",required=True)
        p.add_argument("--daily-call-budget",type=int,default=100)
        p.add_argument("--request-interval",type=float,default=settings.API_FOOTBALL_REQUEST_INTERVAL_SECONDS)
        p.add_argument("--publish-snapshot",action="store_true")
    def handle(self,*a,**o):
        start,end=parse_date(o["from_date"]),parse_date(o["to"])
        if not start or not end or start>end: raise CommandError("Invalid fixture date range")
        if o["daily_call_budget"]<1: raise CommandError("--daily-call-budget must be positive")
        provider=get_provider()
        if not hasattr(provider,"configure_request_limits"): raise CommandError("Selected provider does not support request budgets")
        provider.configure_request_limits(o["daily_call_budget"],o["request_interval"])
        season=resolve_season(o["season"]); now=django_timezone.now()
        state,_=ProviderSyncState.objects.get_or_create(provider=provider.provider_name,sync_key=f"season-backfill:{season.slug}")
        state.last_attempt_at=now; state.last_error=""; state.save(update_fields=["last_attempt_at","last_error","updated_at"])
        with application_lock("season_backfill") as ok:
            if not ok: raise CommandError("season backfill is already running")
            try:
                result=backfill_fixtures_chronologically(provider,season,start,end)
                if result["failures"]: raise CommandError(f"Fixture backfill stopped after failure: {result['failures'][0]}")
                snapshot_id=None
                if o["publish_snapshot"] and result["latest_fixture_at"]:
                    rebuild_elo(season)
                    cutoff=datetime.combine(result["latest_fixture_at"].date(),time.max,tzinfo=timezone.utc)
                    formula=ScoringFormula.objects.get(is_active=True)
                    recompute_scores(season,formula,cutoff)
                    existing=RankingSnapshot.objects.filter(season=season,formula=formula,cutoff_at=cutoff).first()
                    if not existing: snapshot_id=publish(season,formula,cutoff).pk
                state.last_success_at=django_timezone.now(); state.cursor=result["latest_fixture_at"].isoformat() if result["latest_fixture_at"] else state.cursor
                state.metadata={"imported":result["imported"],"remaining":result["remaining"],"calls_used":provider.requests_made,"quota_remaining":provider.quota_remaining,"budget_reached":result["budget_reached"],"listing_complete":result["listing_complete"],"snapshot_id":snapshot_id}
                state.last_error=""; state.save(update_fields=["last_success_at","cursor","metadata","last_error","updated_at"])
            except Exception as exc:
                state.last_error=str(exc); state.metadata={"calls_used":provider.requests_made,"quota_remaining":provider.quota_remaining}; state.save(update_fields=["last_error","metadata","updated_at"]); raise
        self.stdout.write(self.style.SUCCESS(f"Imported {result['imported']} fixtures using {provider.requests_made} calls; {result['remaining']} remain in the listed season range"))
