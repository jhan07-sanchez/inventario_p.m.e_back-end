"""
inventario-pme Dynamic Permission Classes for DRF
=============================================

Proporciona una única clase reutilizable ``HasPermission`` que
reemplaza la necesidad de crear clases de permisos individuales
por cada acción de cada módulo.

Uso en ViewSets::

    from apps.core.security import HasPermission

    class UserViewSet(BaseViewSet):
        def get_permissions(self):
            permission_map = {
                "list":     [HasPermission("users.view")],
                "retrieve": [HasPermission("users.view")],
                "create":   [HasPermission("users.create")],
                "update":   [HasPermission("users.update")],
                "destroy":  [HasPermission("users.delete")],
            }
            return permission_map.get(
                self.action,
                [HasPermission("users.view")],
            )

Principios:
    - Open/Closed: agregar permisos nuevos NO requiere crear
      clases nuevas.
    - DRY: una sola clase para todo el ERP.
    - Dependency Inversion: depende de ``PermissionService``
      (abstracción), no de queries directas.
"""

from __future__ import annotations

from rest_framework.permissions import BasePermission

from apps.core.security.services.permission_service import PermissionService


def HasPermission(permission_code: str):
    """
    Factory que genera una clase dinámica de permisos para un código específico.
    """

    class DynamicPermission(BasePermission):
        message = "No tiene permisos para realizar esta acción."

        def has_permission(self, request, view):
            user = request.user

            if not (user and user.is_authenticated and user.is_active):
                return False

            if user.is_superuser:
                return True

            return PermissionService.user_has_permission(
                user=user,
                permission_code=permission_code,
            )

    DynamicPermission.__name__ = f"HasPermission_{permission_code.replace('.', '_')}"

    return DynamicPermission


def HasAnyPermission(*permission_codes: str):
    """
    Factory que genera una clase dinámica que valida si el usuario posee
    AL MENOS UNO de los códigos de permiso suministrados (unión lógica OR).
    """

    class DynamicAnyPermission(BasePermission):
        message = "No tiene permisos suficientes para realizar esta acción."

        def has_permission(self, request, view):
            user = request.user

            if not (user and user.is_authenticated and user.is_active):
                return False

            if user.is_superuser:
                return True

            return any(
                PermissionService.user_has_permission(
                    user=user,
                    permission_code=code,
                )
                for code in permission_codes
            )

    names = "_or_".join(c.replace(".", "_") for c in permission_codes)
    DynamicAnyPermission.__name__ = f"HasAnyPermission_{names}"

    return DynamicAnyPermission
