from dataclasses import dataclass


@dataclass(frozen=True)
class AuthMeDTO:
    """
    DTO para la consulta del perfil del usuario autenticado.
    """

    user_id: int
