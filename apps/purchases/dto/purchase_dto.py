from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True, slots=True)
class PurchaseDetailCreateDTO:
    """DTO para la creación de un detalle de compra."""

    product_id: int
    quantity: Decimal
    unit_price: Decimal


@dataclass(frozen=True, slots=True)
class PurchaseCreateDTO:
    """DTO para la creación de una compra con sus respectivos detalles."""

    supplier_id: int
    issue_date: Optional[date]
    notes: Optional[str]
    details: list[PurchaseDetailCreateDTO]


@dataclass(frozen=True, slots=True)
class PurchaseUpdateDTO:
    """DTO para la actualización de la cabecera de una compra."""

    issue_date: Optional[date]
    notes: Optional[str]


@dataclass(frozen=True, slots=True)
class PurchasePayDTO:
    """DTO para registrar el pago de una compra a proveedor."""

    amount: Decimal
    payment_method: str
    cash_session_id: Optional[int] = None
    reference: str = ""
    notes: str = ""
