from django.conf import settings
from .api_football import ApiFootballProvider
from .mock import MockFootballProvider

def get_provider():
    if settings.FOOTBALL_PROVIDER == "api_football": return ApiFootballProvider()
    if settings.FOOTBALL_PROVIDER == "mock": return MockFootballProvider()
    raise ValueError(f"Unknown FOOTBALL_PROVIDER: {settings.FOOTBALL_PROVIDER}")
