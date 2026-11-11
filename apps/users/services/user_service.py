from django.db import transaction

from apps.core.exceptions.custom_exceptions import (
    DocumentAlreadyExistsException,
    EmailAlreadyExistsException,
    UserAlreadyExistsException,
    UserInactiveException,
)
from apps.core.services.base_service import BaseService
from apps.users.models import Role, User, UserRole, CompanyMembership

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
        company_id = data.pop("company_id", None)
        password = data.pop("password")
        roles_ids = data.pop("roles", [])

        if "email" in data and data["email"]:
            data["email"] = data["email"].strip().lower()
        user = User(**data)
        user.set_password(password)
        user.full_clean()
        user.save()

        if company_id:
            if roles_ids:
                role = Role.objects.filter(id_role__in=roles_ids, company_id=company_id, is_active=True).first()
                if role:
                    CompanyMembership.objects.create(
                        user=user,
                        company_id=company_id,
                        role=role,
                        status=CompanyMembership.MembershipStatus.ACTIVE,
                        is_owner=False,
                    )
            else:
                CompanyMembership.objects.create(
                    user=user,
                    company_id=company_id,
                    role=None,
                    status=CompanyMembership.MembershipStatus.ACTIVE,
                )
        return user

    def perform_update(self, instance: User, data: dict) -> User:
        company_id = data.pop("company_id", None)
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



        if roles_ids is not None and company_id:
            membership = CompanyMembership.objects.filter(
                user=instance, company_id=company_id
            ).first()

            if membership:
                if roles_ids:
                    role = Role.objects.filter(
                        id_role__in=roles_ids, company_id=company_id
                    ).first()
                    if role:
                        membership.role = role
                        membership.save()
                else:
                    membership.is_active = False
                    membership.save()
            elif roles_ids:
                role = Role.objects.filter(
                    id_role__in=roles_ids, company_id=company_id
                ).first()
                if role:
                    CompanyMembership.objects.create(
                        user=instance, company_id=company_id, role=role, status="ACTIVE"
                    )

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
    def create_user(company_id: int | None, validated_data: dict) -> User:
        """
        Crea un nuevo usuario aplicando las reglas de negocio.
        """
        return UserService().create(
            company_id=company_id,
            **validated_data
        )

    @staticmethod
    @transaction.atomic
    def update_user(user: User, company_id: int, validated_data: dict) -> User:
        """
        Actualiza un usuario aplicando las reglas de negocio.
        """
        return UserService().update(user, company_id=company_id, **validated_data)

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
