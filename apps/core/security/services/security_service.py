"""
inventario-pme Security Service
=========================

Orquestador del contexto de seguridad del usuario autenticado.

Responsabilidades (Single Responsibility):
    - Obtener permisos efectivos.
    - Obtener roles activos.
    - Construir permisos, acciones, navegación y dashboard.

Delega la lógica de construcción a los builders existentes
sin duplicar código.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from apps.core.security.builders.action_builder import ActionBuilder
from apps.core.security.builders.dashboard_builder import DashboardBuilder
from apps.core.security.builders.permission_builder import PermissionBuilder
from apps.core.security.services.permission_service import PermissionService
from apps.core.security.services.permission_catalog_service import (
    PermissionCatalogService,
)
from apps.users.dto.security_context_result import SecurityContextResult

if TYPE_CHECKING:
    from apps.users.models import User


class SecurityService:
    """
    Servicio orquestador del contexto de seguridad del ERP.

    Actúa como fachada sobre ``PermissionService`` y los builders
    de permisos, acciones, navegación y dashboard.
    """

    @staticmethod
    def _resolve_effective_permissions(user: User) -> dict[str, bool]:
        """Obtiene los permisos efectivos del usuario."""

        return PermissionService.get_effective_permissions(user)

    @staticmethod
    def build_context(user: User) -> SecurityContextResult:
        """
        Construye el contexto completo de seguridad del usuario.

        Args:
            user:
                Usuario autenticado.

        Returns:
            ``SecurityContextResult`` con roles, permisos, acciones,
            navegación y dashboard.
        """

        effective_permissions = SecurityService._resolve_effective_permissions(user)
        role_names = PermissionService.get_user_role_names(user)

        return SecurityContextResult(
            roles=role_names,
            permissions=PermissionBuilder.build(effective_permissions),
            actions=ActionBuilder.build(effective_permissions),
            navigation=PermissionService.get_navigation(effective_permissions),
            dashboard=DashboardBuilder.build(effective_permissions),
        )

    @staticmethod
    def get_authorization_context(user: User) -> SecurityContextResult:
        """
        Construye el contexto de autorización (roles, permisos, acciones).

        Caso de uso: ``GET /api/v1/security/context``.
        """

        effective_permissions = SecurityService._resolve_effective_permissions(user)
        role_names = PermissionService.get_user_role_names(user)

        return SecurityContextResult(
            roles=role_names,
            permissions=PermissionBuilder.build(effective_permissions),
            actions=ActionBuilder.build(effective_permissions),
        )

    @staticmethod
    def get_navigation(user: User) -> list[dict]:
        """
        Construye el árbol de navegación del usuario.

        Caso de uso: ``GET /api/v1/security/navigation``.
        """

        effective_permissions = SecurityService._resolve_effective_permissions(user)

        return PermissionService.get_navigation(effective_permissions)

    @staticmethod
    def get_dashboard(user: User) -> dict:
        """
        Construye la configuración del dashboard del usuario.

        Caso de uso: ``GET /api/v1/security/dashboard``.
        """

        effective_permissions = SecurityService._resolve_effective_permissions(user)
        return DashboardBuilder.build(effective_permissions)

    @staticmethod
    def get_permission_catalog() -> list[dict[str, object]]:
        """
        Obtiene el catálogo completo de permisos y acciones
        registrados en SecurityRegistry.

        Delega a ``PermissionCatalogService`` como punto de
        acceso al catálogo de seguridad.

        Returns:
            Lista de módulos con sus permisos y acciones disponibles.
        """

        return PermissionCatalogService.get_catalog()
