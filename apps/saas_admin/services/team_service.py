import logging
from typing import Optional
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.core.exceptions import BusinessException
from apps.core.models.audit_log import AuditLog
from apps.core.security.services.permission_service import PermissionService
from apps.users.models import Role, UserRole

User = get_user_model()
logger = logging.getLogger(__name__)

PROFILE_ROLE_MAPPING = {
    "SUPERADMIN": {
        "role_name": "SaaS Superadmin",
        "description": "Control global de la plataforma SaaS",
        "permissions": {"*": True},
        "is_superuser": True,
    },
    "SUPPORT": {
        "role_name": "SaaS Soporte Técnico",
        "description": "Atención de incidencias e impersonación asistida",
        "permissions": {
            "saas.dashboard.view": True,
            "saas.tenants.view": True,
            "saas.tenants.impersonate": True,
            "saas.versions.view": True,
        },
        "is_superuser": False,
    },
    "SALES": {
        "role_name": "SaaS Ventas y Comercial",
        "description": "Gestión comercial y extensión de pruebas",
        "permissions": {
            "saas.dashboard.view": True,
            "saas.tenants.view": True,
            "saas.tenants.extend_trial": True,
        },
        "is_superuser": False,
    },
    "FINANCE": {
        "role_name": "SaaS Finanzas",
        "description": "Métricas financieras y recaudación de suscripciones",
        "permissions": {
            "saas.dashboard.view": True,
            "saas.tenants.view": True,
            "saas.finance.view": True,
            "saas.metrics.view": True,
        },
        "is_superuser": False,
    },
}


