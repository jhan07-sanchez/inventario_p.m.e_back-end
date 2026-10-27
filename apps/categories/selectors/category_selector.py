from django.db.models import QuerySet

from apps.categories.models import Category
from apps.core.selectors.base_selector import BaseSelector


class CategorySelector(BaseSelector[Category]):
    """
    Selector encargado de centralizar las consultas
    relacionadas con las categorías.
    """

    def __init__(self):
        super().__init__(Category)

    def get_queryset(self, include_deleted: bool = False) -> QuerySet[Category]:
        """
        Retorna el queryset base de categorías ordenadas por nombre.
        """
        return (
            super()
            .get_queryset(include_deleted=include_deleted)
            .order_by("name")
        )

    @staticmethod
    def get_categories() -> QuerySet[Category]:
        """
        Retorna todas las categorías ordenadas según
        la configuración del modelo.
        """
        return CategorySelector().get_all()

    @staticmethod
    def get_active_categories() -> QuerySet[Category]:
        """
        Retorna únicamente las categorías activas.
        """
        return CategorySelector().get_active()

    @staticmethod
    def get_category_by_id(
        category_id: int,
        include_deleted: bool = False,
    ) -> Category:
        """
        Obtiene una categoría mediante su identificador.

        Lanza Category.DoesNotExist si la categoría
        no existe.
        """
        manager = Category.all_objects if include_deleted else Category.objects
        return manager.get(
            pk=category_id,
        )

    @staticmethod
    def get_active_category_by_id(
        category_id: int,
    ) -> Category:
        """
        Obtiene una categoría activa mediante su identificador.

        Lanza Category.DoesNotExist si no existe o está inactiva.
        """
        return Category.objects.get(
            pk=category_id,
            is_active=True,
        )

    @staticmethod
    def get_root_categories() -> QuerySet[Category]:
        """
        Retorna las categorías principales que no tienen
        una categoría padre.
        """
        return CategorySelector().filter(
            parent__isnull=True,
        )

    @staticmethod
    def get_children(
        category: Category,
    ) -> QuerySet[Category]:
        """
        Retorna las categorías hijas de una categoría.
        """
        return CategorySelector().filter(
            parent=category,
        )
