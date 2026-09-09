from django.contrib import admin
from .models import Competition,CompetitionSeason,Fixture,Player,PlayerFixture,PlayerFixtureMetric,PlayerTeamSeason,Season,Team,TeamCompetitionSeason,TeamEloSnapshot

@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin): list_display=("name","starts_on","ends_on","is_current","is_published"); list_filter=("is_current","is_published")
@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin): list_display=("name","provider","competition_type","is_tracked"); list_filter=("provider","competition_type","is_tracked"); list_editable=("is_tracked",); search_fields=("name","provider_id")
@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin): list_display=("name","primary_position","provider","active"); list_filter=("provider","primary_position","active"); search_fields=("name","common_name","provider_id")
@admin.register(Team)
class TeamAdmin(admin.ModelAdmin): list_display=("name","provider","active"); list_filter=("provider","active"); search_fields=("name","provider_id")
@admin.register(Fixture)
class FixtureAdmin(admin.ModelAdmin): list_display=("provider_id","home_team","away_team","starts_at","status"); list_filter=("status","competition_season__season"); search_fields=("provider_id","home_team__name","away_team__name")
admin.site.register([CompetitionSeason,TeamCompetitionSeason,PlayerTeamSeason,PlayerFixture,PlayerFixtureMetric,TeamEloSnapshot])
