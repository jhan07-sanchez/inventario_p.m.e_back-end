from decimal import Decimal

from rest_framework import serializers

from apps.sales.dto.sale_dto import (
    SaleCreateDto,
    SaleUpdateDto,
)
from apps.sales.dto.sale_detail_dto import SaleDetailDto
from apps.sales.models import Sale
from apps.sales.serializers.sale_detail_serializer import (
    SaleDetailCreateSerializer,
    SaleDetailSerializer
)


class SaleListSerializer(serializers.ModelSerializer):
    """
    Serializer utilizado para listar ventas.

    Expone únicamente la información necesaria para las tablas
    y listados del sistema.
    """

    customer_name = serializers.CharField(
        source="customer.business_name",
        read_only=True,
        default="",
    )
    customer_document = serializers.CharField(
        source="customer.document_number",
        read_only=True,
    )

    class Meta:
        model = Sale
        fields = (
            "id_sale",
            "sale_number",
            "customer",
            "customer_name",
            "customer_document",
            "status",
            "sale_date",
            "subtotal",
            "total",
            "is_active",
            "created_at",
        )


class SaleRetrieveSerializer(serializers.ModelSerializer):
    """
    Serializer utilizado para consultar el detalle completo
    de una venta.
    """

    details = SaleDetailSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Sale
        fields = (
            "id_sale",
            "sale_number",
            "customer",
            "user",
            "status",
            "sale_date",
            "subtotal",
            "discount",
            "tax",
            "total",
            "payment_method",
            "notes",
            "details",
            "is_active",
            "created_at",
            "updated_at",
        )


class SaleCreateSerializer(serializers.Serializer):
    """
    Serializer utilizado para crear una venta.

    La transformación de los datos validados hacia el DTO
    se realiza mediante to_dto().
    """

    customer_id = serializers.IntegerField(required=True)

    payment_method = serializers.ChoiceField(
        choices=Sale.PaymentMethod.choices,
        required=False,
        default=Sale.PaymentMethod.CASH,
    )

    discount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        default=Decimal("0.00"),
        min_value=Decimal("0.00"),
    )

    tax = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        default=Decimal("0.00"),
        min_value=Decimal("0.00"),
    )

    notes = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
    )

    details = SaleDetailCreateSerializer(
        many=True,
        required=True,
        allow_empty=False,
    )

    def to_dto(self) -> SaleCreateDto:
        """
        Convierte los datos validados en un SaleCreateDto.
        """

        validated_data = self.validated_data
        details_data = validated_data.get("details", [])

        details_dto = [
            SaleDetailDto(
                product_id=detail["product_id"],
                quantity=detail["quantity"],
                unit_price=detail.get("unit_price"),
                discount=detail.get(
                    "discount",
                    Decimal("0.00"),
                ),
            )
            for detail in details_data
        ]

        return SaleCreateDto(
            customer_id=validated_data["customer_id"],
            details=tuple(details_dto),
            discount=validated_data.get(
                "discount",
                Decimal("0.00"),
            ),
            tax=validated_data.get(
                "tax",
                Decimal("0.00"),
            ),
            payment_method=validated_data.get(
                "payment_method",
                Sale.PaymentMethod.CASH,
            ),
            notes=validated_data.get("notes") or "",
        )



class SaleUpdateSerializer(serializers.Serializer):
    """
    Serializer utilizado para actualizar los campos permitidos
    de una venta.
    """

    customer_id = serializers.IntegerField(
        required=False,
        allow_null=True,
    )

    payment_method = serializers.ChoiceField(
        choices=Sale.PaymentMethod.choices,
        required=False,
        allow_null=True,
    )

    notes = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
    )

    def to_dto(self) -> SaleUpdateDto:
        """
        Convierte los datos validados en un SaleUpdateDto.
        """

        validated_data = self.validated_data

        return SaleUpdateDto(
            customer_id=validated_data.get("customer_id"),
            payment_method=validated_data.get("payment_method"),
            notes=validated_data.get("notes"),
        )
