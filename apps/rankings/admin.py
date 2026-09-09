from django.contrib import admin
from .models import RankingEntry,RankingSnapshot
class RankingEntryInline(admin.TabularInline):
    model=RankingEntry; extra=0; can_delete=False; readonly_fields=("player","team","position","rank","score","previous_rank","movement","minutes","metric_breakdown","context_summary")
    def has_add_permission(self,request,obj=None): return False
@admin.register(RankingSnapshot)
class RankingSnapshotAdmin(admin.ModelAdmin):
    list_display=("season","formula","cutoff_at","published_at","is_public"); readonly_fields=("season","formula","published_at","cutoff_at","is_public","created_at"); inlines=(RankingEntryInline,)
    def has_add_permission(self,request): return False
    def has_delete_permission(self,request,obj=None): return False
