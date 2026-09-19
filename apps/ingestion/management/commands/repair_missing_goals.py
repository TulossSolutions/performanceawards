from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.services import application_lock, resolve_season
from apps.football.models import Fixture, PlayerFixture, PlayerFixtureMetric


class Command(BaseCommand):
    help = "Fill missing player goals only when recorded goals reconcile with the final team score."

    def add_arguments(self, parser):
        parser.add_argument("--season", required=True)
        parser.add_argument("--apply", action="store_true", help="Write verified zero goals; otherwise preview only.")

    def handle(self, *args, **options):
        season = resolve_season(options["season"])
        verified = unresolved = 0
        pending = []
        with application_lock("repair_missing_goals") as acquired:
            if not acquired:
                raise CommandError("Goal repair is already running")
            fixtures = Fixture.objects.filter(
                provider="api_football",
                competition_season__season=season,
                status=Fixture.Status.FINISHED,
                stats_ingested_at__isnull=False,
            ).order_by("pk")
            for fixture in fixtures.iterator():
                rows = list(PlayerFixture.objects.filter(fixture=fixture).prefetch_related("metrics"))
                for team_id, score in ((fixture.home_team_id, fixture.home_score), (fixture.away_team_id, fixture.away_score)):
                    team_rows = [row for row in rows if row.team_id == team_id]
                    if not team_rows:
                        continue
                    goals = {
                        row.pk: next((metric for metric in row.metrics.all() if metric.metric_key == "goals"), None)
                        for row in team_rows
                    }
                    known = sum(
                        (metric.value for metric in goals.values() if metric and metric.is_available and metric.value is not None),
                        Decimal("0"),
                    )
                    missing = [row for row in team_rows if row.minutes > 0 and goals[row.pk] is None]
                    if score is None or any(metric and (not metric.is_available or metric.value is None) for metric in goals.values()) or known != score:
                        unresolved += len(missing)
                        continue
                    verified += len(missing)
                    pending.extend(
                        PlayerFixtureMetric(player_fixture=row, metric_key="goals", value=Decimal("0"), source_type_id="team_score_reconciled")
                        for row in missing
                    )
            if options["apply"]:
                with transaction.atomic():
                    PlayerFixtureMetric.objects.bulk_create(pending, ignore_conflicts=True, batch_size=1000)
        action = "Inserted" if options["apply"] else "Would insert"
        self.stdout.write(f"{action} {verified} verified zero-goal metrics; {unresolved} remain unresolved. No provider requests made.")
