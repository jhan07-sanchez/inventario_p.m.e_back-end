from rest_framework import serializers

from apps.company_info.dto.company_info_dto import (
    CompanyInfoCreateDto,
    CompanyInfoUpdateDto,
)
from apps.company_info.models import CompanyInfo


class CompanyInfoSerializer(serializers.ModelSerializer):
    """
    Serializer utilizado para representar la información
    completa de la empresa.
    """

    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = CompanyInfo
        fields = (
            "id_company",
            "business_name",
            "trade_name",
            "tax_id",
            "phone",
            "mobile",
            "email",
            "website",
            "address",
            "city",
            "state",
            "country",
            "logo",
            "logo_url",
            "description",
            "receipt_footer",
            "is_active",
            "created_at",
            "updated_at",
        )

    def get_logo_url(self, obj) -> str | None:
        """Retorna la URL absoluta del logo si existe."""
        if obj.logo:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.logo.url)
            return obj.logo.url
        return None


class CompanyInfoCreateSerializer(serializers.Serializer):
    """
    Serializer utilizado para crear la información de empresa.
    """

    business_name = serializers.CharField(
        max_length=200,
        required=True,
    )
    trade_name = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        default="",
    )
    tax_id = serializers.CharField(
        max_length=30,
        required=True,
    )
    phone = serializers.CharField(
        max_length=30,
        required=False,
        allow_blank=True,
        default="",
    )
    mobile = serializers.CharField(
        max_length=30,
        required=False,
        allow_blank=True,
        default="",
    )
    email = serializers.EmailField(
        max_length=254,
        required=False,
        allow_blank=True,
        default="",
    )
    website = serializers.URLField(
        max_length=200,
        required=False,
        allow_blank=True,
        default="",
    )
    address = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
    )
    city = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        default="",
    )
    state = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        default="",
    )
    country = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        default="Colombia",
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )
    receipt_footer = serializers.CharField(
        required=False,
        allow_blank=True,
        default="Gracias por su compra",
    )

    def to_dto(self) -> CompanyInfoCreateDto:
        """Convierte los datos validados en un DTO."""
        v = self.validated_data
        return CompanyInfoCreateDto(
            business_name=v["business_name"],
            tax_id=v["tax_id"],
            trade_name=v.get("trade_name", ""),
            phone=v.get("phone", ""),
            mobile=v.get("mobile", ""),
            email=v.get("email", ""),
            website=v.get("website", ""),
            address=v.get("address", ""),
            city=v.get("city", ""),
            state=v.get("state", ""),
            country=v.get("country", "Colombia"),
            description=v.get("description", ""),
            receipt_footer=v.get("receipt_footer", "Gracias por su compra"),
        )


class CompanyInfoUpdateSerializer(serializers.Serializer):
    """
    Serializer utilizado para actualizar la información de empresa.
    """

    business_name = serializers.CharField(
        max_length=200,
        required=False,
        allow_null=True,
    )
    trade_name = serializers.CharField(
        max_length=200,
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    tax_id = serializers.CharField(
        max_length=30,
        required=False,
        allow_null=True,
    )
    phone = serializers.CharField(
        max_length=30,
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    mobile = serializers.CharField(
        max_length=30,
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    email = serializers.EmailField(
        max_length=254,
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    website = serializers.URLField(
        max_length=200,
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    address = serializers.CharField(
        max_length=255,
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    city = serializers.CharField(
        max_length=100,
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    state = serializers.CharField(
        max_length=100,
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    country = serializers.CharField(
        max_length=100,
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    description = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    receipt_footer = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
    )

    def to_dto(self) -> CompanyInfoUpdateDto:
        """Convierte los datos validados en un DTO."""
        v = self.validated_data
        return CompanyInfoUpdateDto(
            business_name=v.get("business_name"),
            trade_name=v.get("trade_name"),
            tax_id=v.get("tax_id"),
            phone=v.get("phone"),
            mobile=v.get("mobile"),
            email=v.get("email"),
            website=v.get("website"),
            address=v.get("address"),
            city=v.get("city"),
            state=v.get("state"),
            country=v.get("country"),
            description=v.get("description"),
            receipt_footer=v.get("receipt_footer"),
        )
