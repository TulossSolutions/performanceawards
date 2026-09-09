from django.core.management.base import BaseCommand,CommandError
from django.utils.dateparse import parse_date
from apps.core.services import resolve_season
from apps.ingestion.providers import get_provider
from apps.ingestion.services.sync import sync_fixtures
class Command(BaseCommand):
    def add_arguments(self,p): p.add_argument("--season",required=True); p.add_argument("--from",dest="from_date",required=True); p.add_argument("--to",required=True)
    def handle(self,*a,**o):
        start,end=parse_date(o["from_date"]),parse_date(o["to"])
        if not start or not end or start>end: raise CommandError("Invalid fixture date range")
        count,failures=sync_fixtures(get_provider(),resolve_season(o["season"]),start,end)
        self.stdout.write(f"Synchronized {count} fixtures")
        if failures: raise CommandError(f"{len(failures)} fixture(s) failed: {failures[:5]}")
