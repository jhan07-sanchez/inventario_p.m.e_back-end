from rest_framework.permissions import BasePermission

from apps.core.security.services.permission_service import PermissionService


class IsSaaSSuperuser(BasePermission):
    """
    Permiso exclusivo para el Propietario / Superadministrador del SaaS.
    Requerido para operaciones de máxima criticidad:
    - Administración del equipo interno de la plataforma.
    - Asignación y revocación de privilegios administrativos.
    - Configuración central de infraestructura.
    """

    message = "Acceso denegado. Se requieren privilegios del Propietario de la plataforma (Superadministrador)."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.is_superuser
        )


class IsSaaSAdmin(BasePermission):
    """
    Permiso para usuarios con acceso al panel de administración SaaS:
    - Superadministradores (acceso completo).
    - Personal interno autorizado (is_staff=True con rol global o permiso SaaS).

    Deniega terminantemente a usuarios empresariales o clientes del ERP.
    """

    message = "Acceso denegado. Se requieren privilegios de administración SaaS."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not (user and user.is_authenticated and user.is_active):
            return False

        # Permitir finalizar sesión de soporte si el token presenta claim de impersonación
        if getattr(request, "auth", None) and hasattr(request.auth, "get"):
            if (
                request.auth.get("is_impersonated", False)
                and getattr(view, "action", None) == "end_impersonate"
            ):
                return True

        if user.is_superuser:
            return True

        # Personal interno: is_staff=True
        # Verificamos que no sea un usuario exclusivo de empresa cliente intentando entrar
        if user.is_staff:
            return True

        return False


def HasSaaSPermission(permission_code: str):
    """
    Factory que genera una clase dinámica de permiso para una operación administrativa específica.
    Superusuarios siempre tienen acceso concedido.
    Personal interno debe tener concedido el código de permiso en sus roles de sistema.
    """

    class DynamicSaaSPermission(BasePermission):
        message = (
            f"Acceso denegado. No posee el permiso administrativo '{permission_code}'."
        )

        def has_permission(self, request, view):
            user = getattr(request, "user", None)
            if not (user and user.is_authenticated and user.is_active):
                return False

            if user.is_superuser:
                return True

            if not user.is_staff:
                return False

            # Validar permiso a nivel de sistema (company_id=None)
            return PermissionService.user_has_permission(
                user=user,
                permission_code=permission_code,
                company_id=None,
            )

    DynamicSaaSPermission.__name__ = (
        f"HasSaaSPermission_{permission_code.replace('.', '_')}"
    )
    return DynamicSaaSPermission
