from typing import Any, Optional

from rest_framework import serializers

from apps.company_info.models import CompanyInfo
from apps.saas_admin.dto.impersonation_dto import ImpersonationRequestDTO
from apps.saas_admin.dto.tenant_action_dto import TenantActionDto
from apps.subscriptions.models import Plan, Subscription, SubscriptionPayment


class PlanSummarySerializer(serializers.ModelSerializer):
    """Representación resumida del plan contratado."""

    class Meta:
        model = Plan
        fields = (
            "id_plan",
            "name",
            "code",
            "billing_cycle",
            "price",
        )


class SubscriptionSummarySerializer(serializers.ModelSerializer):
    """Representación administrativa de una suscripción."""

    plan = PlanSummarySerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Subscription
        fields = (
            "id_subscription",
            "status",
            "status_display",
            "start_date",
            "end_date",
            "grace_period_days",
            "auto_renew",
            "days_remaining",
            "is_valid",
            "plan",
        )


class UserSummarySerializer(serializers.Serializer):
    """Representación mínima del usuario propietario o colaborador."""

    id_user = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj) -> str:
        if not obj:
            return ""
        return obj.get_full_name() or obj.username


class TenantListSerializer(serializers.ModelSerializer):
    """
    Serializador de alto rendimiento para el listado global de empresas.
    Utiliza atributos precargados (prefetched_subscriptions) para evitar N+1 queries.
    """

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    owner = serializers.SerializerMethodField()
    plan_name = serializers.SerializerMethodField()
    sub_status = serializers.SerializerMethodField()
    days_left = serializers.SerializerMethodField()
    subscription = serializers.SerializerMethodField()

    class Meta:
        model = CompanyInfo
        fields = (
            "id_company",
            "uuid",
            "business_name",
            "trade_name",
            "tax_id",
            "email",
            "phone",
            "status",
            "status_display",
            "owner",
            "plan_name",
            "sub_status",
            "days_left",
            "subscription",
            "created_at",
        )

    def _get_subscription(self, obj: CompanyInfo) -> Optional[Subscription]:
        # Revisar prefetched_subscriptions del selector
        prefetched = getattr(obj, "prefetched_subscriptions", None)
        if prefetched is not None:
            return prefetched[0] if prefetched else None

        # Revisar current_subscription
        current = getattr(obj, "current_subscription", None)
        if current is not None:
            return current[0] if isinstance(current, (list, tuple)) else current

        return None

    def get_owner(self, obj: CompanyInfo) -> Optional[dict[str, Any]]:
        owner = getattr(obj, "owner_user", None)
        if not owner:
            return None
        return UserSummarySerializer(owner).data

    def get_plan_name(self, obj: CompanyInfo) -> str:
        sub = self._get_subscription(obj)
        return sub.plan.name if sub and sub.plan else "Sin Plan"

    def get_sub_status(self, obj: CompanyInfo) -> str:
        sub = self._get_subscription(obj)
        return sub.get_status_display() if sub else "N/A"

    def get_days_left(self, obj: CompanyInfo) -> int:
        sub = self._get_subscription(obj)
        return sub.days_remaining if sub else 0

    def get_subscription(self, obj: CompanyInfo) -> Optional[dict[str, Any]]:
        sub = self._get_subscription(obj)
        if not sub:
            return None
        return SubscriptionSummarySerializer(sub).data


class PaymentSummarySerializer(serializers.ModelSerializer):
    """Representación resumida de transacciones y pagos de suscripción."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    plan_name = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionPayment
        fields = (
            "id_payment",
            "amount",
            "payment_method",
            "transaction_reference",
            "status",
            "status_display",
            "payment_date",
            "plan_name",
        )

    def get_plan_name(self, obj: SubscriptionPayment) -> str:
        if obj.subscription and obj.subscription.plan:
            return obj.subscription.plan.name
        return ""


class TenantDetailSerializer(serializers.Serializer):
    """
    Serializador completo para el detalle administrativo de una empresa.
    Mapea la respuesta estructurada de SaaSAdminSelector.get_tenant_detail().
    """

    company = TenantListSerializer(read_only=True)
    owner = serializers.SerializerMethodField()
    current_subscription = SubscriptionSummarySerializer(
        read_only=True, allow_null=True
    )
    all_subscriptions = SubscriptionSummarySerializer(many=True, read_only=True)
    recent_payments = PaymentSummarySerializer(many=True, read_only=True)
    active_members_count = serializers.IntegerField(read_only=True)

    def get_owner(self, obj: dict[str, Any]) -> Optional[dict[str, Any]]:
        owner = obj.get("owner")
        if owner:
            return UserSummarySerializer(owner).data
        company = obj.get("company")
        if company and getattr(company, "owner_user", None):
            return UserSummarySerializer(company.owner_user).data
        return None


class TenantActionSerializer(serializers.Serializer):
    """
    Validador estricto para la ejecución de acciones administrativas en Tenants.
    """

    action = serializers.ChoiceField(
        choices=["extend-trial", "suspend", "reactivate"],
        required=True,
    )
    reason = serializers.CharField(
        required=True,
        min_length=3,
        max_length=500,
        allow_blank=False,
    )
    extra_days = serializers.IntegerField(
        required=False,
        default=0,
        min_value=0,
    )

    def validate(self, attrs):
        action = attrs.get("action")
        extra_days = attrs.get("extra_days", 0)

        if action == "extend-trial" and extra_days <= 0:
            raise serializers.ValidationError(
                {
                    "extra_days": "Se requiere especificar un número mayor a cero de días para extender la prueba."
                }
            )
        return attrs

    def to_dto(self) -> TenantActionDto:
        return TenantActionDto(
            action=self.validated_data["action"],
            reason=self.validated_data.get("reason", "").strip(),
            extra_days=self.validated_data.get("extra_days", 0),
        )


class ImpersonateRequestSerializer(serializers.Serializer):
    """
    Validador para la solicitud de inicio de sesión de soporte / impersonación temporal.
    """

    target_user_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        default=None,
    )
    reason = serializers.CharField(
        required=True,
        min_length=5,
        max_length=500,
        allow_blank=False,
    )

    def to_dto(self, company_id: int) -> ImpersonationRequestDTO:
        return ImpersonationRequestDTO(
            company_id=company_id,
            target_user_id=self.validated_data.get("target_user_id"),
            reason=self.validated_data["reason"].strip(),
        )


class GlobalMetricsSerializer(serializers.Serializer):
    """
    Serializador de salida para las métricas globales y KPIs del SaaS.
    """

    total_companies = serializers.IntegerField(read_only=True)
    active_companies = serializers.IntegerField(read_only=True)
    suspended_companies = serializers.IntegerField(read_only=True)
    total_users = serializers.IntegerField(read_only=True, default=0)
    active_trials = serializers.IntegerField(read_only=True)
    active_paid_subscriptions = serializers.IntegerField(read_only=True)
    past_due_subscriptions = serializers.IntegerField(read_only=True)
    expired_subscriptions = serializers.IntegerField(read_only=True)
    mrr = serializers.FloatField(read_only=True)
    current_month_revenue = serializers.FloatField(read_only=True)
    total_historical_revenue = serializers.FloatField(read_only=True)
    recent_payments = serializers.ListField(
        child=serializers.DictField(),
        read_only=True,
        required=False,
        default=list,
    )
