from django.contrib.auth.password_validation import validate_password
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.users.models import User
from apps.core.security.services.permission_service import PermissionService

from .role_serializer import RoleListSerializer


# serializer para listar usuarios
class UserListSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User

        fields = (
            "id_user",
            "username",
            "first_name",
            "last_name",
            "email",
            "document_number",
            "roles",
            "is_active",
        )

    @extend_schema_field(RoleListSerializer(many=True))
    def get_roles(self, obj):
        """
        Retorna todos los roles asignados al usuario de forma optimizada.
        """

        roles = PermissionService._get_active_roles(obj)

        return RoleListSerializer(
            roles,
            many=True,
        ).data


class UserDetailSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User

        fields = (
            "id_user",
            "username",
            "first_name",
            "last_name",
            "email",
            "document_number",
            "phone_number",
            "roles",
            "is_active",
            "created_at",
            "updated_at",
        )

    @extend_schema_field(RoleListSerializer(many=True))
    def get_roles(self, obj):
        roles = PermissionService._get_active_roles(obj)

        return RoleListSerializer(
            roles,
            many=True,
        ).data


# Serializer para crear usuarios
class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
    )

    class Meta:
        model = User

        fields = (
            "username",
            "password",
            "first_name",
            "last_name",
            "email",
            "document_number",
            "phone_number",
        )

        extra_kwargs = {
            "username": {"validators": []},
            "email": {"validators": []},
            "document_number": {"validators": []},
        }

    def validate_phone_number(self, value):
        # Convierte "" o cadenas de puros espacios a None (NULL en BD)
        if value is not None and value.strip() == "":
            return None
        return value


# Serializer para actualizar usuarios
class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User

        fields = (
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "is_active",
        )

        extra_kwargs = {
            "username": {"validators": []},
            "email": {"validators": []},
            "document_number": {"validators": []},
        }


    def validate_phone_number(self, value):
        if value is not None and value.strip() == "":
            return None
        return value
