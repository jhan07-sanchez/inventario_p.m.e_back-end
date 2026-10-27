from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.configuration.models import ConfigurationAudit


class ConfigurationAuditSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = ConfigurationAudit
        fields = (
            "id",
            "parameter_key",
            "action",
            "user_name",
            "old_value",
            "new_value",
            "reason",
            "created_at",
        )

    @extend_schema_field(serializers.CharField)
    def get_user_name(self, obj) -> str:
        if obj.user:
            return (
                f"{obj.user.first_name} {obj.user.last_name}".strip()
                or obj.user.username
            )
        return "Sistema / Anónimo"
