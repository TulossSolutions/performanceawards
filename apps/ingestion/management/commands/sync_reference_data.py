from django.core.management.base import BaseCommand
from apps.core.services import resolve_season
from apps.ingestion.providers import get_provider
from apps.ingestion.services.sync import sync_reference
class Command(BaseCommand):
    def add_arguments(self,p): p.add_argument("--season",required=True)
    def handle(self,*a,**o):
        result=sync_reference(get_provider(),resolve_season(o["season"])); self.stdout.write(self.style.SUCCESS(f"Synchronized {result['competitions']} competitions, {result['teams']} teams and {result['players']} players"))
