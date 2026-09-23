from dataclasses import dataclass
from decimal import Decimal

from apps.sales.dto.sale_detail_dto import SaleDetailDto


@dataclass(frozen=True)
class SaleCreateDto:
    """
    DTO utilizado para crear una venta.

    Los valores calculados como subtotal y total no forman parte
    del DTO porque deben ser determinados por el backend.
    """

    details: tuple[SaleDetailDto, ...]
    customer_id: int | None = None
    discount: Decimal = Decimal("0.00")
    tax: Decimal = Decimal("0.00")
    payment_method: str = "CASH"
    notes: str = ""
    sale_type: str = "ADMIN"
    amount_received: Decimal | None = None
    change_amount: Decimal | None = None
    generate_invoice: bool = True


@dataclass(frozen=True)
class SaleUpdateDto:
    """
    DTO utilizado para actualizar los campos permitidos
    de una venta.
    """

    customer_id: int | None = None
    payment_method: str | None = None
    notes: str | None = None
