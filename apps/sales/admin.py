from django.contrib import admin

from apps.sales.models import Sale, SaleDetail


class SaleDetailInline(admin.TabularInline):
    model = SaleDetail
    extra = 0
    raw_id_fields = ("product",)
    readonly_fields = ("subtotal",)
    fields = (
        "product",
        "quantity",
        "unit_price",
        "discount",
        "subtotal",
    )


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = (
        "sale_number",
        "company",
        "customer",
        "user",
        "total",
        "payment_method",
        "status",
        "sale_type",
        "sale_date",
    )

    list_filter = (
        "company",
        "status",
        "payment_method",
        "sale_type",
        "sale_date",
        "is_active",
    )

    search_fields = (
        "sale_number",
        "customer__first_name",
        "customer__last_name",
        "customer__document_number",
        "customer__business_name",
        "user__username",
        "company__business_name",
    )

    raw_id_fields = ("company", "customer", "user")

    readonly_fields = (
        "sale_date",
        "created_at",
        "updated_at",
    )

    inlines = [SaleDetailInline]

    fieldsets = (
        (
            "Encabezado de la Venta",
            {
                "fields": (
                    "company",
                    "sale_number",
                    "customer",
                    "user",
                    "sale_type",
                    "status",
                    "sale_date",
                )
            },
        ),
        (
            "Montos y Pago",
            {
                "fields": (
                    "subtotal",
                    "discount",
                    "tax",
                    "total",
                    "payment_method",
                    "amount_received",
                    "change_amount",
                )
            },
        ),
        (
            "Notas y Observaciones",
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


@admin.register(SaleDetail)
class SaleDetailAdmin(admin.ModelAdmin):
    list_display = (
        "id_sale_detail",
        "sale",
        "product",
        "quantity",
        "unit_price",
        "discount",
        "subtotal",
    )

    list_filter = (
        "sale__company",
        "sale__status",
    )

    search_fields = (
        "sale__sale_number",
        "product__name",
        "product__code",
    )

    raw_id_fields = ("sale", "product")
