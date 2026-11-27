from datetime import timedelta
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.company_info.models import CompanyInfo
from apps.subscriptions.models import Plan, Subscription, SubscriptionPayment


class SubscriptionService:
    """
    Servicio de gestión del ciclo de vida de suscripciones SaaS:
    Asignación de planes, renovación de períodos y conciliación de pagos.
    """

    @classmethod
    def invalidate_subscription_cache(cls, company_id: int) -> None:
        """
        Invalida de manera atómica el caché de estado de suscripción,
        entitlements y permisos de usuario para la empresa indicada.
        """
        if not company_id:
            return

        from django.core.cache import cache

        from apps.core.security.services.permission_service import PermissionService
        from apps.subscriptions.services.company_entitlement_service import (
            CompanyEntitlementService,
        )

        cache.delete(f"subscription_status_{company_id}")
        CompanyEntitlementService.invalidate_company(company_id)
        PermissionService.invalidate_user_cache(company_id=company_id)

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
        Asigna o renueva una suscripción para la empresa indicada con control de concurrencia.
        """
        if not company:
            raise ValidationError("Debe proporcionar una empresa válida.")

        company_id = getattr(company, "id_company", getattr(company, "pk", company))
        try:
            company_obj = CompanyInfo.objects.select_for_update().get(
                id_company=company_id
            )
        except CompanyInfo.DoesNotExist:
            raise ValidationError(f"No se encontró la empresa con ID {company_id}.")

        now = timezone.now()
        current_sub = (
            Subscription.objects.select_for_update()
            .filter(
                company=company_obj,
                is_active=True,
                status__in=[
                    Subscription.Status.ACTIVE,
                    Subscription.Status.TRIAL,
                    Subscription.Status.PAST_DUE,
                ],
            )
            .order_by("-end_date")
            .first()
        )

        # Si ya existe una suscripción vigente y activa, extendemos desde la fecha de vencimiento actual
        if (
            current_sub
            and current_sub.end_date > now
            and current_sub.status == Subscription.Status.ACTIVE
        ):
            end_date = current_sub.end_date + timedelta(days=duration_days)
            current_sub.plan = plan
            current_sub.end_date = end_date
            current_sub.status = status
            current_sub.notes = f"{current_sub.notes}\nRenovación: {notes}".strip()
            current_sub.save(
                update_fields=["plan", "end_date", "status", "notes", "updated_at"]
            )
            cls.invalidate_subscription_cache(company_obj.id_company)
            return current_sub

        # De lo contrario, cancelamos cualquier suscripción activa/trial previa para evitar solapamientos
        previous_subs = Subscription.objects.select_for_update().filter(
            company=company_obj,
            status__in=[
                Subscription.Status.ACTIVE,
                Subscription.Status.TRIAL,
                Subscription.Status.PAST_DUE,
            ],
            is_active=True,
        )
        for prev in previous_subs:
            prev.status = Subscription.Status.CANCELLED
            prev.notes = f"{prev.notes}\nCancelada por nueva asignación de plan '{plan.code}'.".strip()
            prev.save(update_fields=["status", "notes", "updated_at"])

        end_date = now + timedelta(days=duration_days)
        grace_days = 0 if status == Subscription.Status.TRIAL else 5
        subscription = Subscription.objects.create(
            company=company_obj,
            plan=plan,
            status=status,
            start_date=now,
            end_date=end_date,
            grace_period_days=grace_days,
            auto_renew=True,
            notes=notes,
        )

        cls.invalidate_subscription_cache(company_obj.id_company)
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
            days = (
                365
                if subscription.plan.billing_cycle == Plan.BillingCycle.ANNUAL
                else 30
            )

        now = timezone.now()
        base_date = subscription.end_date if subscription.end_date > now else now
        subscription.end_date = base_date + timedelta(days=days)
        subscription.status = Subscription.Status.ACTIVE
        subscription.save(update_fields=["end_date", "status", "updated_at"])

        cls.invalidate_subscription_cache(subscription.company_id)
        return payment
