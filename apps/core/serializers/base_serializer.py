"""
Serializadores base con protección estricta Multi-Tenant y prevención de Mass Assignment.
Garantiza que ningún cliente pueda inyectar o modificar la empresa (company_id) a través del payload.
"""

from typing import Any
from rest_framework import serializers


class TenantSerializerMixin:
    """
    Mixin para serializadores que manejan entidades multi-tenant.
    Responsabilidades:
    1. Blindar 'company' y 'company_id' para que sean estrictamente read_only.
    2. Eliminar cualquier intento de inyección de empresa en el payload (Mass Assignment).
    3. Inyectar automáticamente el company_id activo en validated_data.
    """

    def get_fields(self):
        fields = super().get_fields()
        # Asegurar que company y company_id sean siempre read_only si están expuestos
        for field_name in ("company", "company_id"):
            if field_name in fields:
                fields[field_name].read_only = True
        return fields

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        """
        Interpreta los datos de entrada eliminando de raíz cualquier intento de
        especificar la empresa por payload HTTP.
        """
        if isinstance(data, dict):
            # Clonamos para no mutar el diccionario original de request.data si fuera inmutable
            data = data.copy()
            data.pop("company", None)
            data.pop("company_id", None)
        return super().to_internal_value(data)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Inyecta el company_id del request activo en validated_data si el modelo lo requiere.
        """
        attrs = super().validate(attrs)
        request = self.context.get("request")
        if request and hasattr(request, "company_id") and request.company_id:
            model = getattr(self.Meta, "model", None) if hasattr(self, "Meta") else None
            if model:
                model_fields = [f.name for f in getattr(model._meta, "fields", [])]
                if "company" in model_fields or "company_id" in model_fields:
                    attrs["company_id"] = request.company_id
        return attrs


class BaseModelSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    """
    Serializador de modelo base para toda la plataforma.
    Aplica protección multi-tenant y estandarización de campos.
    """
    pass

