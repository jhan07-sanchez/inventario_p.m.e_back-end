from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CashSessionOpenDto:
    """
    DTO para la apertura de una sesión de caja.
    """

    cash_register_id: int
    opening_balance: Decimal
    notes: str = ""


@dataclass(frozen=True)
class CashSessionCloseDto:
    """
    DTO para el cierre de una sesión de caja.
    """

    counted_balance: Decimal
    notes: str = ""
