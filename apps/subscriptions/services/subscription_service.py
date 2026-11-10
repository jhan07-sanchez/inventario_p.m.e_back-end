from datetime import timedelta
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.subscriptions.models import Plan, Subscription, SubscriptionPayment
from apps.subscriptions.selectors.subscription_selector import SubscriptionSelector


class SubscriptionService:
    """
    Servicio de gestión del ciclo de vida de suscripciones SaaS:
    Asignación de planes, renovación de períodos y conciliación de pagos.
    """

    @classmethod
    @transaction.atomic
    def assign_or_renew_plan(
        cls,
        company,
        plan: Plan,
        duration_days: int = 30,
        status: str = Subscription.Status.ACTIVE,
        notes: str = "",
    ) -> Subscription:
        """
        Asigna o renueva una suscripción para la empresa indicada.
        """
        if not company:
            raise ValidationError("Debe proporcionar una empresa válida.")

        now = timezone.now()
        current_sub = SubscriptionSelector.get_current_subscription(company)

        # Si ya existe una suscripción vigente, extendemos desde la fecha de vencimiento actual
        if current_sub and current_sub.end_date > now and current_sub.status == Subscription.Status.ACTIVE:
            start_date = current_sub.start_date
            end_date = current_sub.end_date + timedelta(days=duration_days)
            current_sub.plan = plan
            current_sub.end_date = end_date
            current_sub.status = status
            current_sub.notes = f"{current_sub.notes}\nRenovación: {notes}".strip()
            current_sub.save(update_fields=["plan", "end_date", "status", "notes", "updated_at"])
            return current_sub

        # De lo contrario, creamos una nueva suscripción
        end_date = now + timedelta(days=duration_days)
        subscription = Subscription.objects.create(
            company=company,
            plan=plan,
            status=status,
            start_date=now,
            end_date=end_date,
            grace_period_days=5,
            auto_renew=True,
            notes=notes,
        )
        return subscription

    @classmethod
    @transaction.atomic
    def record_payment(
        cls,
        subscription: Subscription,
        amount: Decimal,
        payment_method: str = "CREDIT_CARD",
        transaction_reference: str = "",
        notes: str = "",
        extend_days: Optional[int] = None,
    ) -> SubscriptionPayment:
        """
        Registra un pago para una suscripción y renueva los días de vigencia acordes al plan.
        """
        payment = SubscriptionPayment.objects.create(
            subscription=subscription,
            amount=amount,
            payment_method=payment_method,
            transaction_reference=transaction_reference,
            status=SubscriptionPayment.PaymentStatus.APPROVED,
            notes=notes,
        )

        # Si el plan es mensual por defecto son 30 días, anual 365 días
        days = extend_days
        if days is None:
            days = 365 if subscription.plan.billing_cycle == Plan.BillingCycle.ANNUAL else 30

        now = timezone.now()
        base_date = subscription.end_date if subscription.end_date > now else now
        subscription.end_date = base_date + timedelta(days=days)
        subscription.status = Subscription.Status.ACTIVE
        subscription.save(update_fields=["end_date", "status", "updated_at"])

        return payment

