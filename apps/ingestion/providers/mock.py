from datetime import date
from .base import ProviderCompetition

class MockFootballProvider:
    provider_name="mock"
    def list_competitions(self): return [ProviderCompetition("mock-league-a","Demo Premier League","GBR"),ProviderCompetition("mock-league-b","Demo Champions League",kind="UCL")]
    def list_seasons(self,competition_id): return []
    def list_teams(self,provider_season_id): return []
    def list_players(self,team_id,provider_season_id): return []
    def list_fixtures(self,provider_season_id,start:date,end:date): return []
    def get_fixture_details(self,fixture_id): raise KeyError(fixture_id)
