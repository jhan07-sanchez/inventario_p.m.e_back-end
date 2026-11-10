from django.contrib import admin

from apps.categories.models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "id_category",
        "company",
        "name",
        "parent",
        "is_active",
        "created_at",
    )

    search_fields = (
        "name",
        "parent__name",
        "company__business_name",
        "company__tax_id",
    )

    list_filter = (
        "company",
        "is_active",
        "parent",
        "created_at",
    )

    ordering = ("id_category",)

    raw_id_fields = ("company", "parent")

    fieldsets = (
        (
            "Información Principal",
            {
                "fields": (
                    "company",
                    "name",
                    "description",
                    "parent",
                )
            },
        ),
        (
            "Estado",
            {"fields": ("is_active",)},
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
        """Muestra todas las categorías incluyendo las eliminadas lógicamente."""
        return Category.all_objects.all()
