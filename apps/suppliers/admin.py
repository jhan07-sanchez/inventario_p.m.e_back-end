from django.contrib import admin

from apps.suppliers.models import Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = (
        "id_supplier",
        "document_type",
        "document_number",
        "first_name",
        "last_name",
        "business_name",
        "email",
        "is_active",
    )

    search_fields = (
        "document_number",
        "firs_name",
        "last_name",
        "business_name",
        "email",
    )

    list_filter = (
        "is_active",
        "document_type",
    )

    ordering = ("id_supplier",)

    fieldsets = (
        (
            "Informacion principal",
            {
                "fields": (
                    "document_type",
                    "document_number",
                    "first_name",
                    "last_name",
                    "business_name",
                )
            },
        ),
        (
            "informacion de contacto",
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
            "Fechas importantes",
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

    exclude = ("delete_at",)

    def get_queryset(self, request):
        """
        Muestra todos los proveedores incluyendo los eliminados logicamente.
        """
        return Supplier.all_objects.all()
