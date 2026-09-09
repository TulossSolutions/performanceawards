import json
from django.conf import settings
from django.core.management.base import BaseCommand,CommandError
from django.utils import timezone
from apps.scoring.models import ScoringFormula
from apps.scoring.services.formulas import validate_formula
class Command(BaseCommand):
    def add_arguments(self,p): p.add_argument("path")
    def handle(self,*args,**opts):
        with open(opts["path"],encoding="utf-8") as f: config=json.load(f)
        if config.get("version") != settings.FORMULA_VERSION:
            raise CommandError(f"Formula version {config.get('version')} does not match FORMULA_VERSION={settings.FORMULA_VERSION}")
        checksum=validate_formula(config); existing=ScoringFormula.objects.filter(version=config["version"]).first()
        if existing:
            if existing.checksum_sha256!=checksum: raise CommandError("Formula version exists with a different checksum")
            self.stdout.write("Formula already imported with matching checksum"); return
        ScoringFormula.objects.filter(is_active=True).update(is_active=False)
        ScoringFormula.objects.create(version=config["version"],name=config.get("name",config["version"]),config=config,checksum_sha256=checksum,is_active=True,activated_at=timezone.now(),notes=config.get("notes",""))
        self.stdout.write(self.style.SUCCESS(f"Imported formula {config['version']}"))
