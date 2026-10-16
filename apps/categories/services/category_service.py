from django.db import transaction

from apps.categories.models import Category
from apps.core.exceptions.custom_exceptions import (
    CategoryAlreadyExistsException,
    CategoryInactiveException,
)
from apps.core.services.base_service import BaseService


class CategoryService(BaseService[Category]):
    """
    Servicio encargado de la lógica de negocio relacionada
    con las categorías.
    """

    def __init__(self) -> None:
        super().__init__(Category)

    def validate(
        self,
        data: dict,
        instance: Category | None = None,
    ) -> dict:
        """
        Valida las reglas de negocio de una categoría.
        """

        category_name = data.get("name")

        if category_name:
            category_name = category_name.strip()

            category_mgr = getattr(Category, "all_objects", Category.objects)
            query = category_mgr.filter(
                name__iexact=category_name,
            )

            if instance is not None:
                query = query.exclude(
                    pk=instance.pk,
                )

            if query.exists():
                raise CategoryAlreadyExistsException()

            data["name"] = category_name

        return data

    def perform_create(
        self,
        data: dict,
    ) -> Category:
        """
        Crea físicamente una categoría.
        """

        category = Category(**data)

        category.full_clean()
        category.save()

        return category

    def perform_update(
        self,
        instance: Category,
        data: dict,
    ) -> Category:
        """
        Actualiza una categoría existente.
        """

        for field, value in data.items():
            setattr(instance, field, value)

        instance.full_clean()
        instance.save()

        return instance

    def perform_delete(
        self,
        instance: Category,
        soft_delete: bool = True,
    ) -> None:
        """
        Desactiva una categoría mediante borrado lógico.
        """

        if not instance.is_active:
            raise CategoryInactiveException()

        if soft_delete:
            instance.soft_delete()
        else:
            if hasattr(instance, "hard_delete"):
                instance.hard_delete()
            else:
                instance.delete()

    @staticmethod
    @transaction.atomic
    def create_category(
        validated_data: dict,
    ) -> Category:
        """
        Crea una nueva categoría aplicando las reglas de negocio.
        """

        return CategoryService().create(
            **validated_data,
        )

    @staticmethod
    @transaction.atomic
    def update_category(
        category: Category,
        validated_data: dict,
    ) -> Category:
        """
        Actualiza una categoría aplicando las reglas de negocio.
        """

        return CategoryService().update(
            category,
            **validated_data,
        )

    @staticmethod
    @transaction.atomic
    def deactivate_category(
        category: Category,
    ) -> Category:
        """
        Realiza el borrado lógico de una categoría.
        """

        CategoryService().delete(
            category,
            soft_delete=True,
        )

        return category

    @staticmethod
    @transaction.atomic
    def restore_category(
        category: Category,
    ) -> Category:
        """
        Reactiva una categoría previamente desactivada.
        """

        return CategoryService().restore(category)
