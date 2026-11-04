from decimal import Decimal
from typing import Optional

from django.db.models import QuerySet, Sum

from apps.core.selectors.base_selector import BaseSelector
from apps.finance.models.financial_account import FinancialAccount


class FinancialAccountSelector(BaseSelector[FinancialAccount]):
    """
    Selector para consultas de lectura sobre Cuentas Financieras.
    """

    def __init__(self):
        super().__init__(FinancialAccount)

    @classmethod
    def get_accounts(
        cls,
        company_id: Optional[int] = None,
        account_type: Optional[str] = None,
        include_deleted: bool = False,
        is_active: Optional[bool] = None,
    ) -> QuerySet[FinancialAccount]:
        if is_active is False:
            include_deleted = True
        qs = cls().get_all(include_deleted=include_deleted).select_related("company")
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        elif not include_deleted:
            qs = qs.filter(is_active=True)

        if company_id:
            qs = qs.filter(company_id=company_id)
        if account_type:
            qs = qs.filter(account_type=account_type)
        return qs

    @classmethod
    def get_account_by_id(
        cls,
        account_id: int,
        include_deleted: bool = False,
    ) -> Optional[FinancialAccount]:
        return (
            cls()
            .get_all(include_deleted=include_deleted)
            .select_related("company")
            .filter(pk=account_id)
            .first()
        )

    @classmethod
    def get_total_balance(
        cls,
        company_id: Optional[int] = None,
        account_type: Optional[str] = None,
    ) -> Decimal:
        qs = cls.get_accounts(company_id=company_id, account_type=account_type)
        total = qs.aggregate(total=Sum("current_balance"))["total"]
        return total or Decimal("0.00")

