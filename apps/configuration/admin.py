from django.contrib import admin

from apps.configuration.models import (
    ConfigurationAudit,
    GlobalParameter,
    SoftwareVersion,
    UserVersionRead,
    VersionChangelogEntry,
)


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


class VersionChangelogEntryInline(admin.TabularInline):
    model = VersionChangelogEntry
    extra = 1
    fields = ("category", "title", "description", "order")


@admin.register(SoftwareVersion)
class SoftwareVersionAdmin(admin.ModelAdmin):
    """
    Gestión de versiones de software y notas de publicación (Changelog).
    """

    list_display = (
        "version",
        "name",
        "status",
        "priority",
        "published_at",
        "published_by",
        "is_active",
        "created_at",
    )

    list_filter = (
        "status",
        "priority",
        "is_active",
        "published_at",
        "created_at",
    )

    search_fields = (
        "version",
        "name",
        "description",
        "upgrade_instructions",
    )

    raw_id_fields = ("published_by", "created_by")

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    inlines = [VersionChangelogEntryInline]

    fieldsets = (
        (
            "Identificación de la Versión",
            {
                "fields": (
                    "version",
                    "name",
                    "status",
                    "priority",
                    "description",
                )
            },
        ),
        (
            "Publicación",
            {
                "fields": (
                    "published_at",
                    "published_by",
                    "created_by",
                )
            },
        ),
        (
            "Requisitos de Actualización",
            {
                "fields": (
                    "min_compatible_version",
                    "prerequisites",
                    "upgrade_instructions",
                )
            },
        ),
        (
            "Estado y Auditoría",
            {
                "fields": (
                    "is_active",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


@admin.register(VersionChangelogEntry)
class VersionChangelogEntryAdmin(admin.ModelAdmin):
    list_display = (
        "id_entry",
        "version",
        "category",
        "title",
        "order",
    )

    list_filter = (
        "category",
        "version",
    )

    search_fields = (
        "title",
        "description",
        "version__version",
    )

    raw_id_fields = ("version",)


@admin.register(UserVersionRead)
class UserVersionReadAdmin(admin.ModelAdmin):
    """
    Registro de lectura de versiones y notificaciones de clientes.
    """

    list_display = (
        "id",
        "user",
        "version",
        "read_at",
    )

    list_filter = (
        "version",
        "read_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "version__version",
    )

    raw_id_fields = ("user", "version")

    readonly_fields = (
        "user",
        "version",
        "read_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
