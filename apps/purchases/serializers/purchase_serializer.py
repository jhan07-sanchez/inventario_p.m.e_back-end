from decimal import Decimal
from rest_framework import serializers

from apps.purchases.dto.purchase_dto import PurchaseCreateDTO, PurchaseDetailCreateDTO, PurchaseUpdateDTO
from apps.purchases.models import Purchase, PurchaseDetail
from apps.suppliers.serializers.supplier_serializer import SupplierListSerializer


class PurchaseDetailSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_code = serializers.CharField(source="product.code", read_only=True)

    class Meta:
        model = PurchaseDetail
        fields = (
            "id_purchase_detail",
            "product",
            "product_name",
            "product_code",
            "quantity",
            "unit_price",
            "subtotal",
        )


class PurchaseListSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.business_name", read_only=True, default="")
    supplier_document = serializers.CharField(source="supplier.document_number", read_only=True)

    class Meta:
        model = Purchase
        fields = (
            "id_purchase",
            "supplier",
            "supplier_name",
            "supplier_document",
            "status",
            "issue_date",
            "subtotal",
            "total",
            "is_active",
            "created_at",
        )


class PurchaseRetrieveSerializer(serializers.ModelSerializer):
    supplier = SupplierListSerializer(read_only=True)
    details = PurchaseDetailSerializer(many=True, read_only=True)
    invoices_summary = serializers.SerializerMethodField()

    class Meta:
        model = Purchase
        fields = (
            "id_purchase",
            "supplier",
            "status",
            "issue_date",
            "subtotal",
            "total",
            "notes",
            "details",
            "invoices_summary",
            "is_active",
            "created_at",
            "updated_at",
        )

    def get_invoices_summary(self, obj):
        invoices = obj.invoices.filter(is_active=True).values(
            "id", "invoice_number", "status", "document_type"
        )
        return list(invoices)


class PurchaseDetailCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2, required=True, min_value=Decimal('0.01'))
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=True, min_value=Decimal('0.00'))


class PurchaseCreateSerializer(serializers.Serializer):
    supplier_id = serializers.IntegerField(required=True)
    issue_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    details = PurchaseDetailCreateSerializer(many=True, required=True, allow_empty=False)

    def to_dto(self) -> PurchaseCreateDTO:
        validated_data = self.validated_data
        details_data = validated_data.get("details", [])

        details_dto = [
            PurchaseDetailCreateDTO(
                product_id=detail["product_id"],
                quantity=detail["quantity"],
                unit_price=detail["unit_price"]
            )
            for detail in details_data
        ]

        return PurchaseCreateDTO(
            supplier_id=validated_data["supplier_id"],
            issue_date=validated_data.get("issue_date"),
            notes=validated_data.get("notes"),
            details=details_dto
        )


class PurchaseUpdateSerializer(serializers.Serializer):
    issue_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def to_dto(self) -> PurchaseUpdateDTO:
        validated_data = self.validated_data
        return PurchaseUpdateDTO(
            issue_date=validated_data.get("issue_date"),
            notes=validated_data.get("notes")
        )
