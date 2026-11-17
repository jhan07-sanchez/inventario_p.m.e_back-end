from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class ImpersonationRequestDTO:
    """
    DTO que representa los parámetros requeridos para iniciar una sesión de soporte (impersonación).
    """

    company_id: int
    reason: str
    target_user_id: Optional[int] = None


@dataclass(frozen=True)
class ImpersonationResultDTO:
    """
    DTO que representa el resultado seguro de una impersonación autorizada.
    No incluye refresh tokens para prevenir extensiones silenciosas no auditadas.
    """

    access_token: str
    token_type: str
    expires_in: int
    target_user: dict[str, Any]
    target_company: dict[str, Any]
    impersonated_by: dict[str, Any]
