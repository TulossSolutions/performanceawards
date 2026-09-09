from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("ingestion", "0002_providersyncstate_created_at_and_more")]
    operations = [
        migrations.CreateModel(
            name="StatsBombBacktestPayload",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("resource_type", models.CharField(max_length=30)),
                ("source_path", models.CharField(max_length=500, unique=True)),
                ("payload", models.JSONField()),
                ("payload_sha256", models.CharField(max_length=64)),
                ("imported_at", models.DateTimeField(auto_now=True)),
            ],
            options={"indexes": [models.Index(fields=["resource_type"], name="ingestion_s_resourc_451cc7_idx")]},
        )
    ]
