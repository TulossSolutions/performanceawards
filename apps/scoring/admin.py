from django.contrib import admin
from .models import PlayerSeasonScore,ScoringFormula
@admin.register(ScoringFormula)
class ScoringFormulaAdmin(admin.ModelAdmin):
    list_display=("version","name","is_active","activated_at"); readonly_fields=("checksum_sha256","created_at","activated_at")
    def get_readonly_fields(self,request,obj=None): return self.readonly_fields+(("version","config","name","notes") if obj and obj.snapshots.exists() else ())
@admin.register(PlayerSeasonScore)
class PlayerSeasonScoreAdmin(admin.ModelAdmin):
    list_display=("player","position","as_of","eligible","final_score"); list_filter=("season","position","eligible","formula"); readonly_fields=("season","player","formula","position","as_of","eligible","minutes","appearances","performance_score","availability_score","final_score","metric_breakdown","coverage_breakdown","context_summary","calculated_at")
