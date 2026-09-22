from dataclasses import dataclass
from decimal import Decimal



@dataclass(frozen=True)
class SaleDetailDto:
    """
    DTO que representa un detalle de venta.

    contiene la informacion necesaria para procesar un producto
    dentro de una operacion de ventas.
    """

    product_id: int
    quantity: Decimal
    unit_price: Decimal | None = None
    discount: Decimal = Decimal("0.00")
