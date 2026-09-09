from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from apps.football.models import Player,Season
class StaticSitemap(Sitemap):
    def items(self): return ["home","ranking_index","methodology","roadmap","changelog"]
    def location(self,item): return reverse(item)
class PlayerSitemap(Sitemap):
    def items(self): return Player.objects.filter(active=True).order_by("pk")
    def location(self,obj): return reverse("player_detail",args=[obj.slug])
class SeasonSitemap(Sitemap):
    def items(self): return Season.objects.filter(is_published=True).order_by("pk")
    def location(self,obj): return reverse("season_archive",args=[obj.slug])
