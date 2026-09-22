from decimal import Decimal

from rest_framework import serializers

from apps.sales.models import SaleDetail


class SaleDetailSerializer(serializers.ModelSerializer):
    """
    Serializer utilizado para representar los detalles de una venta.

    Expone la información del producto junto con los valores
    registrados en el detalle.
    """

    product_name = serializers.CharField(
        source="product.name",
        read_only=True,
    )
    product_code = serializers.CharField(
        source="product.code",
        read_only=True,
    )

    class Meta:
        model = SaleDetail
        fields = (
            "id_sale_detail",
            "product",
            "product_name",
            "product_code",
            "quantity",
            "unit_price",
            "discount",
            "subtotal",
        )


class SaleDetailCreateSerializer(serializers.Serializer):
    """
    Serializer utilizado para recibir los datos de un detalle
    durante la creación de una venta.
    """

    product_id = serializers.IntegerField(required=True)

    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=True,
        min_value=Decimal("0.01"),
    )

    unit_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
        min_value=Decimal("0.00"),
    )

    discount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        default=Decimal("0.00"),
        min_value=Decimal("0.00"),
    )
