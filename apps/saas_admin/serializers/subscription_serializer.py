from rest_framework import serializers

from apps.subscriptions.models import Plan, Subscription
from apps.saas_admin.serializers.plan_serializer import SaaSPlanSerializer


class SaaSSubscriptionListSerializer(serializers.ModelSerializer):
    """
    Serializador de alto rendimiento para el listado global de suscripciones en SaaS Admin.
    """

    company_id = serializers.IntegerField(source="company.id_company", read_only=True)
    company_name = serializers.CharField(source="company.business_name", read_only=True)
    company_tax_id = serializers.CharField(source="company.tax_id", read_only=True)
    plan = SaaSPlanSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    is_in_grace_period = serializers.BooleanField(read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id_subscription",
            "company_id",
            "company_name",
            "company_tax_id",
            "plan",
            "status",
            "status_display",
            "start_date",
            "end_date",
            "grace_period_days",
            "auto_renew",
            "days_remaining",
            "is_valid",
            "is_in_grace_period",
            "notes",
            "created_at",
            "updated_at",
        ]


class SaaSAssignPlanSerializer(serializers.Serializer):
    """
    Validador para la asignación de una nueva suscripción a una empresa.
    """

    company_id = serializers.IntegerField(required=True)
    plan_id = serializers.IntegerField(required=True)
    duration_days = serializers.IntegerField(required=False, default=30, min_value=1)
    status = serializers.ChoiceField(
        choices=Subscription.Status.choices,
        default=Subscription.Status.ACTIVE,
        required=False,
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="", max_length=500)


class SaaSChangePlanSerializer(serializers.Serializer):
    """
    Validador para el cambio de plan comercial de una suscripción activa.
    """

    new_plan_id = serializers.IntegerField(required=True)
    reason = serializers.CharField(required=True, min_length=3, max_length=500)


class SaaSRenewSubscriptionSerializer(serializers.Serializer):
    """
    Validador para la renovación de vigencia de una suscripción.
    """

    duration_days = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    reason = serializers.CharField(required=False, allow_blank=True, default="", max_length=500)
