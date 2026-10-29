from decimal import Decimal, InvalidOperation
from typing import Optional

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.configuration.dto import GlobalParameterCreateDto, GlobalParameterUpdateDto
from apps.configuration.models import ConfigurationAudit, GlobalParameter
from apps.core.exceptions.custom_exceptions import (
    GlobalParameterAlreadyExistsException,
    GlobalParameterInactiveException,
)
from apps.core.services.base_service import BaseService
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.users.models import User


class GlobalParameterService(BaseService[GlobalParameter]):
    """
    Servicio encargado de la lógica de negocio de los parámetros globales.
    Incluye auditoría de cambios.
    """

    def __init__(self):
        super().__init__(GlobalParameter)

    @staticmethod
    def validate_value_by_data_type(value: str, data_type: str) -> None:
        """
        Valida que el string del valor coincida con el tipo de dato esperado.
        """
        try:
            if data_type == GlobalParameter.DataType.INTEGER:
                int(value)
            elif data_type == GlobalParameter.DataType.DECIMAL:
                Decimal(value)
            elif data_type == GlobalParameter.DataType.BOOLEAN:
                if value.lower() not in ["true", "false", "1", "0"]:
                    raise ValueError()
        except (ValueError, InvalidOperation):
            raise ValidationError(
                f"El valor '{value}' no es válido para el tipo de dato '{data_type}'."
            )

    @staticmethod
    def cast_value(value: str, data_type: str):
        """
        Convierte el valor textual al tipo nativo de Python correspondiente.
        """
        if value is None:
            return None
        try:
            if data_type == GlobalParameter.DataType.INTEGER:
                return int(value)
            if data_type == GlobalParameter.DataType.DECIMAL:
                return Decimal(value)
            if data_type == GlobalParameter.DataType.BOOLEAN:
                return value.lower() in ("true", "1")
            return str(value)
        except (ValueError, InvalidOperation):
            return value

    @staticmethod
    def get_typed_value(key: str, default=None):
        """
        Obtiene el valor tipado en Python para un parámetro a partir de su clave.
        Si el parámetro no existe o está inactivo, retorna el valor default.
        """
        from apps.configuration.selectors.global_parameter_selector import (
            GlobalParameterSelector,
        )

        param = GlobalParameterSelector.get_by_key(key)
        if not param or not param.is_active:
            return default

        return GlobalParameterService.cast_value(param.value, param.data_type)

    @staticmethod
    def get_catalog() -> dict:
        """
        Retorna el catálogo predefinido de parámetros del ERP.
        """
        from apps.configuration.constants import SYSTEM_PARAMETERS_CATALOG

        return SYSTEM_PARAMETERS_CATALOG

    @staticmethod
    @transaction.atomic
    def create_parameter(
        dto: GlobalParameterCreateDto, user: Optional["User"] = None
    ) -> GlobalParameter:
        """
        Crea un nuevo parámetro global en el sistema y registra la auditoría.
        """
        if GlobalParameter.objects.filter(key=dto.key).exists():
            raise GlobalParameterAlreadyExistsException()

        GlobalParameterService.validate_value_by_data_type(dto.value, dto.data_type)

        parameter = GlobalParameter.objects.create(
            key=dto.key,
            value=dto.value,
            data_type=dto.data_type,
            description=dto.description or "",
        )

        # Registrar auditoría de creación
        ConfigurationAudit.objects.create(
            parameter=parameter,
            parameter_key=parameter.key,
            action=ConfigurationAudit.Action.CREATE,
            user=user,
            old_value=None,
            new_value=parameter.value,
            reason="Creación inicial del parámetro.",
        )

        return parameter

    @staticmethod
    @transaction.atomic
    def update_parameter(
        parameter: GlobalParameter,
        dto: GlobalParameterUpdateDto,
        user: Optional["User"] = None,
    ) -> GlobalParameter:
        """
        Actualiza los campos permitidos de un parámetro existente y registra la auditoría.
        """
        update_fields = ["updated_at"]
        old_value = parameter.value
        final_data_type = (
            dto.data_type if dto.data_type is not None else parameter.data_type
        )
        has_changes = False

        if dto.value is not None and dto.value != parameter.value:
            GlobalParameterService.validate_value_by_data_type(
                dto.value, final_data_type
            )
            parameter.value = dto.value
            update_fields.append("value")
            has_changes = True

        if dto.data_type is not None and dto.data_type != parameter.data_type:
            parameter.data_type = dto.data_type
            update_fields.append("data_type")
            has_changes = True

        if dto.description is not None and dto.description != parameter.description:
            parameter.description = dto.description
            update_fields.append("description")
            has_changes = True

        # Si no hubo cambios reales, no hacemos nada
        if not has_changes:
            return parameter

        parameter.full_clean()
        parameter.save(update_fields=update_fields)

        # Registrar auditoría de actualización (solo si el valor cambió)
        if old_value != parameter.value:
            ConfigurationAudit.objects.create(
                parameter=parameter,
                parameter_key=parameter.key,
                action=ConfigurationAudit.Action.UPDATE,
                user=user,
                old_value=old_value,
                new_value=parameter.value,
                reason="Actualización de valor.",
            )

        cache.delete(f"global_param_{parameter.key}")
        return parameter

    @staticmethod
    @transaction.atomic
    def deactivate_parameter(
        parameter: GlobalParameter, user: Optional["User"] = None
    ) -> None:
        """
        Realiza un borrado lógico del parámetro y registra la auditoría.
        """
        if not parameter.is_active:
            raise GlobalParameterInactiveException()

        GlobalParameterService().delete(parameter)
        cache.delete(f"global_param_{parameter.key}")

        # Registrar auditoría de desactivación
        ConfigurationAudit.objects.create(
            parameter=parameter,
            parameter_key=parameter.key,
            action=ConfigurationAudit.Action.DEACTIVATE,
            user=user,
            old_value=parameter.value,
            new_value=None,
            reason="Desactivación del parámetro.",
        )

    @staticmethod
    @transaction.atomic
    def restore_parameter(
        parameter: GlobalParameter, user: Optional["User"] = None
    ) -> GlobalParameter:
        """
        Restaura un parámetro previamente desactivado y registra la auditoría.
        """
        if parameter.is_active:
            return parameter

        restored = GlobalParameterService().restore(parameter)
        cache.delete(f"global_param_{restored.key}")

        # Registrar auditoría de restauración
        ConfigurationAudit.objects.create(
            parameter=restored,
            parameter_key=restored.key,
            action=ConfigurationAudit.Action.RESTORE,
            user=user,
            old_value=None,
            new_value=restored.value,
            reason="Restauración del parámetro.",
        )

        return restored
