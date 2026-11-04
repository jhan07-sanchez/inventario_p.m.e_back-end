from typing import Optional

from django.db.models import QuerySet

from apps.core.selectors.base_selector import BaseSelector
from apps.finance.models.financial_reconciliation import FinancialReconciliation


class FinancialReconciliationSelector(BaseSelector[FinancialReconciliation]):
    """
    Selector para consultas de lectura sobre Conciliaciones Financieras.
    """

    def __init__(self):
        super().__init__(FinancialReconciliation)

    @classmethod
    def get_reconciliations(
        cls,
        account_id: Optional[int] = None,
        status: Optional[str] = None,
        include_deleted: bool = False,
    ) -> QuerySet[FinancialReconciliation]:
        qs = (
            cls()
            .get_all(include_deleted=include_deleted)
            .select_related("account", "user")
        )
        if not include_deleted:
            qs = qs.filter(is_active=True)
        if account_id:
            qs = qs.filter(account_id=account_id)
        if status:
            qs = qs.filter(status=status)
        return qs

    @classmethod
    def get_reconciliation_by_id(
        cls,
        reconciliation_id: int,
        include_deleted: bool = False,
    ) -> Optional[FinancialReconciliation]:
        return (
            cls()
            .get_all(include_deleted=include_deleted)
            .select_related("account", "user")
            .filter(pk=reconciliation_id)
            .first()
        )

