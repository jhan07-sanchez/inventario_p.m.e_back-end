from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, slots=True)
class InvoiceTemplateCreateDTO:
    """DTO para la creación de plantillas de factura."""
    name: str
    document_type: str
    header_content: Optional[str] = None
    body_content: Optional[str] = None
    footer_content: Optional[str] = None
    is_default: bool = False


@dataclass(frozen=True, slots=True)
class InvoiceTemplateUpdateDTO:
    """DTO para la actualización de plantillas de factura."""
    name: Optional[str] = None
    header_content: Optional[str] = None
    body_content: Optional[str] = None
    footer_content: Optional[str] = None
    is_default: Optional[bool] = None
