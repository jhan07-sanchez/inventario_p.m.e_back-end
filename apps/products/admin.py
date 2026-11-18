from django.contrib import admin

from apps.products.models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "id_product",
        "code",
        "name",
        "category",
        "company",
        "sale_price",
        "purchase_price",
        "unit",
        "is_active",
        "created_at",
    )

    search_fields = (
        "code",
        "barcode",
        "name",
        "description",
        "category__name",
        "company__business_name",
        "company__tax_id",
    )

    list_filter = (
        "company",
        "category",
        "unit",
        "is_active",
        "created_at",
    )

    raw_id_fields = ("company", "category")

    ordering = ("name",)

    fieldsets = (
        (
            "Identificación del Producto",
            {
                "fields": (
                    "company",
                    "code",
                    "barcode",
                    "name",
                    "category",
                    "description",
                )
            },
        ),
        (
            "Precios y Unidades",
            {
                "fields": (
                    "purchase_price",
                    "sale_price",
                    "unit",
                )
            },
        ),
        (
            "Estado",
            {
                "fields": ("is_active",),
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

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    exclude = ("deleted_at",)

    def get_queryset(self, request):
        """Muestra todos los productos incluyendo eliminados lógicamente."""
        return Product.all_objects.all()
