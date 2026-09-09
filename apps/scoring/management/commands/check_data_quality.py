from django.core.management.base import BaseCommand,CommandError
from apps.core.services import resolve_season
from apps.scoring.services.quality import check_quality
class Command(BaseCommand):
    def add_arguments(self,p): p.add_argument("--season",required=True)
    def handle(self,*a,**o):
        issues=check_quality(resolve_season(o["season"])); fatal=False
        for level,code,count in issues: self.stdout.write(f"{level} {code}: {count}"); fatal|=level=="ERROR"
        if not issues: self.stdout.write("INFO data quality checks passed")
        if fatal: raise CommandError("Fatal data-quality errors found")
