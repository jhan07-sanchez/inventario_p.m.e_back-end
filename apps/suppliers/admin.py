from django.contrib import admin

from apps.suppliers.models import Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = (
        "id_supplier",
        "company",
        "document_type",
        "document_number",
        "first_name",
        "last_name",
        "business_name",
        "email",
        "is_active",
        "created_at",
    )

    search_fields = (
        "document_number",
        "first_name",
        "last_name",
        "business_name",
        "email",
        "company__business_name",
        "company__tax_id",
    )

    list_filter = (
        "company",
        "is_active",
        "document_type",
        "city",
        "country",
        "created_at",
    )

    ordering = ("id_supplier",)

    raw_id_fields = ("company",)

    fieldsets = (
        (
            "Identificación del Proveedor",
            {
                "fields": (
                    "company",
                    "document_type",
                    "document_number",
                    "first_name",
                    "last_name",
                    "business_name",
                )
            },
        ),
        (
            "Información de Contacto",
            {
                "fields": (
                    "email",
                    "phone",
                    "mobile",
                    "address",
                    "city",
                    "country",
                )
            },
        ),
        (
            "Estado y Notas",
            {
                "fields": (
                    "is_active",
                    "notes",
                )
            },
        ),
        (
            "Fechas Importantes",
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
        """Muestra todos los proveedores incluyendo eliminados lógicamente."""
        return Supplier.all_objects.all()
