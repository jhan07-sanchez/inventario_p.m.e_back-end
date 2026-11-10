from django.contrib import admin

from apps.purchases.models import Purchase, PurchaseDetail


class PurchaseDetailInline(admin.TabularInline):
    model = PurchaseDetail
    extra = 0
    raw_id_fields = ("product",)
    readonly_fields = ("subtotal",)
    fields = ("product", "quantity", "unit_price", "subtotal")


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = (
        "id_purchase",
        "company",
        "supplier",
        "status",
        "issue_date",
        "subtotal",
        "total",
        "is_active",
        "created_at",
    )

    list_filter = (
        "company",
        "status",
        "issue_date",
        "is_active",
        "created_at",
    )

    search_fields = (
        "id_purchase",
        "supplier__business_name",
        "supplier__document_number",
        "company__business_name",
        "notes",
    )

    raw_id_fields = ("company", "supplier")

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    inlines = [PurchaseDetailInline]

    fieldsets = (
        (
            "Información de la Compra",
            {
                "fields": (
                    "company",
                    "supplier",
                    "status",
                    "issue_date",
                )
            },
        ),
        (
            "Totales",
            {
                "fields": (
                    "subtotal",
                    "total",
                )
            },
        ),
        (
            "Notas y Estado",
            {
                "fields": (
                    "notes",
                    "is_active",
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


@admin.register(PurchaseDetail)
class PurchaseDetailAdmin(admin.ModelAdmin):
    list_display = (
        "id_purchase_detail",
        "purchase",
        "product",
        "quantity",
        "unit_price",
        "subtotal",
    )

    list_filter = (
        "purchase__company",
        "purchase__status",
    )

    search_fields = (
        "purchase__id_purchase",
        "product__name",
        "product__code",
    )

    raw_id_fields = ("purchase", "product")
