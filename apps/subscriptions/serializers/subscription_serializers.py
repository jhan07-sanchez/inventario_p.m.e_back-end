from rest_framework import serializers

from apps.subscriptions.models import Plan, Subscription, SubscriptionPayment


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
    is_in_grace_period = serializers.BooleanField(read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)

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
            "is_in_grace_period",
            "days_remaining",
            "notes",
        ]
        read_only_fields = ["id_subscription", "start_date"]

