from dataclasses import dataclass


@dataclass(frozen=True)
class TenantActionDto:
    """
    DTO inmutable que representa una acción administrativa sobre una empresa (Tenant).
    """

    action: str
    reason: str = ""
    extra_days: int = 0
