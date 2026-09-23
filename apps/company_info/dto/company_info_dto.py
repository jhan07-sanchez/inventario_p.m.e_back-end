from dataclasses import dataclass


@dataclass(frozen=True)
class CompanyInfoCreateDto:
    """
    DTO utilizado para crear la información de empresa.
    """

    business_name: str
    tax_id: str
    trade_name: str = ""
    phone: str = ""
    mobile: str = ""
    email: str = ""
    website: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    country: str = "Colombia"
    description: str = ""
    receipt_footer: str = "Gracias por su compra"


@dataclass(frozen=True)
class CompanyInfoUpdateDto:
    """
    DTO utilizado para actualizar la información de empresa.
    """

    business_name: str | None = None
    trade_name: str | None = None
    tax_id: str | None = None
    phone: str | None = None
    mobile: str | None = None
    email: str | None = None
    website: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    description: str | None = None
    receipt_footer: str | None = None
