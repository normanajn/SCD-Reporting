from django.contrib import admin

from .models import AuditLogEntry


@admin.register(AuditLogEntry)
class AuditLogEntryAdmin(admin.ModelAdmin):
    list_display  = ('timestamp', 'actor', 'action', 'object_type', 'object_repr', 'ip_address')
    list_filter   = ('action', 'object_type')
    search_fields = ('actor__email', 'object_repr', 'ip_address')
    readonly_fields = [f.name for f in AuditLogEntry._meta.get_fields()]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
