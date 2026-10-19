from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CashMovementCreateDto:
    """
    DTO para registrar un movimiento de caja (ingreso o egreso).
    """

    cash_session_id: int
    amount: Decimal
    movement_type: str
    is_cash: bool = True
    payment_id: int | None = None
    reference: str = ""
    description: str = ""
