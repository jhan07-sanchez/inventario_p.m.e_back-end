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
    def invalidate_user_cache(user_id: int | None = None) -> None:
        """
        Invalida el caché de permisos de un usuario específico o todo el caché.
        """
        if user_id is not None:
            cache.delete(f"user_permissions_{user_id}")
        else:
            cache.clear()

    @staticmethod
    def _get_active_roles(user: User):
        """
        Obtiene los roles activos del usuario de forma optimizada.
        Utiliza prefetch cache si existe.
        """
        if (
            hasattr(user, "_prefetched_objects_cache")
            and "user_roles" in user._prefetched_objects_cache
        ):
            return [ur.role for ur in user.user_roles.all() if ur.role.is_active]

        return [
            ur.role
            for ur in user.user_roles.filter(role__is_active=True).select_related(
                "role"
            )
        ]

    @staticmethod
    def get_effective_permissions(user: User) -> dict[str, bool]:
        """
        Calcula los permisos efectivos de un usuario fusionando
        los permisos de todos sus roles activos.

        La fusión utiliza **unión lógica (OR)**: si *cualquier* rol
        otorga un permiso, el usuario lo tiene.

        Args:
            user:
                Instancia del usuario autenticado.

        Returns:
            Diccionario ``{código_permiso: bool}`` con todos los
            permisos registrados en ``SecurityRegistry``.
        """

        cache_key = f"user_permissions_{user.pk}"
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

        active_roles = PermissionService._get_active_roles(user)

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
    ) -> bool:
        """
        Verifica si un usuario posee un permiso específico.

        Aprovecha la resolución y caché de permisos efectivos
        para máxima velocidad de consulta en middlewares y guards.

        Args:
            user:
                Instancia del usuario autenticado.
            permission_code:
                Código del permiso a verificar (ej. ``"users.view"``).

        Returns:
            ``True`` si el usuario tiene el permiso.
        """

        if getattr(user, "is_superuser", False):
            return True

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
    def get_user_role_names(user: User) -> list[str]:
        """Devuelve los nombres de los roles activos del usuario."""

        active_roles = PermissionService._get_active_roles(user)
        return [role.role_name for role in active_roles]

    @staticmethod
    def has_any_active_role(user: User) -> bool:
        """Verifica que el usuario tiene al menos un rol activo asignado."""

        active_roles = PermissionService._get_active_roles(user)
        return len(active_roles) > 0

    @staticmethod
    def has_any_permission(
        effective_permissions: dict[str, bool],
    ) -> bool:
        """Verifica que el usuario posee al menos un permiso efectivo."""

        return any(effective_permissions.values())
