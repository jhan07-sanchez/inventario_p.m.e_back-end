from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True, slots=True)
class InvoiceItemCreateDTO:
    """DTO para la creación de un detalle de factura."""
    product_id: int
    quantity: Decimal
    unit_price: Decimal
    discount: Decimal = Decimal("0.00")
    tax: Decimal = Decimal("0.00")


@dataclass(frozen=True, slots=True)
class InvoiceCreateDTO:
    """DTO para la creación de una factura con sus ítems."""
    document_type: str
    template_id: int
    invoice_number: str
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    purchase_id: Optional[int] = None
    notes: Optional[str] = None
    items: list[InvoiceItemCreateDTO] = None


@dataclass(frozen=True, slots=True)
class InvoiceUpdateDTO:
    """DTO para la actualización de la cabecera de una factura."""
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None
