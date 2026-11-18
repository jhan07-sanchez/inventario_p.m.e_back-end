from django.contrib import admin

from apps.core.models.audit_log import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Administración de registros de auditoría (Audit Trail) del ERP.
    Por motivos de seguridad e integridad forense, este modelo es de solo lectura.
    """

    list_display = (
        "id",
        "user",
        "company",
        "method",
        "path",
        "status_code",
        "ip_address",
        "created_at",
    )

    list_filter = (
        "method",
        "status_code",
        "company",
        "created_at",
    )

    search_fields = (
        "path",
        "ip_address",
        "user__username",
        "user__email",
        "company__business_name",
        "company__tax_id",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "user",
        "company",
        "method",
        "path",
        "ip_address",
        "user_agent",
        "status_code",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
