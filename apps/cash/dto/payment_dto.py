from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PaymentCreateDto:
    """
    DTO para la creación de un pago asociado a una venta.
    """
    amount: Decimal
    payment_method: str
    sale_id: int | None = None
    reference: str = ""
    notes: str = ""
