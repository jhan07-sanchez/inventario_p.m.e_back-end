"""
inventario-pme Permission Service
============================

Servicio de dominio responsable de calcular los permisos efectivos
de un usuario a partir de sus roles activos, y de construir la
estructura de navegación filtrada.

Responsabilidades (Single Responsibility):
    - Fusionar permisos de múltiples roles (unión lógica OR).
    - Consultar si un usuario posee un permiso específico.
    - Generar la navegación dinámica basada en permisos.

Este servicio NO conoce detalles de serialización, vistas ni JWT.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from apps.core.security.registry import SecurityRegistry

if TYPE_CHECKING:
    from apps.users.models import Role, User


from django.conf import settings
from django.core.cache import cache


class PermissionService:
    """
    Servicio centralizado para la resolución de permisos
    efectivos en todo el ERP.
    """

    @staticmethod
    def invalidate_user_cache(
        user_id: int | None = None,
        company_id: int | None = None,
    ) -> None:
        """
        Invalida el caché de permisos de un usuario específico para una empresa, o de todo el usuario.
        """
        if user_id is not None and company_id is not None:
            cache.delete(f"user_permissions_{user_id}_{company_id}")
            cache.delete(f"user_permissions_{user_id}")
        elif user_id is not None:
            cache.delete(f"user_permissions_{user_id}")
        else:
            cache.clear()

    @staticmethod
    def _get_active_roles(user: User, company_id: int | None = None):
        """
        Obtiene los roles activos del usuario considerando el contexto de empresa si se provee.
        Prioriza las membresías activas en la empresa; si no se especifica empresa,
        retorna los roles globales/legados o la unión de roles activos.
        """
        roles = []

        if company_id is not None and hasattr(user, "memberships"):
            membership_roles = [
                m.role
                for m in user.memberships.filter(
                    company_id=company_id,
                    is_active=True,
                    role__is_active=True,
                ).select_related("role")
            ]
            if membership_roles:
                return membership_roles

        # Fallback a roles directos del usuario (UserRole)
        if hasattr(user, "user_roles"):
            if (
                hasattr(user, "_prefetched_objects_cache")
                and "user_roles" in user._prefetched_objects_cache
            ):
                roles = [ur.role for ur in user.user_roles.all() if ur.role.is_active]
            else:
                roles = [
                    ur.role
                    for ur in user.user_roles.filter(role__is_active=True).select_related(
                        "role"
                    )
                ]

        if not roles and hasattr(user, "memberships"):
            roles = [
                m.role
                for m in user.memberships.filter(
                    is_active=True,
                    role__is_active=True,
                ).select_related("role")
            ]

        return roles

    @staticmethod
    def get_effective_permissions(
        user: User,
        company_id: int | None = None,
    ) -> dict[str, bool]:
        """
        Calcula los permisos efectivos de un usuario fusionando
        los permisos de todos sus roles activos en el contexto de la empresa.

        La fusión utiliza **unión lógica (OR)**: si *cualquier* rol
        otorga un permiso, el usuario lo tiene.
        """

        cache_key = (
            f"user_permissions_{user.pk}_{company_id}"
            if company_id is not None
            else f"user_permissions_{user.pk}"
        )
        cached_permissions = cache.get(cache_key)

        if cached_permissions is not None:
            return cached_permissions

        timeout = getattr(settings, "CACHE_TIMEOUTS", {}).get("permissions", 600)

        if user.is_superuser:
            val = {code: True for code in SecurityRegistry.get_all_security_codes()}
            cache.set(cache_key, val, timeout=timeout)
            return val

        all_codes = SecurityRegistry.get_all_security_codes()
        effective: dict[str, bool] = {code: False for code in all_codes}

        active_roles = PermissionService._get_active_roles(user, company_id=company_id)

        for role in active_roles:
            for code in all_codes:
                if PermissionService.role_grants_permission(role, code):
                    effective[code] = True

        cache.set(cache_key, effective, timeout=timeout)
        return effective

    @staticmethod
    def resolve_permission(
        permissions: dict | None,
        permission_code: str,
    ) -> bool:
        """
        Evalúa un permiso en el JSON del rol.

        Soporta formato plano (``{"users.view": true}``) y jerárquico
        (``{"users": {"view": true}}``).
        """

        if not permissions or not isinstance(permissions, dict):
            return False

        if permission_code in permissions:
            return permissions[permission_code] is True

        parts = permission_code.split(".")
        current: object = permissions

        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return False
            current = current[part]

        return current is True

    @staticmethod
    def role_grants_permission(
        role: Role,
        permission_code: str,
    ) -> bool:
        """Indica si un rol concede un código de permiso (JSON dinámico)."""

        return PermissionService.resolve_permission(
            role.permissions,
            permission_code,
        )

    @staticmethod
    def user_has_permission(
        user: User,
        permission_code: str,
        company_id: int | None = None,
    ) -> bool:
        """
        Verifica si un usuario posee un permiso específico (opcionalmente dentro del contexto de una empresa).
        """

        if getattr(user, "is_superuser", False):
            return True

        if company_id is not None:
            effective = PermissionService.get_effective_permissions(
                user, company_id=company_id
            )
        else:
            effective = PermissionService.get_effective_permissions(user)
        return effective.get(permission_code, False)

    @staticmethod
    def get_navigation(
        effective_permissions: dict[str, bool],
    ) -> list[dict]:
        """
        Genera la estructura de navegación filtrada según
        los permisos efectivos del usuario.

        Delega a ``NavigationBuilder`` como fachada (Facade).
        """

        from apps.core.security.builders.navigation_builder import NavigationBuilder

        return NavigationBuilder.build(effective_permissions)

    @staticmethod
    def get_user_role_names(user: User, company_id: int | None = None) -> list[str]:
        """Devuelve los nombres de los roles activos del usuario en la empresa."""

        active_roles = PermissionService._get_active_roles(user, company_id=company_id)
        return [role.role_name for role in active_roles]

    @staticmethod
    def has_any_active_role(user: User, company_id: int | None = None) -> bool:
        """Verifica que el usuario tiene al menos un rol activo asignado."""

        if getattr(user, "is_superuser", False):
            return True

        active_roles = PermissionService._get_active_roles(user, company_id=company_id)
        return len(active_roles) > 0

    @staticmethod
    def has_any_permission(
        effective_permissions: dict[str, bool],
    ) -> bool:
        """Verifica que el usuario posee al menos un permiso efectivo."""

        return any(effective_permissions.values())
