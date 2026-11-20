from typing import Any, Optional
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from apps.users.models import Role, UserRole

User = get_user_model()


class SaaSRoleSummarySerializer(serializers.ModelSerializer):
    """Representación de un rol del sistema para miembros del SaaS."""

    class Meta:
        model = Role
        fields = (
            "id_role",
            "role_name",
            "role_description",
            "permissions",
            "is_active",
        )


class SaaSTeamListSerializer(serializers.ModelSerializer):
    """Serializador para listado de miembros del equipo interno SaaS."""

    full_name = serializers.SerializerMethodField()
    role_display = serializers.SerializerMethodField()
    saas_profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id_user",
            "username",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "phone_number",
            "document_number",
            "is_superuser",
            "is_staff",
            "is_active",
            "role_display",
            "saas_profile",
            "date_joined",
            "last_login",
        )

    def get_full_name(self, obj: User) -> str:
        return obj.get_full_name() or obj.username

    def get_role_display(self, obj: User) -> str:
        if obj.is_superuser:
            return "Propietario / Superadministrador"
        user_role = obj.user_roles.filter(role__is_active=True).first()
        if user_role and user_role.role:
            return user_role.role.role_name
        return "Personal Interno"

    def get_saas_profile(self, obj: User) -> str:
        if obj.is_superuser:
            return "SUPERADMIN"
        user_role = obj.user_roles.filter(role__is_active=True).first()
        if user_role and user_role.role:
            name = user_role.role.role_name.upper()
            if "SOPORTE" in name:
                return "SUPPORT"
            if "VENTAS" in name or "COMERCIAL" in name:
                return "SALES"
            if "FINANZAS" in name:
                return "FINANCE"
        return "STAFF"


class SaaSTeamDetailSerializer(serializers.ModelSerializer):
    """Serializador con detalle completo, roles y actividad reciente de un miembro."""

    full_name = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    recent_activity = serializers.SerializerMethodField()
    saas_profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id_user",
            "username",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "phone_number",
            "document_number",
            "is_superuser",
            "is_staff",
            "is_active",
            "saas_profile",
            "roles",
            "recent_activity",
            "date_joined",
            "last_login",
            "created_at",
            "updated_at",
        )

    def get_full_name(self, obj: User) -> str:
        return obj.get_full_name() or obj.username

    def get_saas_profile(self, obj: User) -> str:
        if obj.is_superuser:
            return "SUPERADMIN"
        user_role = obj.user_roles.filter(role__is_active=True).first()
        if user_role and user_role.role:
            name = user_role.role.role_name.upper()
            if "SOPORTE" in name:
                return "SUPPORT"
            if "VENTAS" in name or "COMERCIAL" in name:
                return "SALES"
            if "FINANZAS" in name:
                return "FINANCE"
        return "STAFF"

    def get_roles(self, obj: User) -> list[dict]:
        user_roles = obj.user_roles.filter(role__is_active=True).select_related("role")
        return [SaaSRoleSummarySerializer(ur.role).data for ur in user_roles if ur.role]

    def get_recent_activity(self, obj: User) -> list[dict]:
        from apps.core.models.audit_log import AuditLog
        logs = AuditLog.objects.filter(user=obj).order_by("-created_at")[:10]
        return [
            {
                "id_audit": log.pk,
                "method": log.method,
                "path": log.path,
                "status_code": log.status_code,
                "created_at": log.created_at.isoformat() if log.created_at else None,
                "payload": log.payload,
            }
            for log in logs
        ]


class SaaSTeamCreateSerializer(serializers.Serializer):
    """Validador para registro de nuevo miembro del equipo SaaS."""

    username = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=True)
    document_number = serializers.CharField(max_length=50, required=True)
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    saas_profile = serializers.ChoiceField(
        choices=["SUPERADMIN", "SUPPORT", "SALES", "FINANCE"],
        required=True,
        help_text="Perfil funcional: SUPERADMIN, SUPPORT, SALES, FINANCE",
    )

    def validate_username(self, value):
        val = value.strip()
        if User.objects.filter(username__iexact=val).exists():
            raise serializers.ValidationError("El nombre de usuario ya se encuentra registrado.")
        return val

    def validate_email(self, value):
        val = value.strip().lower()
        if User.objects.filter(email__iexact=val).exists():
            raise serializers.ValidationError("El correo electrónico ya se encuentra registrado.")
        return val

    def validate_document_number(self, value):
        val = value.strip()
        if User.objects.filter(document_number=val).exists():
            raise serializers.ValidationError("El número de documento ya se encuentra registrado.")
        return val


class SaaSTeamUpdateSerializer(serializers.Serializer):
    """Validador para actualización de información y perfil de un miembro."""

    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    saas_profile = serializers.ChoiceField(
        choices=["SUPERADMIN", "SUPPORT", "SALES", "FINANCE"],
        required=False,
    )
    is_active = serializers.BooleanField(required=False)
    password = serializers.CharField(
        write_only=True,
        required=False,
        validators=[validate_password],
        style={"input_type": "password"},
    )
