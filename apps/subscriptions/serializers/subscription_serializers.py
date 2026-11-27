from urllib.parse import quote

from django.conf import settings
from rest_framework import serializers

from apps.subscriptions.models import Plan, Subscription, SubscriptionPayment
from apps.subscriptions.services.subscription_contact_service import (
    SubscriptionContactService,
)


class PlanSerializer(serializers.ModelSerializer):
    """
    Serializador para visualización de planes comerciales SaaS.
    """

    billing_cycle_display = serializers.CharField(
        source="get_billing_cycle_display",
        read_only=True,
    )

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
        ]
        read_only_fields = ["id_plan"]


class SubscriptionPaymentSerializer(serializers.ModelSerializer):
    """
    Serializador de pagos de suscripción.
    """

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    class Meta:
        model = SubscriptionPayment
        fields = [
            "id_payment",
            "subscription",
            "amount",
            "payment_method",
            "transaction_reference",
            "status",
            "status_display",
            "payment_date",
            "invoice_url",
            "notes",
        ]
        read_only_fields = ["id_payment", "payment_date"]


class SubscriptionSerializer(serializers.ModelSerializer):
    """
    Serializador detallado de la suscripción de una empresa.
    """

    plan = PlanSerializer(read_only=True)
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )
    is_valid = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    is_in_grace_period = serializers.BooleanField(read_only=True)
    is_read_only = serializers.BooleanField(read_only=True)
    can_write = serializers.BooleanField(read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)
    days_overdue = serializers.IntegerField(read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id_subscription",
            "company",
            "plan",
            "status",
            "status_display",
            "start_date",
            "end_date",
            "grace_period_days",
            "auto_renew",
            "is_valid",
            "is_expired",
            "is_in_grace_period",
            "is_read_only",
            "can_write",
            "days_remaining",
            "days_overdue",
            "notes",
        ]
        read_only_fields = ["id_subscription", "start_date"]


class SubscriptionStatusSerializer(serializers.Serializer):
    """
    Serializador estandarizado para la consulta de estado operativo de la suscripción (Modo Lectura / Escritura).
    """

    is_valid = serializers.BooleanField()
    is_read_only = serializers.BooleanField()
    can_write = serializers.BooleanField()
    status = serializers.CharField()
    status_display = serializers.CharField()
    plan_name = serializers.CharField()
    end_date = serializers.CharField(allow_null=True)
    days_remaining = serializers.IntegerField()
    days_overdue = serializers.IntegerField()
    is_in_grace_period = serializers.BooleanField()
    grace_period_days = serializers.IntegerField()
    renew_url = serializers.CharField(allow_null=True, required=False)
    contact_whatsapp = serializers.SerializerMethodField()
    contact_email = serializers.SerializerMethodField()

    def _resolve_company(self, obj):
        company = (
            self.context.get("company")
            if hasattr(self, "context") and self.context
            else None
        )
        if not company and isinstance(obj, dict):
            company = obj.get("company")
        return company

    def get_contact_whatsapp(self, obj):
        company = self._resolve_company(obj)
        whatsapp, _ = SubscriptionContactService.get_channels(company)
        return whatsapp

    def get_contact_email(self, obj):
        company = self._resolve_company(obj)
        _, email = SubscriptionContactService.get_channels(company)
        return email


class ChangePlanRequestSerializer(serializers.Serializer):
    """
    Serializador de entrada para el cambio o renovación de plan comercial de la empresa.
    """

    plan_code = serializers.CharField(
        required=True,
        max_length=50,
        help_text="Código identificador único del plan comercial a contratar (ej. BASIC, PRO, ENTERPRISE).",
    )
