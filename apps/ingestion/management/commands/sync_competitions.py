from django.core.management.base import BaseCommand
from django.utils.text import slugify
from apps.football.models import Competition
from apps.ingestion.providers import get_provider
class Command(BaseCommand):
    def handle(self,*a,**o):
        count=0; provider=get_provider()
        for item in provider.list_competitions():
            Competition.objects.update_or_create(provider=provider.provider_name,provider_id=item.id,defaults={"name":item.name,"slug":slugify(item.name),"country_code":item.country_code,"competition_type":item.kind}); count+=1
        self.stdout.write(self.style.SUCCESS(f"Synchronized {count} competitions; enable tracked competitions in Admin"))
