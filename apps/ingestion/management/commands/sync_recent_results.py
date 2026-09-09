from datetime import timedelta
from django.core.management.base import BaseCommand,CommandError
from django.utils import timezone
from apps.core.services import resolve_season
from apps.ingestion.providers import get_provider
from apps.ingestion.services.sync import sync_fixtures
from apps.ingestion.models import ProviderSyncState
class Command(BaseCommand):
    def add_arguments(self,p):
        p.add_argument("--lookback-hours",type=int,default=72)
        p.add_argument("--since-last-success",action="store_true")
    def handle(self,*a,**o):
        provider=get_provider(); season=resolve_season("current"); now=timezone.now(); end=now.date()
        state,_=ProviderSyncState.objects.get_or_create(provider=provider.provider_name,sync_key=f"recent-results:{season.slug}")
        state.last_attempt_at=now; state.last_error=""; state.save(update_fields=["last_attempt_at","last_error","updated_at"])
        start=state.last_success_at.date() if o["since_last_success"] and state.last_success_at else (now-timedelta(hours=o["lookback_hours"])).date()
        try:
            count,failures=sync_fixtures(provider,season,start,end,unseen_only=o["since_last_success"])
            if failures: raise CommandError(f"{len(failures)} fixture(s) failed")
        except Exception as exc:
            state.last_error=str(exc); state.save(update_fields=["last_error","updated_at"]); raise
        state.last_success_at=now; state.cursor=now.isoformat(); state.last_error=""; state.save(update_fields=["last_success_at","cursor","last_error","updated_at"])
        self.stdout.write(f"Synchronized {count} recent fixtures")
