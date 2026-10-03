from django.db import transaction
from django.core.cache import cache

from apps.core.exceptions.custom_exceptions import (
    RoleInactiveException,
    UserInactiveException,
    UserRoleAlreadyExistsException,
)
from apps.core.services.base_service import BaseService
from apps.users.models import UserRole


class UserRoleService(BaseService[UserRole]):
    """
    Servicio encargado de la lógica de negocio relacionada
    con la asignación de roles a usuarios.
    """

    def __init__(self):
        super().__init__(UserRole)

    def validate(self, data: dict, instance=None) -> dict:
        user = data.get("user")
        role = data.get("role")

        # Validar que el rol esté activo
        target_role = role if role else (instance.role if instance else None)
        if target_role and not target_role.is_active:
            raise RoleInactiveException()

        # Validar que el usuario esté activo
        target_user = user if user else (instance.user if instance else None)
        if target_user and not target_user.is_active:
            raise UserInactiveException()

        if instance is None:
            if user and role:
                existing = UserRole.all_objects.filter(user=user, role=role).first()
                if existing:
                    if existing.deleted_at is None:
                        raise UserRoleAlreadyExistsException()
                    else:
                        data["_existing_assignment"] = existing
        else:
            current_user = user if user else instance.user
            current_role = role if role else instance.role

            exists = (
                UserRole.objects.filter(
                    user=current_user,
                    role=current_role,
                )
                .exclude(
                    pk=instance.pk,
                )
                .exists()
            )

            if exists:
                raise UserRoleAlreadyExistsException()

        return data

    def perform_create(self, data: dict) -> UserRole:
        existing = data.pop("_existing_assignment", None)
        if existing:
            existing.restore()
            return existing

        user_role = UserRole(**data)
        user_role.full_clean()
        user_role.save()
        return user_role

    def perform_update(self, instance: UserRole, data: dict) -> UserRole:
        for field, value in data.items():
            setattr(
                instance,
                field,
                value,
            )
        instance.full_clean()
        instance.save()
        return instance

    @staticmethod
    @transaction.atomic
    def create_user_role(validated_data: dict) -> UserRole:
        """
        Asigna un rol a un usuario.
        """
        user_role = UserRoleService().create(**validated_data)
        cache.delete(f"user_permissions_{user_role.user_id}")
        return user_role

    @staticmethod
    @transaction.atomic
    def update_user_role(
        user_role: UserRole,
        validated_data: dict,
    ) -> UserRole:
        """
        Actualiza una asignación de rol.
        """
        user_role = UserRoleService().update(user_role, **validated_data)
        cache.delete(f"user_permissions_{user_role.user_id}")
        return user_role

    @staticmethod
    @transaction.atomic
    def deactivate_user_role(
        user_role: UserRole,
    ) -> UserRole:
        """
        Desactiva una asignación.
        """
        UserRoleService().delete(user_role)
        cache.delete(f"user_permissions_{user_role.user_id}")
        return user_role

    @staticmethod
    @transaction.atomic
    def restore_user_role(
        user_role: UserRole,
    ) -> UserRole:
        """
        Restaura una asignación.
        """
        user_role.restore()
        cache.delete(f"user_permissions_{user_role.user_id}")
        return user_role
