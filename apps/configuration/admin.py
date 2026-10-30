from django.contrib import admin

from apps.configuration.models import ConfigurationAudit, GlobalParameter


@admin.register(GlobalParameter)
class GlobalParameterAdmin(admin.ModelAdmin):
    """
    Configuración del administrador para GlobalParameter.
    """

    list_display = (
        "key",
        "value",
        "data_type",
        "is_active",
        "updated_at",
    )
    search_fields = (
        "key",
        "description",
        "value",
    )
    list_filter = (
        "data_type",
        "is_active",
        "created_at",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )


@admin.register(ConfigurationAudit)
class ConfigurationAuditAdmin(admin.ModelAdmin):
    """
    Configuración del administrador para ConfigurationAudit (solo lectura).
    """

    list_display = (
        "parameter_key",
        "action",
        "user",
        "old_value",
        "new_value",
        "created_at",
    )
    search_fields = (
        "parameter_key",
        "reason",
        "user__username",
    )
    list_filter = (
        "action",
        "created_at",
    )
    readonly_fields = (
        "parameter",
        "parameter_key",
        "action",
        "user",
        "old_value",
        "new_value",
        "reason",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

