from django.contrib import admin

from apps.company_info.models import CompanyInfo


@admin.register(CompanyInfo)
class CompanyInfoAdmin(admin.ModelAdmin):
    """
    Configuración del administrador para CompanyInfo.
    """

    list_display = (
        "business_name",
        "tax_id",
        "phone",
        "email",
        "is_active",
    )
    search_fields = (
        "business_name",
        "trade_name",
        "tax_id",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
