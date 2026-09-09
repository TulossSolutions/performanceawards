from django.core.management.base import BaseCommand, CommandError

from apps.ingestion.statsbomb import StatsBombImporter


class Command(BaseCommand):
    help = "Import local StatsBomb Open Data JSON into the isolated backtesting store."

    def add_arguments(self, parser):
        parser.add_argument("--path", required=True)

    def handle(self, *args, **options):
        try:
            count = StatsBombImporter().import_path(options["path"])
        except (ValueError, OSError, UnicodeError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Imported {count} StatsBomb backtesting files"))
