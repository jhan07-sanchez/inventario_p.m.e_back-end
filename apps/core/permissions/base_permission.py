from rest_framework.permissions import BasePermission

from apps.core.security.services.permission_service import PermissionService


class BaseRolePermission(BasePermission):
    """
    Clase base para compatibilidad con permisos legados.
    Se traduce dinámicamente al sistema moderno de PermissionService.
    """

    required_permission: str | None = None
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

    def has_permission(self, request, view) -> bool:
        if not (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "is_active", False)
        ):
            return False

        if getattr(request.user, "is_superuser", False):
            return True

        if not self.required_permission:
            return False

        perm_code = self.LEGACY_PERMISSION_MAP.get(
            self.required_permission, self.required_permission
        )
        return PermissionService.user_has_permission(request.user, perm_code)
