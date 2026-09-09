from django.core.management.base import BaseCommand,CommandError
from apps.ingestion.providers import get_provider
from apps.ingestion.services.sync import replay_fixture
class Command(BaseCommand):
    def add_arguments(self,p): p.add_argument("provider_fixture_id")
    def handle(self,*a,**o):
        try: fixture=replay_fixture(get_provider(),o["provider_fixture_id"])
        except (ValueError,LookupError) as exc: raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Replayed fixture {fixture.provider_id} without a provider call"))
