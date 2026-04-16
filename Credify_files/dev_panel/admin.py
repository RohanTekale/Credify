from django.contrib import admin
from .models import QueryLog,AuditLog


@admin.register(QueryLog)
class QueryLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'sql_preview', 'exec_ms', 'row_count', 'success', 'created_at')
    list_filter = ("success",)
    search_fields = ("sql", "user__email")
    readonly_fields = ('user', 'sql', 'exec_ms', 'row_count', 'success', 'error_msg', 'created_at')

    def sql_preview(self, obj):
        return obj.sql[:60]
    sql_preview.short_description = 'SQL'

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("level", "user", "message_preview","meta","created_at")
    list_filter = ("level",)
    search_fields = ("message","user__email")
    readonly_fields = ("user", "level", "message", "meta", "created_at")

    def message_preview(self, obj):
        return obj.message[:80]
    message_preview.short_description = 'Message'