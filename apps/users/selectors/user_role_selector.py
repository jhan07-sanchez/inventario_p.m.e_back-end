from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from apps.core.selectors.base_selector import BaseSelector
from apps.users.models import UserRole


class UserRoleSelector(BaseSelector[UserRole]):
    """
    Selector encargado de las consultas relacionadas
    con la asignacion de roles a usuarios.

    Los selectors unicamente contienen logica de lectura
    """

    def __init__(self):
        super().__init__(UserRole)

    def get_queryset(self, include_deleted: bool = False) -> QuerySet[UserRole]:
        """
        Sobreescribimos get_queryset para asegurar que todas las consultas
        hereden la optimización de select_related y el orden por defecto.
        """
        return (
            super()
            .get_queryset(include_deleted=include_deleted)
            .select_related("user", "role")
            .order_by("id_user_role")
        )

    @staticmethod
    def get_user_roles():
        """
        Retorna todas las asignaciones de roles.
        """
        return UserRoleSelector().get_all()

    @staticmethod
    def get_active_user_roles():
        """
        Retorna unicamente las asignaciones activas.
        """
        return UserRoleSelector().get_active()

    @staticmethod
    def get_by_id(id_user_role: int, include_deleted: bool = False) -> UserRole:
        """
        Obtiene una asignacion por su identificador.
        """
        return get_object_or_404(
            UserRoleSelector().get_queryset(include_deleted=include_deleted),
            id_user_role=id_user_role,
        )

    @staticmethod
    def assignment_exists(
        user_id: int,
        role_id: int,
    ) -> bool:
        """
        Verifica si un usuario ya posee
        un rol determinado.
        """
        return UserRoleSelector().exists(
            user_id=user_id,
            role_id=role_id,
        )

    @staticmethod
    def filter_user_roles(
        *,
        user=None,
        role=None,
        is_active=None,
    ) -> QuerySet:
        """
        Retorna las asignaciones aplicando filtros opcionales.
        """
        kwargs = {}
        if user:
            kwargs["user_id"] = user
        if role:
            kwargs["role_id"] = role
        qs = UserRole.all_objects.select_related("user", "role").order_by(
            "id_user_role"
        )

        if is_active is not None:
            kwargs["deleted_at__isnull"] = is_active

        return UserRoleSelector().filter(qs=qs, **kwargs).order_by("-created_at")
