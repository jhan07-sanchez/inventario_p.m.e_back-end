"""
Permisos de acceso para la app users.

IsAuthenticatedAndActive se mantiene como guardia transversal.

Las clases Can* están deprecadas: usar ``apps.core.security.HasPermission``
en los ViewSets.
"""

from rest_framework.permissions import BasePermission

from apps.core.security.services.permission_service import PermissionService


class IsAuthenticatedAndActive(BasePermission):
    """
    Permite acceso unicamente a usuarios autenticados y activos.
    """

    message = "Debe iniciar sesion."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active)


class BaseRolePermission(BasePermission):
    """
    Deprecado. Se traduce dinámicamente al sistema moderno de PermissionService.
    """

    required_permission = None
    message = "No tiene permisos para realizar esta acción."

    LEGACY_PERMISSION_MAP = {
        "users_read": "users.view",
        "users_create": "users.create",
        "users_update": "users.update",
        "users_delete": "users.delete",
        "roles_read": "roles.view",
        "roles_create": "roles.create",
        "roles_update": "roles.update",
        "roles_delete": "roles.delete",
        "user_roles_read": "user_roles.view",
        "user_roles_create": "user_roles.create",
        "user_roles_delete": "user_roles.delete",
    }

    def has_permission(self, request, view):
        user = request.user

        if not (user and user.is_authenticated and getattr(user, "is_active", False)):
            return False

        if getattr(user, "is_superuser", False):
            return True

        if not self.required_permission:
            return False

        perm_code = self.LEGACY_PERMISSION_MAP.get(
            self.required_permission, self.required_permission
        )
        return PermissionService.user_has_permission(user, perm_code)


class CanReadUsers(BaseRolePermission):
    """Deprecado: ``HasPermission("users.view")``."""

    required_permission = "users_read"
    message = "No tiene permisos para listar usuarios."


class CanCreateUsers(BaseRolePermission):
    """Deprecado: ``HasPermission("users.create")``."""

    required_permission = "users_create"
    message = "No tienes permisos para crear usuarios."


class CanUpdateUsers(BaseRolePermission):
    """Deprecado: ``HasPermission("users.update")``."""

    required_permission = "users_update"
    message = "No tiene permisos para actualizar usuarios."


class CanDeleteUsers(BaseRolePermission):
    """Deprecado: ``HasPermission("users.delete")``."""

    required_permission = "users_delete"
    message = "No tiene permisos para eliminar usuarios."


class CanReadUserRoles(BaseRolePermission):
    """Deprecado: ``HasPermission("user_roles.view")``."""

    required_permission = "user_roles_read"
    message = "No tiene permisos para consultar las asignaciones de roles."


class CanCreateUserRoles(BaseRolePermission):
    """Deprecado: ``HasPermission("user_roles.create")``."""

    required_permission = "user_roles_create"
    message = "No tiene permisos para crear asignaciones de roles."


class CanUpdateUserRoles(BaseRolePermission):
    """Deprecado: ``HasPermission("user_roles.update")``."""

    required_permission = "user_roles_update"
    message = "No tiene permisos para actualizar asignaciones de roles."


class CanDeleteUserRoles(BaseRolePermission):
    """Deprecado: ``HasPermission("user_roles.delete")``."""

    required_permission = "user_roles_delete"
    message = "No tiene permisos para eliminar asignaciones de roles."
