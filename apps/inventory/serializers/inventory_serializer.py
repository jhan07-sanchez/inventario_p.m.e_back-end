from rest_framework import serializers

from apps.inventory.models import Inventory
from apps.inventory.models import InventoryMovement
from apps.products.models import Product


class InventoryListSerializer(serializers.ModelSerializer):
    """
    Serializer utilizado para listar inventarios.
    """

    product_name = serializers.CharField(
        source="product.name",
        read_only=True,
    )

    product_code = serializers.CharField(
        source="product.code",
        read_only=True,
    )

    category_name = serializers.CharField(
        source="product.category.name",
        read_only=True,
    )

    is_low_stock = serializers.BooleanField(
        read_only=True,
    )

    is_overstocked = serializers.BooleanField(
        read_only=True,
    )

    class Meta:
        model = Inventory
        fields = [
            "id_inventory",
            "product",
            "product_code",
            "product_name",
            "category_name",
            "current_stock",
            "minimum_stock",
            "maximum_stock",
            "is_low_stock",
            "is_overstocked",
            "is_active",
            "created_at",
            "updated_at",
        ]


class InventoryDetailSerializer(serializers.ModelSerializer):
    """
    Serializer utilizado para consultar el detalle de un inventario.
    """

    product_name = serializers.CharField(
        source="product.name",
        read_only=True,
    )

    product_code = serializers.CharField(
        source="product.code",
        read_only=True,
    )

    product_barcode = serializers.CharField(
        source="product.barcode",
        read_only=True,
    )

    category_name = serializers.CharField(
        source="product.category.name",
        read_only=True,
    )

    product_unit = serializers.CharField(
        source="product.unit",
        read_only=True,
    )

    is_low_stock = serializers.BooleanField(
        read_only=True,
    )

    is_overstocked = serializers.BooleanField(
        read_only=True,
    )

    class Meta:
        model = Inventory
        fields = [
            "id_inventory",
            "product",
            "product_code",
            "product_name",
            "product_barcode",
            "category_name",
            "product_unit",
            "current_stock",
            "minimum_stock",
            "maximum_stock",
            "is_low_stock",
            "is_overstocked",
            "is_active",
            "created_at",
            "updated_at",
        ]


class InventoryCreateSerializer(serializers.ModelSerializer):
    """
    Serializer utilizado para crear un inventario.
    """

    class Meta:
        model = Inventory
        fields = [
            "product",
            "current_stock",
            "minimum_stock",
            "maximum_stock",
        ]

    def validate(self, attrs):
        """
        Valida las reglas relacionadas con los niveles de stock.
        """
        current_stock = attrs.get(
            "current_stock",
            0,
        )
        minimum_stock = attrs.get(
            "minimum_stock",
            0,
        )
        maximum_stock = attrs.get(
            "maximum_stock",
        )

        if current_stock < 0:
            raise serializers.ValidationError(
                {"current_stock": ("El stock actual no puede ser negativo.")}
            )

        if maximum_stock is not None:
            if maximum_stock < minimum_stock:
                raise serializers.ValidationError(
                    {
                        "maximum_stock": (
                            "El stock máximo no puede ser menor que el stock mínimo."
                        )
                    }
                )

        return attrs

    def create(self, validated_data):
        from apps.inventory.services.inventory_service import InventoryService
        return InventoryService.create_inventory(validated_data)


class InventoryUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer utilizado para actualizar los parámetros
    de configuración del inventario.
    """

    class Meta:
        model = Inventory
        fields = [
            "minimum_stock",
            "maximum_stock",
            "is_active",
        ]

    def validate(self, attrs):
        """
        Valida la configuración de los niveles de stock.
        """
        minimum_stock = attrs.get(
            "minimum_stock",
            self.instance.minimum_stock,
        )

        maximum_stock = attrs.get(
            "maximum_stock",
            self.instance.maximum_stock,
        )

        if maximum_stock is not None:
            if maximum_stock < minimum_stock:
                raise serializers.ValidationError(
                    {
                        "maximum_stock": (
                            "El stock máximo no puede ser menor que el stock mínimo."
                        )
                    }
                )

        return attrs

    def update(self, instance, validated_data):
        from apps.inventory.services.inventory_service import InventoryService
        return InventoryService.update_inventory(instance, validated_data)


class InventoryMovementListSerializer(
    serializers.ModelSerializer,
):
    """
    Serializer utilizado para listar movimientos de inventario.
    """

    product_code = serializers.CharField(
        source="inventory.product.code",
        read_only=True,
    )

    product_name = serializers.CharField(
        source="inventory.product.name",
        read_only=True,
    )

    movement_type_display = serializers.CharField(
        source="get_movement_type_display",
        read_only=True,
    )

    supplier_name = serializers.CharField(
        source="supplier.__str__",
        read_only=True,
    )

    class Meta:
        model = InventoryMovement
        fields = [
            "id_movement",
            "inventory",
            "product_code",
            "product_name",
            "movement_type",
            "movement_type_display",
            "quantity",
            "previous_stock",
            "new_stock",
            "reference",
            "notes",
            "supplier_name",
            "created_at",
            "updated_at",
        ]


class InventoryMovementDetailSerializer(
    serializers.ModelSerializer,
):
    """
    Serializer utilizado para consultar el detalle
    de un movimiento de inventario.
    """

    product_code = serializers.CharField(
        source="inventory.product.code",
        read_only=True,
    )

    product_name = serializers.CharField(
        source="inventory.product.name",
        read_only=True,
    )

    movement_type_display = serializers.CharField(
        source="get_movement_type_display",
        read_only=True,
    )

    supplier_name = serializers.CharField(
        source="supplier.__str__",
        read_only=True,
    )

    class Meta:
        model = InventoryMovement
        fields = [
            "id_movement",
            "inventory",
            "product_code",
            "product_name",
            "movement_type",
            "movement_type_display",
            "quantity",
            "previous_stock",
            "new_stock",
            "reference",
            "notes",
            "supplier_name",
            "created_at",
            "updated_at",
        ]


class InventoryThresholdUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer utilizado para actualizar únicamente
    los umbrales de stock mínimo y máximo.
    """

    class Meta:
        model = Inventory
        fields = [
            "minimum_stock",
            "maximum_stock",
        ]

    def validate(self, attrs):
        minimum_stock = attrs.get(
            "minimum_stock",
            self.instance.minimum_stock,
        )
        maximum_stock = attrs.get(
            "maximum_stock",
            self.instance.maximum_stock,
        )

        if maximum_stock is not None and maximum_stock < minimum_stock:
            raise serializers.ValidationError(
                {
                    "maximum_stock": (
                        "El stock máximo no puede ser menor que el stock mínimo."
                    )
                }
            )

        return attrs

    def update(self, instance, validated_data):
        from apps.inventory.services.inventory_service import InventoryService
        return InventoryService.update_thresholds(instance, validated_data)


class InventoryEntrySerializer(serializers.Serializer):
    """
    Serializer para registrar una entrada de stock.
    """

    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    reference = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    supplier_id = serializers.IntegerField(
        required=False,
        allow_null=True,
    )

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "La cantidad de entrada debe ser mayor a cero."
            )
        return value


class InventoryExitSerializer(serializers.Serializer):
    """
    Serializer para registrar una salida de stock.
    """

    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    reference = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "La cantidad de salida debe ser mayor a cero."
            )
        return value


class InventoryAdjustmentSerializer(serializers.Serializer):
    """
    Serializer para registrar un ajuste manual de inventario.
    """

    new_stock = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    def validate_new_stock(self, value):
        if value < 0:
            raise serializers.ValidationError("El nuevo stock no puede ser negativo.")
        return value


# Alias para que el ViewSet reconozca el serializer de movimientos
InventoryMovementSerializer = InventoryMovementListSerializer
