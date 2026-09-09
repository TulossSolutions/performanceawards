from django.core.management.base import BaseCommand,CommandError
from django.utils.dateparse import parse_datetime
from apps.core.services import application_lock,resolve_season
from apps.rankings.services.publish import publish
from apps.scoring.models import ScoringFormula
class Command(BaseCommand):
    def add_arguments(self,p): p.add_argument("--season",required=True); p.add_argument("--cutoff",required=True); p.add_argument("--force",action="store_true")
    def handle(self,*a,**o):
        cutoff=parse_datetime(o["cutoff"])
        if not cutoff or not cutoff.tzinfo: raise CommandError("--cutoff must be an explicit timezone-aware ISO datetime")
        with application_lock("publish_rankings") as ok:
            if not ok: raise CommandError("publish_rankings is already running")
            snapshot=publish(resolve_season(o["season"]),ScoringFormula.objects.get(is_active=True),cutoff,o["force"]); self.stdout.write(self.style.SUCCESS(f"Published snapshot {snapshot.pk}"))
