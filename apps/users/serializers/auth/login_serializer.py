from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.users.dto import LoginResult
from apps.users.serializers.user_serializer import UserDetailSerializer

User = get_user_model()


class AuthLoginSerializer(serializers.Serializer):
    """Serializer para validar las credenciales de inicio de sesión."""

    email = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Correo electrónico o nombre de usuario.",
    )

    username = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Nombre de usuario alternativo.",
    )

    password = serializers.CharField(
        required=True,
        write_only=True,
        trim_whitespace=False,
        style={"input_type": "password"},
        help_text="Contraseña del usuario.",
    )

    def validate(self, attrs: dict) -> dict:
        """Valida que las credenciales hayan sido enviadas y resuelve el identificador."""
        email = attrs.get("email")
        username = attrs.get("username")
        password = attrs.get("password")

        identifier = (email or username or "").strip()

        if not identifier:
            raise serializers.ValidationError(
                {"email": "El correo electrónico o nombre de usuario es obligatorio."},
            )

        if not password:
            raise serializers.ValidationError(
                {"password": "La contraseña es obligatoria."},
            )

        # Si el identificador no tiene formato email o es un username, resolver al email del usuario
        if "@" not in identifier:
            matched_user = User.objects.filter(username__iexact=identifier).first()
            if matched_user:
                identifier = matched_user.email

        attrs["email"] = identifier.lower()
        return attrs


class LoginResponseSerializer(serializers.Serializer):
    """
    Serializer de respuesta del login.

    Serializa únicamente usuario y tokens JWT.
    """

    user = UserDetailSerializer(read_only=True)
    access_token = serializers.CharField(read_only=True)
    refresh_token = serializers.CharField(read_only=True)

    def to_representation(self, instance: LoginResult) -> dict:
        """Convierte un ``LoginResult`` en la respuesta JSON del API."""

        return {
            "user": UserDetailSerializer(instance.user).data,
            "access_token": instance.access_token,
            "refresh_token": instance.refresh_token,
        }
