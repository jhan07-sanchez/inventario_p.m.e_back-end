from rest_framework.permissions import BasePermission


class IsSaaSAdmin(BasePermission):
    """
    Permiso estricto para el dueño del SaaS.
    Solo los superusuarios pueden acceder a los endpoints de administración global.
    """

    message = "Acceso denegado. Se requieren privilegios de Superadministrador SaaS."

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.is_superuser
        )
