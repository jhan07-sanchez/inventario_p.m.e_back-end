from django.shortcuts import get_object_or_404

from apps.core.selectors.base_selector import BaseSelector
from apps.users.models import Role


class RoleSelector(BaseSelector[Role]):
    """
    Selector encargado de las consultas relacionadas con los roles.

    Los Selectors unicamente contienen logica de lectura.
    No deben crear, actualizar ni eliminar registros.
    """

    def __init__(self):
        super().__init__(Role)

    @staticmethod
    def get_roles():
        """
        Retorna todos los roles ordenados por nombre.
        """
        return RoleSelector().get_all().order_by("role_name")

    @staticmethod
    def get_active_roles():
        """
        Retorna únicamente los roles activos.
        """
        return RoleSelector().get_active().order_by("role_name")

    @staticmethod
    def get_role_by_id(id_role: int, include_deleted: bool = False) -> Role:
        """
        Obtiene un rol por su identificador.

        Lanza un 404 si no existe.
        """
        return get_object_or_404(
            RoleSelector().get_queryset(include_deleted=include_deleted),
            id_role=id_role,
        )

    @staticmethod
    def role_exists(role_name: str) -> bool:
        """
        Verifica si ya existe un rol con el mismo nombre.
        """
        return RoleSelector().exists(role_name__iexact=role_name)
