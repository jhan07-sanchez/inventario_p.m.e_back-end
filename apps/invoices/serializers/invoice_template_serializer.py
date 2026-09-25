from rest_framework import serializers

from apps.invoices.dto.invoice_template_dto import InvoiceTemplateCreateDTO, InvoiceTemplateUpdateDTO
from apps.invoices.models import InvoiceTemplate


class InvoiceTemplateListSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceTemplate
        fields = (
            "id",
            "name",
            "document_type",
            "is_default",
            "is_active",
            "created_at",
        )


class InvoiceTemplateRetrieveSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceTemplate
        fields = (
            "id",
            "name",
            "document_type",
            "header_content",
            "body_content",
            "footer_content",
            "is_default",
            "is_active",
            "created_at",
            "updated_at",
        )


class InvoiceTemplateCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=True)
    document_type = serializers.ChoiceField(choices=InvoiceTemplate.DocumentType.choices, required=True)
    header_content = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    body_content = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    footer_content = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    is_default = serializers.BooleanField(required=False, default=False)

    def to_dto(self) -> InvoiceTemplateCreateDTO:
        validated_data = self.validated_data
        return InvoiceTemplateCreateDTO(
            name=validated_data["name"],
            document_type=validated_data["document_type"],
            header_content=validated_data.get("header_content"),
            body_content=validated_data.get("body_content"),
            footer_content=validated_data.get("footer_content"),
            is_default=validated_data.get("is_default", False),
        )


class InvoiceTemplateUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=False)
    header_content = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    body_content = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    footer_content = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    is_default = serializers.BooleanField(required=False)

    def to_dto(self) -> InvoiceTemplateUpdateDTO:
        validated_data = self.validated_data
        return InvoiceTemplateUpdateDTO(
            name=validated_data.get("name"),
            header_content=validated_data.get("header_content"),
            body_content=validated_data.get("body_content"),
            footer_content=validated_data.get("footer_content"),
            is_default=validated_data.get("is_default"),
        )
