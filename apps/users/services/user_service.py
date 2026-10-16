from django.db import transaction

from apps.core.exceptions.custom_exceptions import (
    DocumentAlreadyExistsException,
    EmailAlreadyExistsException,
    UserAlreadyExistsException,
    UserInactiveException,
)
from apps.core.services.base_service import BaseService
from apps.users.models import Role, User, UserRole


class UserService(BaseService[User]):
    """
    Servicio encargado de la lógica de negocio relacionada con los usuarios.
    """

    def __init__(self):
        super().__init__(User)

    def validate(self, data: dict, instance=None) -> dict:
        username = data.get("username")
        email = data.get("email")
        document_number = data.get("document_number")

        user_mgr = getattr(User, "all_objects", User.objects)

        if instance is None:
            if username and user_mgr.filter(username=username).exists():
                raise UserAlreadyExistsException()

            if email and user_mgr.filter(email=email).exists():
                raise EmailAlreadyExistsException()

            if (
                document_number
                and user_mgr.filter(document_number=document_number).exists()
            ):
                raise DocumentAlreadyExistsException()
        else:
            if (
                username
                and user_mgr.filter(username=username).exclude(pk=instance.pk).exists()
            ):
                raise UserAlreadyExistsException()

            if email and user_mgr.filter(email=email).exclude(pk=instance.pk).exists():
                raise EmailAlreadyExistsException()

            if (
                document_number
                and user_mgr.filter(document_number=document_number)
                .exclude(pk=instance.pk)
                .exists()
            ):
                raise DocumentAlreadyExistsException()

        return data

    def perform_create(self, data: dict) -> User:
        password = data.pop("password")
        roles_ids = data.pop("roles", [])

        if "email" in data and data["email"]:
            data["email"] = data["email"].strip().lower()
        user = User(**data)
        user.set_password(password)
        user.full_clean()
        user.save()

        if roles_ids:
            roles = Role.objects.filter(id_role__in=roles_ids, is_active=True)
            for role in roles:
                UserRole.objects.create(user=user, role=role)

        return user

    def perform_update(self, instance: User, data: dict) -> User:
        password = data.pop("password", None)
        roles_ids = data.pop("roles", None)

        if "email" in data and data["email"]:
            data["email"] = data["email"].strip().lower()

        for field, value in data.items():
            setattr(instance, field, value)

        if password:
            instance.set_password(password)

        instance.full_clean()
        instance.save()

        if roles_ids is not None:
            # Eliminar roles existentes y asignar los nuevos
            UserRole.objects.filter(user=instance).delete()
            if roles_ids:
                roles = Role.objects.filter(id_role__in=roles_ids, is_active=True)
                for role in roles:
                    UserRole.objects.create(user=instance, role=role)

            from apps.core.security.services.permission_service import PermissionService

            PermissionService.invalidate_user_cache(instance.pk)

        return instance

    def perform_delete(self, instance: User, soft_delete: bool = True) -> None:
        if not instance.is_active:
            raise UserInactiveException()

        if soft_delete:
            instance.delete()
        else:
            if hasattr(instance, "hard_delete"):
                instance.hard_delete()
            else:
                instance.delete()

        from apps.core.security.services.permission_service import PermissionService

        PermissionService.invalidate_user_cache(instance.pk)

    @staticmethod
    @transaction.atomic
    def create_user(validated_data: dict) -> User:
        """
        Crea un nuevo usuario aplicando las reglas de negocio.
        """
        return UserService().create(**validated_data)

    @staticmethod
    @transaction.atomic
    def update_user(user: User, validated_data: dict) -> User:
        """
        Actualiza un usuario aplicando las reglas de negocio.
        """
        return UserService().update(user, **validated_data)

    @staticmethod
    @transaction.atomic
    def deactivate_user(user: User) -> User:
        """
        Realiza el borrado lógico de un usuario.

        No elimina el registro físicamente de la base de datos.
        Cambia el estado del usuario a inactivo y registra la fecha de borrado.
        """
        UserService().delete(user, soft_delete=True)
        return user

    @staticmethod
    @transaction.atomic
    def restore_user(user: User) -> User:
        """
        Reactiva un usuario previamente desactivado.
        """
        restored = UserService().restore(user)
        from apps.core.security.services.permission_service import PermissionService

        PermissionService.invalidate_user_cache(user.pk)
        return restored
