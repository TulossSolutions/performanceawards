import hashlib
import json
from pathlib import Path

from apps.ingestion.models import StatsBombBacktestPayload


class StatsBombImporter:
    resource_directories = {"matches", "events", "lineups", "three-sixty"}

    def import_path(self, data_path):
        root = Path(data_path).resolve()
        if not root.is_dir():
            raise ValueError(f"StatsBomb data directory does not exist: {root}")
        files = []
        competitions = root / "competitions.json"
        if competitions.is_file():
            files.append(("competitions", competitions))
        for resource_type in self.resource_directories:
            directory = root / resource_type
            if directory.is_dir():
                files.extend((resource_type, path) for path in directory.rglob("*.json"))
        count = 0
        for resource_type, path in sorted(files, key=lambda item: str(item[1])):
            raw = path.read_bytes()
            payload = json.loads(raw.decode("utf-8"))
            relative = path.relative_to(root).as_posix()
            StatsBombBacktestPayload.objects.update_or_create(
                source_path=relative,
                defaults={"resource_type": resource_type, "payload": payload, "payload_sha256": hashlib.sha256(raw).hexdigest()},
            )
            count += 1
        return count
