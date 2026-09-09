from django.contrib import admin
from .models import ProviderSyncState,RawProviderPayload,StatsBombBacktestPayload
@admin.register(ProviderSyncState)
class ProviderSyncStateAdmin(admin.ModelAdmin): list_display=("provider","sync_key","last_success_at","last_attempt_at"); readonly_fields=("last_error",)
@admin.register(RawProviderPayload)
class RawProviderPayloadAdmin(admin.ModelAdmin): list_display=("provider","resource_type","provider_resource_id","received_at","http_status"); readonly_fields=("provider","resource_type","provider_resource_id","request_path","payload","payload_sha256","received_at","http_status"); search_fields=("provider_resource_id",)
@admin.register(StatsBombBacktestPayload)
class StatsBombBacktestPayloadAdmin(admin.ModelAdmin): list_display=("resource_type","source_path","imported_at"); readonly_fields=("resource_type","source_path","payload","payload_sha256","imported_at")
