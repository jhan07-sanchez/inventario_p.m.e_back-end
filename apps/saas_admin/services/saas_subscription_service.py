from datetime import timedelta
from typing import Optional
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.company_info.models import CompanyInfo
from apps.core.models.audit_log import AuditLog
from apps.subscriptions.models import Plan, Subscription


class SaaSSubscriptionService:
    """
    Servicio administrativo para la gestión del ciclo de vida de suscripciones SaaS:
    Diferencia estrictamente asignación inicial, cambio de plan y renovación.
    """

    @classmethod
    @transaction.atomic
    def assign_plan(
        cls,
        company_id: int,
        plan_id: int,
        duration_days: int = 30,
        status: str = Subscription.Status.ACTIVE,
        notes: str = "",
        actor_user=None,
    ) -> Subscription:
        """
        Asigna una nueva suscripción a una empresa cliente.
        """
        try:
            company = CompanyInfo.objects.select_for_update().get(id_company=company_id)
        except CompanyInfo.DoesNotExist:
            raise NotFound(detail=f"No se encontró la empresa con ID {company_id}.")

        try:
            plan = Plan.objects.get(id_plan=plan_id)
        except Plan.DoesNotExist:
            raise NotFound(detail=f"No se encontró el plan con ID {plan_id}.")

        if not plan.is_active:
            raise ValidationError(detail=f"El plan '{plan.name}' está desactivado y no puede asignarse a nuevas suscripciones.")

        if duration_days <= 0:
            raise ValidationError(detail="La duración en días debe ser un número entero positivo.")

        now = timezone.now()
        end_date = now + timedelta(days=duration_days)

        # Regla comercial: Cancelar y archivar suscripciones activas, en prueba o en gracia previas
        # para garantizar la unicidad de la suscripción operativa de la empresa.
        previous_active_subs = Subscription.objects.select_for_update().filter(
            company=company,
            status__in=[
                Subscription.Status.ACTIVE,
                Subscription.Status.TRIAL,
                Subscription.Status.PAST_DUE,
            ],
            is_active=True,
        )
        superseded_ids = []
        for prev in previous_active_subs:
            superseded_ids.append(prev.id_subscription)
            prev.status = Subscription.Status.CANCELLED
            prev.notes = (
                f"{prev.notes}\n[SaaS Admin] Cancelada automáticamente por nueva asignación de plan '{plan.code}'."
            ).strip()
            prev.save(update_fields=["status", "notes", "updated_at"])

        subscription = Subscription.objects.create(
            company=company,
            plan=plan,
            status=status,
            start_date=now,
            end_date=end_date,
            grace_period_days=5,
            auto_renew=True,
            notes=notes or f"Asignación inicial por administrador {getattr(actor_user, 'email', 'SaaS Admin')}",
        )

        # Si la empresa cliente estaba suspendida, reactivarla
        if company.status == CompanyInfo.CompanyStatus.SUSPENDED and status == Subscription.Status.ACTIVE:
            company.status = CompanyInfo.CompanyStatus.ACTIVE
            company.save(update_fields=["status", "updated_at"])

        cls._log_subscription_action(
            actor_user=actor_user,
            company=company,
            action="ASSIGN_SUBSCRIPTION_PLAN",
            subscription=subscription,
            details={
                "plan_id": plan.id_plan,
                "plan_code": plan.code,
                "plan_name": plan.name,
                "duration_days": duration_days,
                "end_date": str(end_date),
                "superseded_subscription_ids": superseded_ids,
                "notes": notes,
            },
        )

        # Invalidar caché de entitlements y permisos
        from apps.subscriptions.services.company_entitlement_service import (
            CompanyEntitlementService,
        )
        from apps.core.security.services.permission_service import PermissionService

        CompanyEntitlementService.invalidate_company(subscription.company.id_company)
        PermissionService.invalidate_user_cache(company_id=subscription.company.id_company)

        try:
            from apps.notifications.services import NotificationService

            NotificationService().notify_subscription_assigned(
                company_name=company.name,
                plan_name=plan.name,
                company_id=company.pk,
                origin_id=str(subscription.pk),
            )
        except Exception:
            pass

        return subscription

    @classmethod
    @transaction.atomic
    def change_plan(
        cls,
        subscription_id: int,
        new_plan_id: int,
        reason: str = "",
        actor_user=None,
    ) -> Subscription:
        """
        Cambia el plan comercial de una suscripción activa sin alterar la fecha de vencimiento.
        Regla de negocio: La vigencia y los días restantes se preservan de manera estricta.
        """
        try:
            subscription = Subscription.objects.select_for_update().select_related("plan", "company").get(
                id_subscription=subscription_id
            )
        except Subscription.DoesNotExist:
            raise NotFound(detail=f"No se encontró la suscripción con ID {subscription_id}.")

        if subscription.status == Subscription.Status.CANCELLED:
            raise ValidationError(detail="No se puede cambiar el plan de una suscripción cancelada. Debe asignar una nueva suscripción a la empresa.")

        now = timezone.now()
        if subscription.status == Subscription.Status.EXPIRED or subscription.end_date <= now:
            raise ValidationError(detail="No se puede cambiar el plan de una suscripción vencida. Debe renovar la vigencia o asignar una nueva suscripción.")

        try:
            new_plan = Plan.objects.get(id_plan=new_plan_id)
        except Plan.DoesNotExist:
            raise NotFound(detail=f"No se encontró el nuevo plan con ID {new_plan_id}.")

        if not new_plan.is_active:
            raise ValidationError(detail=f"El plan '{new_plan.name}' no está disponible para contratación porque se encuentra inactivo.")

        old_plan = subscription.plan
        if old_plan.id_plan == new_plan.id_plan:
            raise ValidationError(detail=f"La suscripción ya cuenta con el plan '{new_plan.name}'.")

        # Modificación de plan sin alterar end_date
        subscription.plan = new_plan
        subscription.notes = (
            f"{subscription.notes}\n[SaaS Admin] Cambio de plan: {old_plan.name} ({old_plan.code}) → {new_plan.name} ({new_plan.code}). Motivo: {reason}".strip()
        )
        subscription.save(update_fields=["plan", "notes", "updated_at"])

        cls._log_subscription_action(
            actor_user=actor_user,
            company=subscription.company,
            action="CHANGE_SUBSCRIPTION_PLAN",
            subscription=subscription,
            details={
                "old_plan_id": old_plan.id_plan,
                "old_plan_code": old_plan.code,
                "old_plan_name": old_plan.name,
                "new_plan_id": new_plan.id_plan,
                "new_plan_code": new_plan.code,
                "new_plan_name": new_plan.name,
                "reason": reason,
                "preserved_end_date": str(subscription.end_date),
            },
        )
        return subscription

    @classmethod
    @transaction.atomic
    def renew_subscription(
        cls,
        subscription_id: int,
        duration_days: Optional[int] = None,
        reason: str = "",
        actor_user=None,
    ) -> Subscription:
        """
        Renueva una suscripción extendiendo su fecha de vencimiento a partir de la fecha actual
        o acumulando sobre la fecha de vencimiento previa si aún está vigente.
        """
        try:
            subscription = Subscription.objects.select_for_update().select_related("plan", "company").get(
                id_subscription=subscription_id
            )
        except Subscription.DoesNotExist:
            raise NotFound(detail=f"No se encontró la suscripción con ID {subscription_id}.")

        if subscription.status == Subscription.Status.CANCELLED:
            raise ValidationError(detail="No se puede renovar una suscripción cancelada. Debe asignar una nueva suscripción formal a la empresa.")

        days = duration_days
        if days is None or days <= 0:
            days = 365 if subscription.plan.billing_cycle == Plan.BillingCycle.ANNUAL else 30

        now = timezone.now()
        base_date = subscription.end_date if subscription.end_date > now else now
        new_end_date = base_date + timedelta(days=days)

        old_status = subscription.status
        old_end_date = subscription.end_date

        subscription.end_date = new_end_date
        subscription.status = Subscription.Status.ACTIVE
        subscription.notes = (
            f"{subscription.notes}\n[SaaS Admin] Renovación extendida en {days} días hasta {new_end_date.strftime('%Y-%m-%d')}. Motivo: {reason}".strip()
        )
        subscription.save(update_fields=["end_date", "status", "notes", "updated_at"])

        # Si la empresa cliente estaba suspendida por mora, reactivarla
        if subscription.company.status == CompanyInfo.CompanyStatus.SUSPENDED:
            subscription.company.status = CompanyInfo.CompanyStatus.ACTIVE
            subscription.company.save(update_fields=["status", "updated_at"])

        cls._log_subscription_action(
            actor_user=actor_user,
            company=subscription.company,
            action="RENEW_SUBSCRIPTION",
            subscription=subscription,
            details={
                "days_added": days,
                "old_end_date": str(old_end_date),
                "new_end_date": str(new_end_date),
                "old_status": old_status,
                "new_status": subscription.status,
                "reason": reason,
            },
        )

        # Invalidar caché de entitlements y permisos
        from apps.subscriptions.services.company_entitlement_service import (
            CompanyEntitlementService,
        )
        from apps.core.security.services.permission_service import PermissionService

        CompanyEntitlementService.invalidate_company(subscription.company.id_company)
        PermissionService.invalidate_user_cache(company_id=subscription.company.id_company)

        try:
            from apps.notifications.services import NotificationService

            plan_name = getattr(subscription.plan, "name", "Plan")
            NotificationService().notify_subscription_renewed(
                company_name=subscription.company.name,
                plan_name=plan_name,
                company_id=subscription.company.pk,
                origin_id=str(subscription.pk),
            )
        except Exception:
            pass

        return subscription

    @staticmethod
    def _log_subscription_action(
        actor_user,
        company: CompanyInfo,
        action: str,
        subscription: Subscription,
        details: dict,
    ) -> None:
        try:
            AuditLog.objects.create(
                user=actor_user if getattr(actor_user, "is_authenticated", False) else None,
                company=company,
                method="POST",
                path=f"/api/v1/saas-admin/subscriptions/{subscription.id_subscription}/",
                status_code=200,
                payload={
                    "security_event": action,
                    "subscription_id": subscription.id_subscription,
                    "company_id": company.id_company,
                    "company_name": company.business_name,
                    **details,
                },
            )
        except Exception:
            pass
