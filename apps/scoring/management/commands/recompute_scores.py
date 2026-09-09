from datetime import datetime,time,timezone
from django.core.management.base import BaseCommand,CommandError
from django.utils.dateparse import parse_date,parse_datetime
from apps.core.services import application_lock,resolve_season
from apps.scoring.models import ScoringFormula
from apps.scoring.services.calculate import recompute_scores
class Command(BaseCommand):
    def add_arguments(self,p): p.add_argument("--season",required=True); p.add_argument("--as-of",required=True)
    def handle(self,*a,**o):
        value=parse_datetime(o["as_of"]); date=parse_date(o["as_of"])
        cutoff=value or datetime.combine(date,time.max,tzinfo=timezone.utc)
        with application_lock("recompute_scores") as ok:
            if not ok: raise CommandError("recompute_scores is already running")
            formula=ScoringFormula.objects.get(is_active=True); result=recompute_scores(resolve_season(o["season"]),formula,cutoff); self.stdout.write(self.style.SUCCESS(f"Calculated {len(result)} player scores"))
