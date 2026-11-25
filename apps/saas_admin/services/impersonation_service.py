import logging
from datetime import timedelta
from typing import Optional

from django.core.exceptions import PermissionDenied
from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken

from apps.company_info.models import CompanyInfo
from apps.core.exceptions import (
    BusinessException,
    CannotImpersonateSuperuserException,
    ChainedImpersonationDeniedException,
    TargetUserNotInTenantException,
    TenantNotFoundException,
)
from apps.core.models.audit_log import AuditLog
from apps.saas_admin.dto.impersonation_dto import (
    ImpersonationRequestDTO,
    ImpersonationResultDTO,
)
from apps.users.models import CompanyMembership, User

logger = logging.getLogger(__name__)


class ImpersonationService:
    """
    Servicio de alta seguridad para impersonación controlada y auditada de usuarios para soporte técnico.

    Principios innegociables:
    1. Exclusivo para Superadministradores (is_superuser=True).
    2. Prohíbe terminantemente la impersonación de otros Superadministradores.
    3. Prohíbe impersonaciones encadenadas (no se puede impersonar desde una sesión ya impersonada).
    4. Confinado estrictamente a la empresa objetivo (Tenant).
    5. Tokens de corta duración (15 minutos).
    6. No emite Refresh Tokens para prevenir renovaciones automáticas no autorizadas.
    7. Registro inmutable en el AuditLog de la plataforma.
    """

    IMPERSONATION_LIFETIME_MINUTES = 15

    @classmethod
    @transaction.atomic
    def start_impersonation(
        cls,
        admin_user: User,
        dto: ImpersonationRequestDTO,
        is_already_impersonated: bool = False,
    ) -> ImpersonationResultDTO:
        """
        Genera una sesión de soporte temporal para acceder en nombre del usuario objetivo de la empresa.
        """
        # 1. Validación de privilegios del actor
        if (
            not admin_user
            or not getattr(admin_user, "is_authenticated", False)
            or not admin_user.is_superuser
        ):
            raise PermissionDenied(
                "Se requieren privilegios de Superadministrador para iniciar impersonación."
            )

        # 2. Validación de no-encadenamiento
        if is_already_impersonated:
            raise ChainedImpersonationDeniedException()

        # 3. Validación de empresa objetivo
        try:
            company = CompanyInfo.objects.get(id_company=dto.company_id, is_active=True)
        except CompanyInfo.DoesNotExist:
            raise TenantNotFoundException()

        # 4. Resolución y validación del usuario objetivo
        target_user = cls._resolve_target_user(
            company=company, target_user_id=dto.target_user_id
        )

        # 5. Prohibición de impersonar superusuarios
        if target_user.is_superuser:
            raise CannotImpersonateSuperuserException()

        # 6. Generación del Access Token temporal con claims criptográficos
        refresh = RefreshToken.for_user(target_user)
        access = refresh.access_token

        lifetime = timedelta(minutes=cls.IMPERSONATION_LIFETIME_MINUTES)
        access.set_exp(lifetime=lifetime)

        # Claims explícitos de impersonación auditada
        access["is_impersonated"] = True
        access["impersonator_id"] = admin_user.id_user
        access["impersonator_email"] = admin_user.email
        access["impersonated_company"] = company.id_company
        access["company_id"] = company.id_company
        access["impersonation_reason"] = dto.reason.strip()

        # 7. Registro de auditoría
        cls._log_impersonation_event(
            admin_user=admin_user,
            target_user=target_user,
            company=company,
            reason=dto.reason,
            lifetime_minutes=cls.IMPERSONATION_LIFETIME_MINUTES,
        )

        logger.warning(
            f"[SaaS Security] Superusuario #{admin_user.id_user} ({admin_user.email}) "
            f"inició impersonación de #{target_user.id_user} ({target_user.email}) "
            f"en Empresa #{company.id_company} ('{company.business_name}'). Motivo: '{dto.reason}'"
        )

        return ImpersonationResultDTO(
            access_token=str(access),
            token_type="Bearer",
            expires_in=cls.IMPERSONATION_LIFETIME_MINUTES * 60,
            target_user={
                "id_user": target_user.id_user,
                "username": target_user.username,
                "email": target_user.email,
                "full_name": target_user.get_full_name() or target_user.username,
            },
            target_company={
                "id_company": company.id_company,
                "business_name": company.business_name,
                "tax_id": company.tax_id,
            },
            impersonated_by={
                "id_user": admin_user.id_user,
                "email": admin_user.email,
                "reason": dto.reason,
            },
        )

    @classmethod
    def _resolve_target_user(
        cls,
        company: CompanyInfo,
        target_user_id: Optional[int] = None,
    ) -> User:
        """
        Determina de forma segura el usuario que será impersonado dentro de la empresa.
        """
        if target_user_id:
            membership = (
                CompanyMembership.objects.filter(
                    company=company,
                    user_id=target_user_id,
                    is_active=True,
                    user__is_active=True,
                )
                .select_related("user")
                .first()
            )
            if not membership or not membership.user:
                raise TargetUserNotInTenantException()
            return membership.user

        # Si no se envió target_user_id, buscar al propietario principal de la empresa
        if company.owner_user and company.owner_user.is_active:
            # Validar que tenga membresía activa en la empresa
            has_membership = CompanyMembership.objects.filter(
                company=company,
                user=company.owner_user,
                is_active=True,
            ).exists()
            if has_membership:
                return company.owner_user

        owner_membership = (
            CompanyMembership.objects.filter(
                company=company,
                is_owner=True,
                is_active=True,
                user__is_active=True,
            )
            .select_related("user")
            .first()
        )
        if owner_membership and owner_membership.user:
            return owner_membership.user

        # Fallback al primer miembro activo
        first_member = (
            CompanyMembership.objects.filter(
                company=company,
                is_active=True,
                user__is_active=True,
            )
            .select_related("user")
            .first()
        )
        if first_member and first_member.user:
            return first_member.user

        raise BusinessException(
            "La empresa no cuenta con usuarios activos elegibles para soporte.",
            code="SAAS_NO_ELIGIBLE_USERS",
        )

    @staticmethod
    def _log_impersonation_event(
        admin_user: User,
        target_user: User,
        company: CompanyInfo,
        reason: str,
        lifetime_minutes: int,
    ) -> None:
        """
        Registra el evento de soporte de forma inmutable en el AuditLog.
        """
        try:
            AuditLog.objects.create(
                user=admin_user,
                company=company,
                method="POST",
                path=f"/api/v1/saas-admin/tenants/{company.id_company}/impersonate/",
                status_code=200,
                payload={
                    "security_event": "SUPPORT_IMPERSONATION_STARTED",
                    "impersonator_id": admin_user.id_user,
                    "impersonator_email": admin_user.email,
                    "target_user_id": target_user.id_user,
                    "target_email": target_user.email,
                    "target_company_id": company.id_company,
                    "target_business_name": company.business_name,
                    "reason": reason,
                    "duration_minutes": lifetime_minutes,
                },
            )
        except Exception as e:
            logger.error(
                f"[SaaS Security] Fallo al guardar log de auditoría para impersonación: {e}"
            )

    @classmethod
    @transaction.atomic
    def end_impersonation(
        cls,
        actor_user: User,
        auth_payload: Optional[dict] = None,
    ) -> dict:
        """
        Finaliza formalmente una sesión de soporte técnico por impersonación
        y registra la traza inmutable en el registro de auditoría.
        """
        impersonator_id = None
        impersonated_company_id = None
        target_user_id = getattr(actor_user, "id_user", None) or getattr(
            actor_user, "pk", None
        )

        if auth_payload and isinstance(auth_payload, dict):
            impersonator_id = auth_payload.get("impersonator_id")
            impersonated_company_id = auth_payload.get("impersonated_company")

        try:
            AuditLog.objects.create(
                user_id=impersonator_id or target_user_id,
                company_id=impersonated_company_id,
                method="POST",
                path="/api/v1/saas-admin/tenants/impersonate/end/",
                status_code=200,
                payload={
                    "security_event": "SUPPORT_IMPERSONATION_ENDED",
                    "impersonator_id": impersonator_id,
                    "target_user_id": target_user_id,
                    "company_id": impersonated_company_id,
                },
            )
        except Exception as e:
            logger.error(
                f"[SaaS Security] Error registrando fin de impersonación en AuditLog: {e}"
            )

        logger.info(
            f"[SaaS Security] Finalizó sesión de impersonación para usuario #{target_user_id}"
        )

        return {
            "impersonation_ended": True,
            "message": "Sesión de soporte finalizada correctamente.",
        }
