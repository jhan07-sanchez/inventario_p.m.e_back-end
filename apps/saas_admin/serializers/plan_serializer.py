from decimal import Decimal
from rest_framework import serializers

from apps.subscriptions.models import Plan


class SaaSPlanSerializer(serializers.ModelSerializer):
    """
    Serializador administrativo completo para la visualización de planes comerciales en SaaS Admin.
    """

    billing_cycle_display = serializers.CharField(
        source="get_billing_cycle_display",
        read_only=True,
    )
    active_subscriptions_count = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = [
            "id_plan",
            "code",
            "name",
            "description",
            "price",
            "billing_cycle",
            "billing_cycle_display",
            "max_users",
            "max_products",
            "max_invoices_per_month",
            "enabled_modules",
            "is_active",
            "active_subscriptions_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id_plan",
            "billing_cycle_display",
            "active_subscriptions_count",
            "created_at",
            "updated_at",
        ]

    def get_active_subscriptions_count(self, obj: Plan) -> int:
        if hasattr(obj, "active_subs_count"):
            return obj.active_subs_count
        return obj.subscriptions.filter(
            is_active=True,
            status="ACTIVE",
        ).count()


class SaaSPlanCreateSerializer(serializers.ModelSerializer):
    """
    Validador y serializador para la creación de un nuevo plan comercial.
    """

    price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.00"),
        required=True,
    )
    max_users = serializers.IntegerField(min_value=1, default=1)
    max_products = serializers.IntegerField(min_value=1, default=100)
    max_invoices_per_month = serializers.IntegerField(min_value=1, default=100)
    enabled_modules = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        default=list,
    )

    class Meta:
        model = Plan
        fields = [
            "code",
            "name",
            "description",
            "price",
            "billing_cycle",
            "max_users",
            "max_products",
            "max_invoices_per_month",
            "enabled_modules",
            "is_active",
        ]

    def validate_code(self, value: str) -> str:
        code_clean = value.strip().upper()
        if not code_clean:
            raise serializers.ValidationError("El código del plan no puede estar vacío.")
        if Plan.objects.filter(code=code_clean).exists():
            raise serializers.ValidationError(
                f"Ya existe un plan registrado con el código '{code_clean}'."
            )
        return code_clean

    def validate_enabled_modules(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("enabled_modules debe ser una lista de identificadores.")

        from apps.subscriptions.services.company_entitlement_service import (
            CompanyEntitlementService,
        )

        valid_codes = CompanyEntitlementService.get_all_valid_module_codes()
        cleaned = []
        invalid = []

        for item in value:
            if not isinstance(item, str):
                invalid.append(str(item))
                continue
            code = item.strip().lower()
            if not code:
                continue
            canonical = CompanyEntitlementService.canonicalize_module_code(code)
            if canonical in valid_codes:
                if canonical not in cleaned:
                    cleaned.append(canonical)
            else:
                invalid.append(item)

        if invalid:
            raise serializers.ValidationError(
                f"Los siguientes identificadores de módulos no existen en el catálogo del ERP: {', '.join(invalid)}."
            )
        return cleaned


class SaaSPlanUpdateSerializer(serializers.ModelSerializer):
    """
    Validador y serializador para la edición de un plan comercial existente.
    """

    price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.00"),
        required=False,
    )
    max_users = serializers.IntegerField(min_value=1, required=False)
    max_products = serializers.IntegerField(min_value=1, required=False)
    max_invoices_per_month = serializers.IntegerField(min_value=1, required=False)
    enabled_modules = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
    )

    class Meta:
        model = Plan
        fields = [
            "name",
            "description",
            "price",
            "billing_cycle",
            "max_users",
            "max_products",
            "max_invoices_per_month",
            "enabled_modules",
            "is_active",
        ]

    def validate_enabled_modules(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("enabled_modules debe ser una lista de identificadores.")

        from apps.subscriptions.services.company_entitlement_service import (
            CompanyEntitlementService,
        )

        valid_codes = CompanyEntitlementService.get_all_valid_module_codes()
        cleaned = []
        invalid = []

        for item in value:
            if not isinstance(item, str):
                invalid.append(str(item))
                continue
            code = item.strip().lower()
            if not code:
                continue
            canonical = CompanyEntitlementService.canonicalize_module_code(code)
            if canonical in valid_codes:
                if canonical not in cleaned:
                    cleaned.append(canonical)
            else:
                invalid.append(item)

        if invalid:
            raise serializers.ValidationError(
                f"Los siguientes identificadores de módulos no existen en el catálogo del ERP: {', '.join(invalid)}."
            )
        return cleaned
