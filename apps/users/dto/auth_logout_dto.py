from dataclasses import dataclass


@dataclass(frozen=True)
class AuthLogoutDTO:
    """
    DTO para la solicitud de cierre de sesión e invalidación de token.
    """

    refresh_token: str
