from contextlib import contextmanager
from django.db import connection

@contextmanager
def application_lock(name):
    if connection.vendor != "postgresql":
        yield True; return
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(hashtext(%s))",[name]); acquired=cursor.fetchone()[0]
        try: yield acquired
        finally:
            if acquired: cursor.execute("SELECT pg_advisory_unlock(hashtext(%s))",[name])

def resolve_season(value):
    from apps.football.models import Season
    return Season.objects.get(is_current=True) if value=="current" else Season.objects.get(slug=value)
