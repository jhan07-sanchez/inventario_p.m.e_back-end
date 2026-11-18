from dataclasses import dataclass


@dataclass(frozen=True)
class AuthRefreshDTO:
    """
    DTO para la solicitud de refresco de tokens JWT.
    """

    refresh_token: str
