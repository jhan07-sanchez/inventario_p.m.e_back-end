from django.contrib import admin

from apps.company_info.models import CompanyInfo
from apps.users.models import CompanyMembership


class CompanyMembershipInline(admin.TabularInline):
    model = CompanyMembership
    extra = 0
    raw_id_fields = ("user", "role")
    fields = ("user", "role", "is_owner", "status", "is_active")


@admin.register(CompanyInfo)
class CompanyInfoAdmin(admin.ModelAdmin):
    """
    Configuración del administrador para CompanyInfo (Organizaciones SaaS).
    """

    list_display = (
        "id_company",
        "business_name",
        "trade_name",
        "tax_id",
        "owner_user",
        "status",
        "phone",
        "email",
        "is_active",
        "created_at",
    )

    list_filter = (
        "status",
        "is_active",
        "city",
        "country",
        "created_at",
    )

    search_fields = (
        "business_name",
        "trade_name",
        "tax_id",
        "email",
        "owner_user__username",
        "owner_user__email",
    )

    readonly_fields = (
        "uuid",
        "created_at",
        "updated_at",
    )

    raw_id_fields = ("owner_user",)

    inlines = [CompanyMembershipInline]

    fieldsets = (
        (
            "Identificación y Estado SaaS",
            {
                "fields": (
                    "uuid",
                    "status",
                    "owner_user",
                    "business_name",
                    "trade_name",
                    "tax_id",
                    "is_active",
                )
            },
        ),
        (
            "Contacto y Ubicación",
            {
                "fields": (
                    "phone",
                    "mobile",
                    "email",
                    "website",
                    "address",
                    "city",
                    "country",
                )
            },
        ),
        (
            "Personalización y Facturación",
            {
                "fields": (
                    "logo",
                    "description",
                    "receipt_footer",
                )
            },
        ),
        (
            "Auditoría",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )
