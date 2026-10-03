from __future__ import annotations

from typing import Any

from django.core.cache import cache
from django.db import transaction

from apps.core.exceptions.custom_exceptions import (
    InvalidRolePermissionsException,
    RoleAlreadyExistsException,
    RoleInactiveException,
)
from apps.core.security.registry import SecurityRegistry
from apps.core.services.base_service import BaseService
from apps.users.models import Role


class RoleService(BaseService[Role]):
    """
    Servicio encargado de la lógica de negocio relacionada
    con los roles.

    Responsabilidades:

    - Validar nombres de roles.
    - Validar permisos dinámicos.
    - Crear roles.
    - Actualizar roles.
    - Desactivar roles.
    - Restaurar roles.
    - Garantizar que los permisos provengan del
      SecurityRegistry.
    """

    def __init__(self) -> None:
        super().__init__(Role)

    def validate(
        self,
        data: dict[str, Any],
        instance: Role | None = None,
    ) -> dict[str, Any]:
        """
        Ejecuta las validaciones de negocio del rol.

        Args:
            data:
                Datos que serán utilizados para crear o actualizar
                el rol.

            instance:
                Instancia existente cuando se está actualizando
                un rol.

        Returns:
            Los datos validados.

        Raises:
            RoleAlreadyExistsException:
                Si el nombre del rol ya existe.

            InvalidRolePermissionsException:
                Si los permisos enviados no son válidos.
        """

        self._validate_role_name(
            role_name=data.get("role_name"),
            instance=instance,
        )

        self._validate_permissions(
            permissions=data.get("permissions"),
        )

        return data

    @staticmethod
    def _validate_role_name(
        role_name: str | None,
        instance: Role | None = None,
    ) -> None:
        """
        Valida que el nombre del rol sea único.

        La comparación se realiza sin distinguir mayúsculas
        y minúsculas.
        """

        if not role_name:
            return

        queryset = Role.objects.filter(
            role_name__iexact=role_name,
        )

        if instance is not None:
            queryset = queryset.exclude(
                pk=instance.pk,
            )

        if queryset.exists():
            raise RoleAlreadyExistsException()

    @staticmethod
    def _validate_permissions(
        permissions: dict[str, bool] | None,
    ) -> None:
        """
        Valida los permisos dinámicos asignados al rol.

        Los códigos permitidos son exclusivamente los registrados
        en SecurityRegistry.

        Formato esperado:

        {
            "users.view": True,
            "users.create": True,
            "sales.view": True,
        }

        Args:
            permissions:
                Diccionario de permisos dinámicos.

        Raises:
            InvalidRolePermissionsException:
                Si el formato es incorrecto, existe un código
                no registrado o un valor que no es booleano.
        """

        if permissions is None:
            return

        if not isinstance(permissions, dict):
            raise InvalidRolePermissionsException()

        valid_codes = set(SecurityRegistry.get_all_security_codes())

        invalid_codes = [code for code in permissions if code not in valid_codes]

        if invalid_codes:
            raise InvalidRolePermissionsException()

        invalid_values = [
            code for code, value in permissions.items() if not isinstance(value, bool)
        ]

        if invalid_values:
            raise InvalidRolePermissionsException()

    def perform_create(
        self,
        data: dict[str, Any],
    ) -> Role:
        """
        Crea físicamente un nuevo rol.

        La validación de negocio se ejecuta antes mediante
        BaseService.create().
        """

        role = Role(**data)

        role.full_clean()
        role.save()

        return role

    def perform_update(
        self,
        instance: Role,
        data: dict[str, Any],
    ) -> Role:
        """
        Actualiza físicamente un rol existente.

        La validación de negocio se ejecuta antes mediante
        BaseService.update().
        """

        for field, value in data.items():
            setattr(instance, field, value)

        instance.full_clean()
        instance.save()

        return instance

    def perform_delete(
        self,
        instance: Role,
        soft_delete: bool = True,
    ) -> None:
        """
        Desactiva un rol mediante borrado lógico.

        Args:
            instance:
                Rol que será desactivado.

            soft_delete:
                Controla si se ejecuta el mecanismo de borrado
                lógico definido por BaseService.
        """

        if not instance.is_active:
            raise RoleInactiveException()

        instance.is_active = False

        instance.full_clean()

        instance.save(
            update_fields=[
                "is_active",
                "updated_at",
            ],
        )

        if soft_delete:
            instance.delete()

    @staticmethod
    @transaction.atomic
    def create_role(
        validated_data: dict[str, Any],
    ) -> Role:
        """
        Crea un nuevo rol aplicando las reglas de negocio.
        """

        return RoleService().create(
            **validated_data,
        )

    @staticmethod
    @transaction.atomic
    def update_role(
        role: Role,
        validated_data: dict[str, Any],
    ) -> Role:
        """
        Actualiza un rol aplicando las reglas de negocio.
        """

        role = RoleService().update(
            role,
            **validated_data,
        )
        cache.clear()
        return role

    @staticmethod
    @transaction.atomic
    def deactivate_role(
        role: Role,
    ) -> Role:
        """
        Realiza el borrado lógico de un rol.

        El registro permanece en la base de datos.
        """

        RoleService().delete(
            role,
            soft_delete=False,
        )
        cache.clear()
        return role

    @staticmethod
    @transaction.atomic
    def restore_role(
        role: Role,
    ) -> Role:
        """
        Reactiva un rol previamente desactivado.
        """

        role.is_active = True

        role.save(
            update_fields=[
                "is_active",
                "updated_at",
            ],
        )

        role.restore()
        cache.clear()
        return role
