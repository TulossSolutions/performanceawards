from django.core.management.base import BaseCommand,CommandError
from apps.core.services import application_lock,resolve_season
from apps.scoring.services.elo import rebuild_elo
class Command(BaseCommand):
    def add_arguments(self,p): p.add_argument("--season",required=True)
    def handle(self,*a,**o):
        with application_lock("rebuild_elo") as ok:
            if not ok: raise CommandError("rebuild_elo is already running")
            self.stdout.write(self.style.SUCCESS(f"Rebuilt Elo for {rebuild_elo(resolve_season(o['season']))} fixtures"))
