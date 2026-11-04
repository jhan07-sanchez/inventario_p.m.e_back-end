from rest_framework import serializers

from apps.finance.models.financial_category import FinancialCategory


class FinancialCategorySerializer(serializers.ModelSerializer):
    category_type_display = serializers.CharField(
        source="get_category_type_display", read_only=True
    )

    class Meta:
        model = FinancialCategory
        fields = [
            "id_financial_category",
            "name",
            "category_type",
            "category_type_display",
            "description",
            "company",
            "is_active",
            "created_at",
            "updated_at",
        ]


class FinancialCategoryCreateUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    category_type = serializers.ChoiceField(
        choices=FinancialCategory.CategoryType.choices,
        default=FinancialCategory.CategoryType.OUTFLOW,
    )
    description = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    company_id = serializers.IntegerField(required=False, allow_null=True, default=None)

