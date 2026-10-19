from rest_framework import serializers

from apps.categories.models import Category
from apps.categories.services.category_service import CategoryService


class CategoryListSerializer(serializers.ModelSerializer):
    """
    Serializer utilizado para listar categorías.

    Expone únicamente la información necesaria para las tablas
    y listados del sistema.
    """

    parent_name = serializers.CharField(source="parent.name", read_only=True)

    class Meta:
        model = Category
        fields = (
            "id_category",
            "name",
            "description",
            "parent",
            "parent_name",
            "is_active",
        )

        read_only_fields = fields


class CategoryDetailSerializer(serializers.ModelSerializer):
    """
    Serializer utilizado para consultar el detalle completo
    de una categoría.
    """

    class Meta:
        model = Category
        fields = (
            "id_category",
            "name",
            "description",
            "is_active",
            "parent",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id_category",
            "created_at",
            "updated_at",
        )


class CategoryCreateSerializer(serializers.ModelSerializer):
    """
    Serializer utilizado para crear una categoría.

    La persistencia es delegada al CategoryService para mantener
    separadas las responsabilidades.
    """

    class Meta:
        model = Category
        fields = (
            "name",
            "description",
            "parent",
            "is_active",
        )

    def create(self, validated_data: dict) -> Category:
        """
        Crea una categoría utilizando el CategoryService.
        """

        return CategoryService.create_category(
            validated_data,
        )


class CategoryUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer utilizado para actualizar una categoría.

    La persistencia es delegada al CategoryService para mantener
    separadas las responsabilidades.
    """

    class Meta:
        model = Category
        fields = (
            "name",
            "description",
            "parent",
            "is_active",
        )

    def update(
        self,
        instance: Category,
        validated_data: dict,
    ) -> Category:
        """
        Actualiza una categoría utilizando el CategoryService.
        """

        return CategoryService.update_category(
            category=instance,
            validated_data=validated_data,
        )