class SaaSTeamService:
    """
    Servicio de dominio para la gestión del personal interno del SaaS.
    Aplica principio de mínimo privilegio y separación de responsabilidades.
    """

    @classmethod
    def _get_or_create_saas_role(cls, profile_key: str) -> Optional[Role]:
        config = PROFILE_ROLE_MAPPING.get(profile_key)
        if not config:
            return None

        role, _ = Role.objects.get_or_create(
            role_name=config["role_name"],
            company=None,
            defaults={
                "role_description": config["description"],
                "permissions": config["permissions"],
                "is_active": True,
            },
        )
        return role

    @classmethod
    @transaction.atomic
    def create_member(cls, data: dict, actor_user: User) -> User:
        """
        Crea un nuevo miembro del equipo SaaS asignándole rol y credenciales.
        Solo permitido para el Superadministrador.
        """
        if not (actor_user and actor_user.is_superuser):
            raise PermissionDenied("Solo el Superadministrador puede registrar personal del equipo SaaS.")

        profile_key = data["saas_profile"].upper()
        profile_config = PROFILE_ROLE_MAPPING.get(profile_key)
        if not profile_config:
            raise BusinessException(f"Perfil SaaS desconocido: {profile_key}")

        is_superuser = profile_config["is_superuser"]

        # Crear el usuario en Django
        user = User.objects.create_user(
            username=data["username"].strip(),
            email=data["email"].strip().lower(),
            password=data["password"],
            first_name=data["first_name"].strip(),
            last_name=data["last_name"].strip(),
            document_number=data["document_number"].strip(),
            phone_number=data.get("phone_number", "").strip(),
            is_staff=True,
            is_superuser=is_superuser,
            is_active=True,
        )

        # Asignar rol global del sistema si no es superuser
        role = cls._get_or_create_saas_role(profile_key)
        if role:
            UserRole.objects.create(user=user, role=role)

        # Registrar evento en AuditLog
        try:
            AuditLog.objects.create(
                user=actor_user,
                company=None,
                method="POST",
                path="/api/v1/saas-admin/team/",
                status_code=201,
                payload={
                    "security_event": "SAAS_TEAM_MEMBER_CREATED",
                    "created_user_id": user.id_user,
                    "created_username": user.username,
                    "created_email": user.email,
                    "saas_profile": profile_key,
                    "is_superuser": is_superuser,
                    "actor_id": actor_user.id_user,
                },
            )
        except Exception as e:
            logger.error(f"[SaaS Team Service] Error al registrar auditoría: {e}")

        logger.info(
            f"[SaaS Team] Superusuario #{actor_user.id_user} creó al integrante #{user.id_user} "
            f"({user.email}) con perfil {profile_key}"
        )
        return user

    @classmethod
    @transaction.atomic
    def update_member(cls, user_id: int, data: dict, actor_user: User) -> User:
        """
        Actualiza los datos y/o perfil de un miembro del equipo SaaS.
        """
        if not (actor_user and actor_user.is_superuser):
            raise PermissionDenied("Solo el Superadministrador puede modificar miembros del equipo.")

        try:
            member = User.objects.get(pk=user_id, is_staff=True)
        except User.DoesNotExist:
            raise BusinessException("Miembro del equipo no encontrado o no pertenece al staff.", code="TEAM_MEMBER_NOT_FOUND")

        # Evitar que el actor se quite sus propios privilegios de superadmin si es el único
        if member.pk == actor_user.pk and "saas_profile" in data:
            if data["saas_profile"] != "SUPERADMIN":
                super_count = User.objects.filter(is_superuser=True, is_active=True).count()
                if super_count <= 1:
                    raise BusinessException("No puede revocar sus propios privilegios de superadministrador siendo el único activo.")

        # Actualizar campos básicos
        if "first_name" in data:
            member.first_name = data["first_name"].strip()
        if "last_name" in data:
            member.last_name = data["last_name"].strip()
        if "phone_number" in data:
            member.phone_number = data["phone_number"].strip()
        if "is_active" in data:
            if member.pk == actor_user.pk and not data["is_active"]:
                raise BusinessException("No puede desactivar su propia cuenta.")
            member.is_active = data["is_active"]
        if "password" in data and data["password"]:
            member.set_password(data["password"])

        # Actualizar perfil / roles si cambió
        if "saas_profile" in data:
            new_profile = data["saas_profile"].upper()
            profile_config = PROFILE_ROLE_MAPPING.get(new_profile)
            if profile_config:
                member.is_superuser = profile_config["is_superuser"]
                # Limpiar roles anteriores de sistema
                UserRole.objects.filter(user=member, role__company=None).delete()
                new_role = cls._get_or_create_saas_role(new_profile)
                if new_role:
                    UserRole.objects.create(user=member, role=new_role)

        member.save()
        PermissionService.invalidate_user_cache(member.pk)

        # Auditoría
        try:
            AuditLog.objects.create(
                user=actor_user,
                company=None,
                method="PUT",
                path=f"/api/v1/saas-admin/team/{member.id_user}/",
                status_code=200,
                payload={
                    "security_event": "SAAS_TEAM_MEMBER_UPDATED",
                    "target_user_id": member.id_user,
                    "target_username": member.username,
                    "updated_fields": list(data.keys()),
                    "actor_id": actor_user.id_user,
                },
            )
        except Exception as e:
            logger.error(f"[SaaS Team Service] Error al registrar auditoría: {e}")

        return member

    @classmethod
    @transaction.atomic
    def toggle_status(cls, user_id: int, is_active: bool, actor_user: User) -> User:
        """
        Activa o desactiva (revocación de acceso) a un miembro del equipo.
        """
        if not (actor_user and actor_user.is_superuser):
            raise PermissionDenied("Solo el Superadministrador puede modificar el estado de un integrante.")

        try:
            member = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise BusinessException("Miembro no encontrado.", code="TEAM_MEMBER_NOT_FOUND")

        if member.pk == actor_user.pk:
            raise BusinessException("No puede desactivar su propia cuenta.")

        member.is_active = is_active
        member.save()
        PermissionService.invalidate_user_cache(member.pk)

        # Auditoría
        try:
            AuditLog.objects.create(
                user=actor_user,
                company=None,
                method="POST",
                path=f"/api/v1/saas-admin/team/{member.id_user}/toggle-status/",
                status_code=200,
                payload={
                    "security_event": "SAAS_TEAM_MEMBER_STATUS_CHANGED",
                    "target_user_id": member.id_user,
                    "new_status": is_active,
                    "actor_id": actor_user.id_user,
                },
            )
        except Exception as e:
            logger.error(f"[SaaS Team Service] Error al registrar auditoría: {e}")

        return member
