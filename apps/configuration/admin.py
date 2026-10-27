from django.contrib import admin

from apps.configuration.models import GlobalParameter

# Register your models here.

admin.site.register(GlobalParameter)


class GlobalParameterAdmin(admin.ModelAdmin):
    """
    Configuracion del administrador para GlobalParameter.
    """

    list_display = (
        "key",
        "value",
        "data_type",
        "is_active",
    )
    search_fields = (
        "key",
        "description",
    )
    list_filter = (
        "data_type",
        "is_active",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
