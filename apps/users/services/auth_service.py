from datetime import timedelta

from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.configuration.services.global_parameter_service import GlobalParameterService
from apps.core.exceptions.custom_exceptions import (
    AccountLockedException,
    InvalidCredentialsException,
    InvalidTokenException,
    NoActiveRoleException,
    NoPermissionsException,
    UserInactiveException,
)
from apps.core.security.services import PermissionService
from apps.users.dto import LoginResult, MeResult
from apps.users.models import User


class AuthService:
    """
    Servicio encargado exclusivamente de la autenticación de usuarios.

    Responsabilidades:
        - Autenticar credenciales.
        - Validar estado del usuario, roles y permisos efectivos.
        - Generar y gestionar tokens JWT.
        - Gestionar bloqueo por intentos fallidos y expiración dinámica.
    """

    @staticmethod
    def login(email: str, password: str) -> LoginResult:
        """
        Autentica un usuario y genera los tokens JWT.
        """
        # 1. Buscamos al usuario primero para verificar si está bloqueado
        user = User.objects.filter(email=email).first()

        if user and user.is_locked_out:
            #Calculamos el tiempo exacto
            remaining_time = user.lockout_until - timezone.now()
            remaining_minutes = max(1, int(remaining_time.total_seconds() / 60))
            raise AccountLockedException(remaining_minutes=remaining_minutes)

        # 2. Autenticamos las credenciales
        authenticated_user = authenticate(email=email, password=password)

        if authenticated_user is None:
            # 3. Manejo de intentos fallidos (solo si el usuario existe en la BD)
            if user:
                user.failed_login_attempts += 1
                max_attempts = GlobalParameterService.get_typed_value(
                    "SECURITY_MAX_LOGIN_ATTEMPTS", default=5
                )

                if user.failed_login_attempts >= max_attempts:
                    # Bloqueo por 15 minutos
                    user.lockout_until = timezone.now() + timedelta(minutes=15)
                    user.failed_login_attempts = (
                        0  # Reiniciamos el contador tras bloquear
                    )

                user.save(update_fields=["failed_login_attempts", "lockout_until"])

            raise InvalidCredentialsException()

        # 4. Login Exitoso: Si tenía intentos fallidos previos, los reiniciamos
        if user and (user.failed_login_attempts > 0 or user.lockout_until):
            user.failed_login_attempts = 0
            user.lockout_until = None
            user.save(update_fields=["failed_login_attempts", "lockout_until"])

        # 5. Validaciones de negocio estandar
        if not authenticated_user.is_active:
            raise UserInactiveException()

        if not PermissionService.has_any_active_role(authenticated_user):
            raise NoActiveRoleException()

        effective_permissions = PermissionService.get_effective_permissions(
            authenticated_user
        )

        if not PermissionService.has_any_permission(effective_permissions):
            raise NoPermissionsException()

        # 6. Generación del Token Dinámico
        refresh = RefreshToken.for_user(authenticated_user)

        # Leemos el parámetro del tiempo desde la base de datos
        timeout_minutes = GlobalParameterService.get_typed_value(
            "SECURITY_SESSION_TIMEOUT_MINUTES", default=30
        )

        # Sobreescribimos la expiración del Access Token
        refresh.access_token.set_exp(lifetime=timedelta(minutes=timeout_minutes))

        return LoginResult(
            user=authenticated_user,
            access_token=str(refresh.access_token),
            refresh_token=str(refresh),
        )

    @staticmethod
    def me(user: User) -> MeResult:
        """
        Retorna la información del usuario autenticado.
        """
        return MeResult(user=user)

    @staticmethod
    def refresh_token(validated_data: dict) -> dict:
        """Genera un nuevo Access Token a partir de un Refresh Token válido."""

        refresh_token = validated_data.get("refresh")
        from rest_framework.exceptions import ValidationError
        from rest_framework_simplejwt.serializers import TokenRefreshSerializer

        try:
            serializer = TokenRefreshSerializer(data={"refresh": refresh_token})
            serializer.is_valid(raise_exception=True)
            return serializer.validated_data
        except (TokenError, ValidationError):
            raise InvalidTokenException()

    @staticmethod
    def logout(refresh_token: str, user: User) -> None:
        """Invalida un Refresh Token incluyéndolo en la Blacklist."""

        try:
            token = RefreshToken(refresh_token)

            from rest_framework_simplejwt.settings import api_settings

            user_id_claim = api_settings.USER_ID_CLAIM

            if str(token.payload.get(user_id_claim)) != str(user.id_user):
                raise InvalidTokenException()

            token.blacklist()
        except TokenError:
            # Según RFC 7009, revocar un token ya revocado o inválido debe retornar 200 OK.
            pass
