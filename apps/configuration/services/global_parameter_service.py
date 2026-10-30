import re
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any, Optional

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

if TYPE_CHECKING:
    from apps.users.models import User


class GlobalParameterService(BaseService[GlobalParameter]):
    """
    Servicio encargado de la lógica de negocio de los parámetros globales.
    Garantiza tipado estricto, integridad de valores, consistencia de caché y auditoría.
    """

    KEY_PATTERN = re.compile(r"^[A-Z0-9_]+$")

    def __init__(self):
        super().__init__(GlobalParameter)

    @staticmethod
    def validate_value_by_data_type(value: Any, data_type: str) -> None:
        """
        Valida que el valor coincida de forma estricta con el tipo de dato esperado.
        Rechaza valores ambiguos, nulos o no serializables.
        """
        if data_type not in GlobalParameter.DataType.values:
            raise ValidationError(
                f"El tipo de dato '{data_type}' no está soportado en el sistema."
            )

        if value is None:
            raise ValidationError("El valor del parámetro no puede ser nulo.")

        try:
            if data_type == GlobalParameter.DataType.INTEGER:
                if isinstance(value, bool):
                    raise ValueError("Un booleano no es un entero válido.")
                v_str = str(value).strip()
                int(v_str)

            elif data_type == GlobalParameter.DataType.DECIMAL:
                if isinstance(value, bool):
                    raise ValueError("Un booleano no es un decimal válido.")
                v_str = str(value).strip()
                d = Decimal(v_str)
                if d.is_nan() or d.is_infinite():
                    raise ValueError("Valor decimal inválido o infinito.")

            elif data_type == GlobalParameter.DataType.BOOLEAN:
                if isinstance(value, bool):
                    return
                v_str = str(value).strip().lower()
                if v_str not in ["true", "false", "1", "0", "t", "f", "yes", "no", "si"]:
                    raise ValueError("Valor no reconocido como booleano.")

            elif data_type == GlobalParameter.DataType.STRING:
                # El valor debe ser representable como texto no nulo
                pass

        except (ValueError, InvalidOperation, TypeError):
            raise ValidationError(
                f"El valor '{value}' no es válido para el tipo de dato '{data_type}'."
            )

    @staticmethod
    def cast_value(value: Any, data_type: str) -> Any:
        """
        Convierte el valor textual o nativo al tipo correspondiente de Python.
        """
        if value is None:
            return None
        try:
            if data_type == GlobalParameter.DataType.INTEGER:
                return int(str(value).strip())
            if data_type == GlobalParameter.DataType.DECIMAL:
                return Decimal(str(value).strip())
            if data_type == GlobalParameter.DataType.BOOLEAN:
                if isinstance(value, bool):
                    return value
                return str(value).strip().lower() in ("true", "1", "t", "yes", "si")
            return str(value)
        except (ValueError, InvalidOperation, TypeError):
            return value

    @staticmethod
    def get_typed_value(key: str, default=None) -> Any:
        """
        Obtiene el valor tipado en Python para un parámetro a partir de su clave.
        Si el parámetro no existe en base de datos o está inactivo:
          1. Retorna el 'default' si fue provisto explícitamente.
          2. Consulta el catálogo predeterminado del sistema como fallback de resiliencia.
        """
        from apps.configuration.selectors.global_parameter_selector import (
            GlobalParameterSelector,
        )

        norm_key = key.strip().upper() if key else key
        param = GlobalParameterSelector.get_by_key(norm_key)

        if param and param.is_active:
            return GlobalParameterService.cast_value(param.value, param.data_type)

        if default is not None:
            return default

        # Fallback a catálogo si no se especificó un default explícito
        from apps.configuration.constants import SYSTEM_PARAMETERS_CATALOG

        cat_entry = SYSTEM_PARAMETERS_CATALOG.get(norm_key)
        if cat_entry:
            return GlobalParameterService.cast_value(
                cat_entry["default"], cat_entry["data_type"]
            )

        return None

    @staticmethod
    def get_catalog() -> dict:
        """
        Retorna el catálogo predefinido y categorizado de parámetros del ERP.
        """
        from apps.configuration.constants import SYSTEM_PARAMETERS_CATALOG

        return SYSTEM_PARAMETERS_CATALOG

    @staticmethod
    @transaction.atomic
    def create_parameter(
        dto: GlobalParameterCreateDto, user: Optional["User"] = None
    ) -> GlobalParameter:
        """
        Crea un nuevo parámetro global en el sistema, valida su formato e invariantes
        y registra la auditoría de cambios.
        """
        norm_key = dto.key.strip().upper()

        if not GlobalParameterService.KEY_PATTERN.match(norm_key):
            raise ValidationError(
                "La clave del parámetro solo puede contener letras mayúsculas, números y guiones bajos."
            )

        if GlobalParameter.objects.filter(key=norm_key).exists():
            raise GlobalParameterAlreadyExistsException()

        GlobalParameterService.validate_value_by_data_type(dto.value, dto.data_type)

        parameter = GlobalParameter.objects.create(
            key=norm_key,
            value=str(dto.value).strip(),
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

        cache_key = f"global_param_{norm_key}"
        cache.delete(cache_key)

        return parameter

    @staticmethod
    @transaction.atomic
    def update_parameter(
        parameter: GlobalParameter,
        dto: GlobalParameterUpdateDto,
        user: Optional["User"] = None,
    ) -> GlobalParameter:
        """
        Actualiza los campos permitidos de un parámetro existente, asegurando
        la consistencia cruzada entre valor y tipo de dato.
        """
        update_fields = ["updated_at"]
        old_value = parameter.value
        old_data_type = parameter.data_type
        final_data_type = (
            dto.data_type if dto.data_type is not None else parameter.data_type
        )
        final_value = (
            str(dto.value).strip() if dto.value is not None else parameter.value
        )
        has_changes = False

        if dto.value is not None and str(dto.value).strip() != parameter.value:
            parameter.value = str(dto.value).strip()
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

        if not has_changes:
            return parameter

        # Validación cruzada obligatoria: asegura que el valor existente sea compatible con el nuevo tipo
        GlobalParameterService.validate_value_by_data_type(
            final_value, final_data_type
        )

        parameter.full_clean()
        parameter.save(update_fields=update_fields)

        # Registrar auditoría de actualización
        if old_value != parameter.value or old_data_type != parameter.data_type:
            reason = (
                "Actualización de valor."
                if old_value != parameter.value
                else "Actualización de tipo de dato."
            )
            ConfigurationAudit.objects.create(
                parameter=parameter,
                parameter_key=parameter.key,
                action=ConfigurationAudit.Action.UPDATE,
                user=user,
                old_value=old_value,
                new_value=parameter.value,
                reason=reason,
            )

        param_key = parameter.key
        cache.delete(f"global_param_{param_key}")
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
        param_key = parameter.key
        cache.delete(f"global_param_{param_key}")

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
        param_key = restored.key
        cache.delete(f"global_param_{param_key}")

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

