from decimal import Decimal

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.core.enums import PaymentMethod
from apps.purchases.dto.purchase_dto import (
    PurchaseCreateDTO,
    PurchaseDetailCreateDTO,
    PurchasePayDTO,
    PurchaseUpdateDTO,
)
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
    supplier_name = serializers.CharField(
        source="supplier.business_name", read_only=True, default=""
    )
    supplier_document = serializers.CharField(
        source="supplier.document_number", read_only=True
    )
    total_paid = serializers.SerializerMethodField()
    pending_balance = serializers.SerializerMethodField()
    is_fully_paid = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()

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
            "total_paid",
            "pending_balance",
            "is_fully_paid",
            "payment_status",
            "is_active",
            "created_at",
        )

    def _get_paid_amount(self, obj):
        if not hasattr(obj, "_cached_paid"):
            from django.db.models import Sum
            from apps.cash.models.payment import Payment

            ref_prefix = f"COMPRA #{obj.id_purchase}"
            total = (
                Payment.objects.filter(
                    reference__startswith=ref_prefix,
                    status=Payment.PaymentStatus.COMPLETED,
                    is_active=True,
                ).aggregate(total=Sum("amount"))["total"]
                or Decimal("0.00")
            )
            obj._cached_paid = total
        return obj._cached_paid

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_total_paid(self, obj):
        return self._get_paid_amount(obj)

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_pending_balance(self, obj):
        paid = self._get_paid_amount(obj)
        diff = obj.total - paid
        return diff if diff > Decimal("0.00") else Decimal("0.00")

    @extend_schema_field(serializers.BooleanField())
    def get_is_fully_paid(self, obj):
        return self.get_pending_balance(obj) <= Decimal("0.00")

    @extend_schema_field(serializers.CharField())
    def get_payment_status(self, obj):
        paid = self._get_paid_amount(obj)
        if paid >= obj.total:
            return "PAID"
        elif paid > Decimal("0.00"):
            return "PARTIAL"
        return "UNPAID"


class PurchaseRetrieveSerializer(serializers.ModelSerializer):
    supplier = SupplierListSerializer(read_only=True)
    details = PurchaseDetailSerializer(many=True, read_only=True)
    invoices_summary = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()
    pending_balance = serializers.SerializerMethodField()
    is_fully_paid = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    payments_summary = serializers.SerializerMethodField()

    class Meta:
        model = Purchase
        fields = (
            "id_purchase",
            "supplier",
            "status",
            "issue_date",
            "subtotal",
            "total",
            "total_paid",
            "pending_balance",
            "is_fully_paid",
            "payment_status",
            "payments_summary",
            "notes",
            "details",
            "invoices_summary",
            "is_active",
            "created_at",
            "updated_at",
        )

    def _get_paid_amount(self, obj):
        if not hasattr(obj, "_cached_paid"):
            from django.db.models import Sum
            from apps.cash.models.payment import Payment

            ref_prefix = f"COMPRA #{obj.id_purchase}"
            total = (
                Payment.objects.filter(
                    reference__startswith=ref_prefix,
                    status=Payment.PaymentStatus.COMPLETED,
                    is_active=True,
                ).aggregate(total=Sum("amount"))["total"]
                or Decimal("0.00")
            )
            obj._cached_paid = total
        return obj._cached_paid

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_total_paid(self, obj):
        return self._get_paid_amount(obj)

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_pending_balance(self, obj):
        paid = self._get_paid_amount(obj)
        diff = obj.total - paid
        return diff if diff > Decimal("0.00") else Decimal("0.00")

    @extend_schema_field(serializers.BooleanField())
    def get_is_fully_paid(self, obj):
        return self.get_pending_balance(obj) <= Decimal("0.00")

    @extend_schema_field(serializers.CharField())
    def get_payment_status(self, obj):
        paid = self._get_paid_amount(obj)
        if paid >= obj.total:
            return "PAID"
        elif paid > Decimal("0.00"):
            return "PARTIAL"
        return "UNPAID"

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_payments_summary(self, obj):
        from apps.cash.models.payment import Payment

        ref_prefix = f"COMPRA #{obj.id_purchase}"
        payments = Payment.objects.filter(
            reference__startswith=ref_prefix,
            is_active=True,
        ).order_by("-created_at")

        return [
            {
                "id_payment": p.id_payment,
                "amount": str(p.amount),
                "payment_method": p.payment_method,
                "payment_method_display": p.get_payment_method_display(),
                "status": p.status,
                "reference": p.reference,
                "notes": p.notes,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in payments
        ]

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_invoices_summary(self, obj):
        if hasattr(obj, "prefetched_invoices"):
            return [
                {
                    "id": inv.id,
                    "invoice_number": inv.invoice_number,
                    "status": inv.status,
                    "document_type": inv.document_type,
                }
                for inv in obj.prefetched_invoices
                if getattr(inv, "is_active", True)
            ]
        invoices = obj.invoices.filter(is_active=True).values(
            "id", "invoice_number", "status", "document_type"
        )
        return list(invoices)


class PurchaseDetailCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    quantity = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=True, min_value=Decimal("0.01")
    )
    unit_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=True, min_value=Decimal("0.00")
    )


class PurchaseCreateSerializer(serializers.Serializer):
    supplier_id = serializers.IntegerField(required=True)
    issue_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    details = PurchaseDetailCreateSerializer(
        many=True, required=True, allow_empty=False
    )

    def to_dto(self) -> PurchaseCreateDTO:
        validated_data = self.validated_data
        details_data = validated_data.get("details", [])

        details_dto = [
            PurchaseDetailCreateDTO(
                product_id=detail["product_id"],
                quantity=detail["quantity"],
                unit_price=detail["unit_price"],
            )
            for detail in details_data
        ]

        return PurchaseCreateDTO(
            supplier_id=validated_data["supplier_id"],
            issue_date=validated_data.get("issue_date"),
            notes=validated_data.get("notes"),
            details=details_dto,
        )


class PurchaseUpdateSerializer(serializers.Serializer):
    issue_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def to_dto(self) -> PurchaseUpdateDTO:
        validated_data = self.validated_data
        return PurchaseUpdateDTO(
            issue_date=validated_data.get("issue_date"),
            notes=validated_data.get("notes"),
        )


class PurchasePaySerializer(serializers.Serializer):
    """Serializer para registrar el pago de una compra."""

    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=True, min_value=Decimal("0.01")
    )
    payment_method = serializers.ChoiceField(
        choices=PaymentMethod.choices, default=PaymentMethod.CASH
    )
    cash_session_id = serializers.IntegerField(
        required=False, allow_null=True, default=None
    )
    reference = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )

    def to_dto(self) -> PurchasePayDTO:
        return PurchasePayDTO(
            amount=self.validated_data["amount"],
            payment_method=self.validated_data.get("payment_method", PaymentMethod.CASH),
            cash_session_id=self.validated_data.get("cash_session_id"),
            reference=self.validated_data.get("reference", ""),
            notes=self.validated_data.get("notes", ""),
        )
