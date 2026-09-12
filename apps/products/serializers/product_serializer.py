from rest_framework import serializers

from apps.categories.models import Category
from apps.products.models import Product
from apps.products.services.product_service import ProductService


class ProductListSerializer(serializers.ModelSerializer):
    """
    Serializer utilizado para listar productos.

    Expone la información necesaria para tablas y listados
    del módulo de productos.
    """

    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
    )

    profit_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    profit_margin_percentage = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    stock = serializers.DecimalField(
        source="inventory.current_stock",
        read_only=True,
        max_digits=12,
        decimal_places=2,
    )

    minimum_stock = serializers.DecimalField(
        source="inventory.minimum_stock",
        read_only=True,
        max_digits=12,
        decimal_places=2,
    )

    maximum_stock = serializers.DecimalField(
        source="inventory.maximum_stock",
        read_only=True,
        max_digits=12,
        decimal_places=2,
    )

    is_low_stock = serializers.BooleanField(
        source="inventory.is_low_stock",
        read_only=True,
    )

    is_overstocked = serializers.BooleanField(
        source="inventory.is_overstocked",
        read_only=True,
    )

    class Meta:
        model = Product

        fields = (
            "id_product",
            "code",
            "barcode",
            "name",
            "category",
            "category_name",
            "purchase_price",
            "sale_price",
            "profit_amount",
            "profit_margin_percentage",
            "stock",
            "minimum_stock",
            "maximum_stock",
            "unit",
            "is_low_stock",
            "is_overstocked",
            "is_active",
        )

        read_only_fields = fields


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Serializer utilizado para consultar el detalle completo
    de un producto.
    """

    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
    )

    profit_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    profit_margin_percentage = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    stock = serializers.DecimalField(
        source="inventory.current_stock",
        read_only=True,
        max_digits=12,
        decimal_places=2,
    )

    minimum_stock = serializers.DecimalField(
        source="inventory.minimum_stock",
        read_only=True,
        max_digits=12,
        decimal_places=2,
    )

    maximum_stock = serializers.DecimalField(
        source="inventory.maximum_stock",
        read_only=True,
        max_digits=12,
        decimal_places=2,
    )

    is_low_stock = serializers.BooleanField(
        source="inventory.is_low_stock",
        read_only=True,
    )

    is_overstocked = serializers.BooleanField(
        source="inventory.is_overstocked",
        read_only=True,
    )

    class Meta:
        model = Product

        fields = (
            "id_product",
            "code",
            "barcode",
            "name",
            "description",
            "category",
            "category_name",
            "purchase_price",
            "sale_price",
            "profit_amount",
            "profit_margin_percentage",
            "stock",
            "minimum_stock",
            "maximum_stock",
            "unit",
            "is_low_stock",
            "is_overstocked",
            "is_active",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id_product",
            "profit_amount",
            "profit_margin_percentage",
            "stock",
            "minimum_stock",
            "maximum_stock",
            "is_low_stock",
            "is_overstocked",
            "created_at",
            "updated_at",
        )


class ProductCreateSerializer(serializers.ModelSerializer):
    """
    Serializer utilizado para crear productos.

    La persistencia es delegada al ProductService para mantener
    separadas las responsabilidades entre validación de entrada,
    lógica de negocio y persistencia.
    """

    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.filter(is_active=True),
    )

    class Meta:
        model = Product

        fields = (
            "code",
            "barcode",
            "name",
            "description",
            "category",
            "purchase_price",
            "sale_price",
            "unit",
            "is_active",
        )

    def create(
        self,
        validated_data: dict,
    ) -> Product:
        """
        Crea un producto utilizando el ProductService.
        """

        return ProductService.create_product(
            validated_data,
        )


class ProductUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer utilizado para actualizar productos.

    La persistencia es delegada al ProductService.
    """

    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.filter(is_active=True),
    )

    class Meta:
        model = Product

        fields = (
            "code",
            "barcode",
            "name",
            "description",
            "category",
            "purchase_price",
            "sale_price",
            "unit",
            "is_active",
        )

    def update(
        self,
        instance: Product,
        validated_data: dict,
    ) -> Product:
        """
        Actualiza un producto utilizando el ProductService.
        """

        return ProductService.update_product(
            product=instance,
            validated_data=validated_data,
        )
