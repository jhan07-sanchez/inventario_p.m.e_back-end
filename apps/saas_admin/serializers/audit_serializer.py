from rest_framework import serializers

from apps.core.models.audit_log import AuditLog


class SaaSAuditLogSerializer(serializers.ModelSerializer):
    """Serializador para el registro de auditoría global del SaaS."""

    user_email = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "user",
            "user_email",
            "company",
            "company_name",
            "method",
            "path",
            "ip_address",
            "user_agent",
            "status_code",
            "payload",
            "created_at",
        )

    def get_user_email(self, obj: AuditLog) -> str:
        if obj.user:
            return obj.user.email or obj.user.username
        return "Sistema / Anónimo"

    def get_company_name(self, obj: AuditLog) -> str:
        if obj.company:
            return obj.company.business_name or obj.company.trade_name
        return "Plataforma Global (SaaS)"
