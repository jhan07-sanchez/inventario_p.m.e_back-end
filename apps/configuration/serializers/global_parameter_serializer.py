import re

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.configuration.dto import GlobalParameterCreateDto, GlobalParameterUpdateDto
from apps.configuration.models import GlobalParameter


class GlobalParameterSerializer(serializers.ModelSerializer):
    """
    Serializer utilizado para representar la información completa
    de un parámetro global.
    """

    class Meta:
        model = GlobalParameter
        fields = (
            "id_parameter",
            "key",
            "value",
            "data_type",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        )


class GlobalParameterCreateSerializer(serializers.Serializer):
    """
    Serializer utilizado para crear un parámetro global con validaciones estrictas.
    """

    key = serializers.CharField(
        max_length=100,
        required=True,
    )
    value = serializers.CharField(
        required=True,
    )
    data_type = serializers.ChoiceField(
        choices=GlobalParameter.DataType.choices,
        required=True,
    )
    description = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
        default="",
    )

    def validate_key(self, value: str) -> str:
        norm_key = value.strip().upper()
        if not re.match(r"^[A-Z0-9_]+$", norm_key):
            raise serializers.ValidationError(
                "La clave solo puede contener letras mayúsculas, números y guiones bajos."
            )
        return norm_key

    def validate(self, attrs: dict) -> dict:
        from apps.configuration.services.global_parameter_service import (
            GlobalParameterService,
        )

        try:
            GlobalParameterService.validate_value_by_data_type(
                attrs["value"], attrs["data_type"]
            )
        except DjangoValidationError as exc:
            msg = exc.messages[0] if hasattr(exc, "messages") else str(exc)
            raise serializers.ValidationError({"value": msg})

        return attrs

    def to_dto(self) -> GlobalParameterCreateDto:
        """Convierte los datos validados en un DTO."""
        v = self.validated_data
        return GlobalParameterCreateDto(
            key=v["key"],
            value=v["value"],
            data_type=v["data_type"],
            description=v.get("description", ""),
        )


class GlobalParameterUpdateSerializer(serializers.Serializer):
    """
    Serializer utilizado para actualizar un parámetro global.
    """

    value = serializers.CharField(
        required=False,
        allow_null=True,
    )
    data_type = serializers.ChoiceField(
        choices=GlobalParameter.DataType.choices,
        required=False,
        allow_null=True,
    )
    description = serializers.CharField(
        max_length=1000,
        required=False,
        allow_null=True,
        allow_blank=True,
    )

    def validate(self, attrs: dict) -> dict:
        val = attrs.get("value")
        dt = attrs.get("data_type")
        instance = getattr(self, "instance", None)

        target_dt = (
            dt if dt is not None else (instance.data_type if instance else None)
        )
        target_val = (
            val if val is not None else (instance.value if instance else None)
        )

        if target_dt is not None and target_val is not None:
            from apps.configuration.services.global_parameter_service import (
                GlobalParameterService,
            )

            try:
                GlobalParameterService.validate_value_by_data_type(
                    target_val, target_dt
                )
            except DjangoValidationError as exc:
                msg = exc.messages[0] if hasattr(exc, "messages") else str(exc)
                raise serializers.ValidationError({"value": msg})

        return attrs

    def to_dto(self) -> GlobalParameterUpdateDto:
        """Convierte los datos validados en un DTO."""
        v = self.validated_data
        return GlobalParameterUpdateDto(
            value=v.get("value"),
            data_type=v.get("data_type"),
            description=v.get("description"),
        )

