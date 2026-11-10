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
from apps.core.security.services.permission_catalog_service import (
    PermissionCatalogService,
)
from apps.core.security.services.permission_service import PermissionService
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
    def _resolve_effective_permissions(
        user: User, company_id: int | None = None
    ) -> dict[str, bool]:
        """Obtiene los permisos efectivos del usuario en el contexto de una empresa."""

        return PermissionService.get_effective_permissions(user, company_id=company_id)

    @staticmethod
    def _get_user_companies_and_active(
        user: User, company_id: int | None = None
    ) -> tuple[list[dict], dict | None]:
        from apps.company_info.models import CompanyInfo
        from apps.users.models import CompanyMembership

        companies_data = []
        active_company_data = None

        if getattr(user, "is_superuser", False):
            for c in CompanyInfo.objects.filter(is_active=True).order_by("business_name"):
                info = {
                    "id_company": c.id_company,
                    "uuid": str(c.uuid),
                    "business_name": c.business_name,
                    "trade_name": c.trade_name,
                    "tax_id": c.tax_id,
                    "role_name": "Superadministrador",
                    "is_owner": True,
                    "status": c.status,
                }
                companies_data.append(info)
                if (company_id and c.id_company == company_id) or (
                    active_company_data is None and company_id is None
                ):
                    active_company_data = info
        elif hasattr(user, "memberships"):
            memberships = (
                user.memberships.filter(is_active=True,status=CompanyMembership.MembershipStatus.ACTIVE, company__is_active=True)
                .select_related("company", "role")
                .order_by("-is_owner", "company__business_name")
            )
            for m in memberships:
                info = {
                    "id_company": m.company.id_company,
                    "uuid": str(m.company.uuid),
                    "business_name": m.company.business_name,
                    "trade_name": m.company.trade_name,
                    "tax_id": m.company.tax_id,
                    "role_name": m.role.role_name,
                    "id_role": m.role.id_role,
                    "is_owner": m.is_owner,
                    "status": m.company.status,
                }
                companies_data.append(info)
                if (company_id and m.company.id_company == company_id) or (
                    active_company_data is None and company_id is None
                ):
                    active_company_data = info

        return companies_data, active_company_data

    @staticmethod
    def build_context(
        user: User, company_id: int | None = None
    ) -> SecurityContextResult:
        """
        Construye el contexto completo de seguridad del usuario en una empresa.
        """

        effective_permissions = SecurityService._resolve_effective_permissions(
            user, company_id=company_id
        )
        role_names = PermissionService.get_user_role_names(user, company_id=company_id)
        companies, active_company = SecurityService._get_user_companies_and_active(
            user, company_id=company_id
        )

        return SecurityContextResult(
            roles=role_names,
            permissions=PermissionBuilder.build(effective_permissions),
            actions=ActionBuilder.build(effective_permissions),
            navigation=PermissionService.get_navigation(effective_permissions),
            dashboard=DashboardBuilder.build(
                effective_permissions, company_id=company_id
            ),
            companies=companies,
            active_company=active_company,
        )

    @staticmethod
    def get_authorization_context(
        user: User, company_id: int | None = None
    ) -> SecurityContextResult:
        """
        Construye el contexto de autorización (roles, permisos, acciones, empresas).
        """

        effective_permissions = SecurityService._resolve_effective_permissions(
            user, company_id=company_id
        )
        role_names = PermissionService.get_user_role_names(user, company_id=company_id)
        companies, active_company = SecurityService._get_user_companies_and_active(
            user, company_id=company_id
        )

        return SecurityContextResult(
            roles=role_names,
            permissions=PermissionBuilder.build(effective_permissions),
            actions=ActionBuilder.build(effective_permissions),
            companies=companies,
            active_company=active_company,
        )

    @staticmethod
    def get_navigation(user: User, company_id: int | None = None) -> list[dict]:
        """
        Construye el árbol de navegación del usuario.

        Caso de uso: ``GET /api/v1/security/navigation``.
        """

        effective_permissions = SecurityService._resolve_effective_permissions(
            user, company_id=company_id
        )

        return PermissionService.get_navigation(effective_permissions)

    @staticmethod
    def get_dashboard(user: User, company_id: int | None = None) -> dict:
        """
        Construye la configuración del dashboard del usuario.

        Caso de uso: ``GET /api/v1/security/dashboard``.
        """

        effective_permissions = SecurityService._resolve_effective_permissions(
            user, company_id=company_id
        )
        return DashboardBuilder.build(effective_permissions, company_id=company_id)

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
