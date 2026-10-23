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
    Serializer utilizado para crear un parámetro global.
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
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
    )

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
        max_length=255,
        required=False,
        allow_null=True,
        allow_blank=True,
    )

    def to_dto(self) -> GlobalParameterUpdateDto:
        """Convierte los datos validados en un DTO."""
        v = self.validated_data
        return GlobalParameterUpdateDto(
            value=v.get("value"),
            data_type=v.get("data_type"),
            description=v.get("description"),
        )
