from datetime import timedelta
from typing import Optional, Union

from django.db import transaction
from django.utils import timezone

from apps.company_info.models import CompanyInfo
from apps.core.exceptions import (
    InvalidTenantActionException,
    SubscriptionNotFoundException,
    TenantNotFoundException,
)
from apps.core.models.audit_log import AuditLog
from apps.saas_admin.dto.tenant_action_dto import TenantActionDto
from apps.subscriptions.models import Subscription


class TenantManagementService:
    """
    Servicio encargado de la ejecución de operaciones administrativas sobre empresas (Tenants).
    Garantiza consistencia transaccional, validaciones de transiciones de estado y registro en auditoría.
    """

    @classmethod
    @transaction.atomic
    def suspend_company(
        cls,
        company_id: int,
        reason: str = "",
        actor_user=None,
    ) -> CompanyInfo:
        """
        Suspende una empresa activa impidiendo su operatividad en la plataforma SaaS.
        """
        try:
            company = CompanyInfo.objects.select_for_update().get(id_company=company_id)
        except CompanyInfo.DoesNotExist:
            raise TenantNotFoundException()

        if company.status == CompanyInfo.CompanyStatus.SUSPENDED:
            raise InvalidTenantActionException(
                "La empresa ya se encuentra en estado suspendido."
            )

        company.status = CompanyInfo.CompanyStatus.SUSPENDED
        company.save(update_fields=["status", "updated_at"])

        cls._log_administrative_action(
            actor_user=actor_user,
            company=company,
            action="SUSPEND_TENANT",
            reason=reason,
        )

        return company

    @classmethod
    @transaction.atomic
    def reactivate_company(
        cls,
        company_id: int,
        reason: str = "",
        actor_user=None,
    ) -> CompanyInfo:
        """
        Reactiva una empresa previamente suspendida restituyendo su estado operativo.
        """
        try:
            company = CompanyInfo.objects.select_for_update().get(id_company=company_id)
        except CompanyInfo.DoesNotExist:
            raise TenantNotFoundException()

        if company.status == CompanyInfo.CompanyStatus.ACTIVE:
            raise InvalidTenantActionException(
                "La empresa ya se encuentra en estado activo."
            )

        company.status = CompanyInfo.CompanyStatus.ACTIVE
        company.save(update_fields=["status", "updated_at"])

        cls._log_administrative_action(
            actor_user=actor_user,
            company=company,
            action="REACTIVATE_TENANT",
            reason=reason,
        )

        return company

    @classmethod
    @transaction.atomic
    def extend_trial(
        cls,
        company_id: int,
        extra_days: int,
        reason: str = "",
        actor_user=None,
    ) -> Subscription:
        """
        Extiende el período de prueba gratuita (Trial) de una empresa o reactiva una prueba vencida.
        """
        if extra_days <= 0:
            raise InvalidTenantActionException(
                "Los días de extensión deben ser un número positivo mayor a cero."
            )

        try:
            company = CompanyInfo.objects.get(id_company=company_id)
        except CompanyInfo.DoesNotExist:
            raise TenantNotFoundException()

        sub = (
            Subscription.objects.select_for_update()
            .filter(company=company, is_active=True)
            .order_by("-start_date")
            .first()
        )
        if not sub:
            raise SubscriptionNotFoundException(
                "La empresa no cuenta con una suscripción registrada."
            )

        now = timezone.now()
        base_date = sub.end_date if sub.end_date > now else now
        sub.end_date = base_date + timedelta(days=extra_days)

        # Si estaba expirada, reactivamos estado a TRIAL
        if sub.status in [Subscription.Status.EXPIRED, Subscription.Status.PAST_DUE]:
            sub.status = Subscription.Status.TRIAL

        sub.notes = f"{sub.notes}\n[SaaS Admin] Extensión de trial por {extra_days} días. Motivo: {reason}".strip()
        sub.save(update_fields=["end_date", "status", "notes", "updated_at"])

        # Si la empresa estaba suspendida por vencimiento de suscripción, reactivarla
        if company.status == CompanyInfo.CompanyStatus.SUSPENDED:
            company.status = CompanyInfo.CompanyStatus.ACTIVE
            company.save(update_fields=["status", "updated_at"])

        cls._log_administrative_action(
            actor_user=actor_user,
            company=company,
            action="EXTEND_TRIAL",
            reason=reason,
            details={"extra_days": extra_days, "new_end_date": str(sub.end_date)},
        )

        return sub

    @classmethod
    def execute_action(
        cls,
        company_id: int,
        dto: TenantActionDto,
        actor_user=None,
    ) -> Union[CompanyInfo, Subscription]:
        """
        Despachador centralizado de acciones administrativas basado en TenantActionDto.
        """
        action = dto.action.lower().strip()

        if action == "suspend":
            return cls.suspend_company(
                company_id=company_id, reason=dto.reason, actor_user=actor_user
            )
        elif action == "reactivate":
            return cls.reactivate_company(
                company_id=company_id, reason=dto.reason, actor_user=actor_user
            )
        elif action == "extend-trial":
            return cls.extend_trial(
                company_id=company_id,
                extra_days=dto.extra_days,
                reason=dto.reason,
                actor_user=actor_user,
            )
        else:
            raise InvalidTenantActionException(
                f"Acción administrativa no soportada: '{dto.action}'. Acciones válidas: 'suspend', 'reactivate', 'extend-trial'."
            )

    @staticmethod
    def _log_administrative_action(
        actor_user,
        company: CompanyInfo,
        action: str,
        reason: str,
        details: Optional[dict] = None,
    ) -> None:
        """
        Registra la acción administrativa de manera inmutable en el AuditLog de la plataforma.
        """
        payload = {
            "administrative_action": action,
            "reason": reason,
            "company_id": company.id_company,
            "company_business_name": company.business_name,
        }
        if details:
            payload["details"] = details

        try:
            AuditLog.objects.create(
                user=actor_user
                if getattr(actor_user, "is_authenticated", False)
                else None,
                company=company,
                method="POST",
                path=f"/api/v1/saas-admin/tenants/{company.id_company}/actions/",
                status_code=200,
                payload=payload,
            )
        except Exception:
            # Fallback silencioso para no romper la transacción si la auditoría falla
            pass
