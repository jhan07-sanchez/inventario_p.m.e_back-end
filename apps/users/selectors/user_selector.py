from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from apps.core.selectors.base_selector import BaseSelector
from apps.users.models import User


class UserSelector(BaseSelector[User]):
    """
    Capa encargada exclusivamente de consultas
    sobre el modelo User.
    """

    def __init__(self):
        super().__init__(User)

    def get_queryset(self, include_deleted: bool = False) -> QuerySet[User]:
        return (
            super()
            .get_queryset(include_deleted=include_deleted)
            .prefetch_related("user_roles__role")
            .order_by("id_user")
        )

    @staticmethod
    def get_users():
        return UserSelector().get_all()

    @staticmethod
    def get_by_id(user_id: int, include_deleted: bool = False):
        return get_object_or_404(
            UserSelector().get_queryset(include_deleted=include_deleted),
            pk=user_id,
        )

    @staticmethod
    def get_by_username(username: str):
        return UserSelector().filter(username=username).first()

    @staticmethod
    def get_by_email(email: str):
        return UserSelector().filter(email=email).first()
