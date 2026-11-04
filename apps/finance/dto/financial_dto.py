from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class FinancialAccountCreateDTO:
    name: str
    account_type: str
    account_number: str = ""
    bank_name: str = ""
    currency: str = "COP"
    initial_balance: Decimal = Decimal("0.00")
    description: str = ""
    company_id: Optional[int] = None


@dataclass(frozen=True)
class FinancialAccountUpdateDTO:
    name: Optional[str] = None
    account_type: Optional[str] = None
    account_number: Optional[str] = None
    bank_name: Optional[str] = None
    description: Optional[str] = None


@dataclass(frozen=True)
class FinancialMovementCreateDTO:
    account_id: int
    movement_type: str
    amount: Decimal
    movement_date: date
    description: str
    category_id: Optional[int] = None
    payment_method: str = "TRANSFER"
    reference: str = ""
    origin_type: str = "MANUAL"
    origin_id: Optional[int] = None
    notes: str = ""


@dataclass(frozen=True)
class FinancialTransferCreateDTO:
    source_account_id: int
    destination_account_id: int
    amount: Decimal
    transfer_date: date
    reference: str = ""
    notes: str = ""


@dataclass(frozen=True)
class FinancialReconciliationCreateDTO:
    account_id: int
    start_date: date
    end_date: date
    statement_balance: Decimal
    notes: str = ""

