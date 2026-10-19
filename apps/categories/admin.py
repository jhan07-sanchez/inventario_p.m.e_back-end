from django.contrib import admin

from apps.categories.models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "id_category",
        "name",
        "description",
        "parent",
        "is_active",
    )

    search_fields = (
        "name",
        "parent",
    )

    list_filter = (
        "is_active",
        "parent",
    )

    ordering = ("id_category",)

    fieldsets = (
        (
            "Informacion principal",
            {
                "fields": (
                    "name",
                    "description",
                    "parent",
                )
            },
        ),
        (
            "Estado y Notas",
            {"fields": ("is_active",)},
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
        Muestra todos las categorias incluyendo las eliminadas logicamente.
        """

        return Category.all_objects.all()
