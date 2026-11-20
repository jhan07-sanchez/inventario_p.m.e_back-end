from typing import Any, Dict
from django.db import transaction
from rest_framework.exceptions import NotFound, ValidationError

from apps.core.models.audit_log import AuditLog
from apps.subscriptions.models import Plan
from apps.subscriptions.services.company_entitlement_service import (
    CompanyEntitlementService,
)


class SaaSPlanService:
    """
    Servicio de gestión administrativa para el catálogo de planes comerciales.
    Garantiza consistencia transaccional, validaciones de negocio y registro de auditoría.
    """

    @classmethod
    @transaction.atomic
    def create_plan(cls, validated_data: Dict[str, Any], actor_user=None) -> Plan:
        """
        Crea un nuevo plan comercial en la plataforma y registra la auditoría.
        """
        plan = Plan.objects.create(**validated_data)

        cls._log_action(
            actor_user=actor_user,
            action="CREATE_PLAN",
            plan=plan,
            payload={
                "id_plan": plan.id_plan,
                "code": plan.code,
                "name": plan.name,
                "price": str(plan.price),
                "billing_cycle": plan.billing_cycle,
                "limits": {
                    "max_users": plan.max_users,
                    "max_products": plan.max_products,
                    "max_invoices": plan.max_invoices_per_month,
                },
                "enabled_modules": plan.enabled_modules,
            },
        )
        return plan

    @classmethod
    @transaction.atomic
    def update_plan(cls, plan_id: int, validated_data: Dict[str, Any], actor_user=None) -> Plan:
        """
        Edita un plan comercial existente, validando su existencia y registrando auditoría.
        """
        try:
            plan = Plan.objects.select_for_update().get(id_plan=plan_id)
        except Plan.DoesNotExist:
            raise NotFound(detail=f"No se encontró el plan comercial con ID {plan_id}.")

        old_state = {
            "name": plan.name,
            "price": str(plan.price),
            "billing_cycle": plan.billing_cycle,
            "max_users": plan.max_users,
            "max_products": plan.max_products,
            "max_invoices_per_month": plan.max_invoices_per_month,
            "enabled_modules": plan.enabled_modules,
            "is_active": plan.is_active,
        }

        for attr, value in validated_data.items():
            setattr(plan, attr, value)

        plan.save()

        from apps.subscriptions.services.company_entitlement_service import (
            CompanyEntitlementService,
        )

        CompanyEntitlementService.invalidate_plan(plan.id_plan)

        cls._log_action(
            actor_user=actor_user,
            action="UPDATE_PLAN",
            plan=plan,
            payload={
                "id_plan": plan.id_plan,
                "code": plan.code,
                "old_state": old_state,
                "new_state": {k: str(getattr(plan, k)) if k == "price" else getattr(plan, k) for k in old_state},
            },
        )
        return plan

    @classmethod
    @transaction.atomic
    def toggle_status(cls, plan_id: int, actor_user=None) -> Plan:
        """
        Alterna el estado activo/inactivo de un plan comercial.
        Si se desactiva un plan que tiene suscriptores vigentes, el plan no se elimina,
        simplemente deja de estar disponible para nuevas suscripciones.
        """
        try:
            plan = Plan.objects.select_for_update().get(id_plan=plan_id)
        except Plan.DoesNotExist:
            raise NotFound(detail=f"No se encontró el plan comercial con ID {plan_id}.")

        plan.is_active = not plan.is_active
        plan.save(update_fields=["is_active", "updated_at"])

        CompanyEntitlementService.invalidate_plan(plan.id_plan)

        cls._log_action(
            actor_user=actor_user,
            action="TOGGLE_STATUS_PLAN",
            plan=plan,
            payload={
                "id_plan": plan.id_plan,
                "code": plan.code,
                "new_is_active": plan.is_active,
            },
        )
        return plan

    @staticmethod
    def _log_action(actor_user, action: str, plan: Plan, payload: dict) -> None:
        try:
            AuditLog.objects.create(
                user=actor_user if getattr(actor_user, "is_authenticated", False) else None,
                company=None,
                method="POST",
                path=f"/api/v1/saas-admin/plans/{plan.id_plan}/",
                status_code=200,
                payload={
                    "security_event": action,
                    **payload,
                },
            )
        except Exception:
            pass
