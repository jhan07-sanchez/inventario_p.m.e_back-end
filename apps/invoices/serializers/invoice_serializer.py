from decimal import Decimal
from rest_framework import serializers

from apps.invoices.dto.invoice_dto import InvoiceCreateDTO, InvoiceItemCreateDTO, InvoiceUpdateDTO
from apps.invoices.models import Invoice, InvoiceItem
from apps.invoices.serializers.invoice_template_serializer import (
    InvoiceTemplateListSerializer,
    InvoiceTemplateRetrieveSerializer,
)


class InvoiceItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_code = serializers.CharField(source="product.code", read_only=True)

    class Meta:
        model = InvoiceItem
        fields = (
            "id",
            "product",
            "product_name",
            "product_code",
            "quantity",
            "unit_price",
            "discount",
            "tax",
            "subtotal",
        )


class InvoiceListSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source="template.name", read_only=True)

    class Meta:
        model = Invoice
        fields = (
            "id",
            "invoice_number",
            "document_type",
            "status",
            "issue_date",
            "due_date",
            "template",
            "template_name",
            "purchase",
            "sale",
            "subtotal",
            "total",
            "is_active",
            "created_at",
        )


class InvoiceRetrieveSerializer(serializers.ModelSerializer):
    template = InvoiceTemplateRetrieveSerializer(read_only=True)
    items = InvoiceItemSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = (
            "id",
            "invoice_number",
            "document_type",
            "status",
            "issue_date",
            "due_date",
            "template",
            "purchase",
            "sale",
            "subtotal",
            "discount",
            "tax",
            "total",
            "notes",
            "company_name_snapshot",
            "company_tax_id_snapshot",
            "company_address_snapshot",
            "company_phone_snapshot",
            "company_email_snapshot",
            "items",
            "is_active",
            "created_at",
            "updated_at",
        )


class InvoiceItemCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2, required=True, min_value=Decimal('0.01'))
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=True, min_value=Decimal('0.00'))
    discount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal('0.00'), min_value=Decimal('0.00'))
    tax = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal('0.00'), min_value=Decimal('0.00'))


class InvoiceCreateSerializer(serializers.Serializer):
    document_type = serializers.ChoiceField(choices=Invoice.DocumentType.choices, required=True)
    template_id = serializers.IntegerField(required=True)
    invoice_number = serializers.CharField(max_length=50, required=True)
    issue_date = serializers.DateField(required=False, allow_null=True)
    due_date = serializers.DateField(required=False, allow_null=True)
    purchase_id = serializers.IntegerField(required=False, allow_null=True)
    sale_id = serializers.IntegerField(required=False, allow_null=True)
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
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    items = InvoiceItemCreateSerializer(many=True, required=True, allow_empty=False)

    def to_dto(self) -> InvoiceCreateDTO:
        validated_data = self.validated_data
        items_data = validated_data.get("items", [])

        items_dto = [
            InvoiceItemCreateDTO(
                product_id=item["product_id"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                discount=item.get("discount", Decimal("0.00")),
                tax=item.get("tax", Decimal("0.00")),
            )
            for item in items_data
        ]

        return InvoiceCreateDTO(
            document_type=validated_data["document_type"],
            template_id=validated_data["template_id"],
            invoice_number=validated_data["invoice_number"],
            issue_date=validated_data.get("issue_date"),
            due_date=validated_data.get("due_date"),
            purchase_id=validated_data.get("purchase_id"),
            sale_id=validated_data.get("sale_id"),
            discount=validated_data.get("discount", Decimal("0.00")),
            tax=validated_data.get("tax", Decimal("0.00")),
            notes=validated_data.get("notes"),
            items=items_dto
        )


class InvoiceUpdateSerializer(serializers.Serializer):
    issue_date = serializers.DateField(required=False, allow_null=True)
    due_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def to_dto(self) -> InvoiceUpdateDTO:
        validated_data = self.validated_data
        return InvoiceUpdateDTO(
            issue_date=validated_data.get("issue_date"),
            due_date=validated_data.get("due_date"),
            notes=validated_data.get("notes")
        )
