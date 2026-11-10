from datetime import date
from typing import Optional

from django.db.models import Q, QuerySet

from apps.core.selectors.base_selector import BaseSelector
from apps.finance.models.financial_transfer import FinancialTransfer


class FinancialTransferSelector(BaseSelector[FinancialTransfer]):
    """
    Selector para consultas de lectura sobre Transferencias Financieras.
    """

    def __init__(self):
        super().__init__(FinancialTransfer)

    @classmethod
    def get_transfers(
        cls,
        company_id: Optional[int] = None,
        source_account_id: Optional[int] = None,
        destination_account_id: Optional[int] = None,
        account_id: Optional[int] = None,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        include_deleted: bool = False,
    ) -> QuerySet[FinancialTransfer]:
        qs = (
            cls()
            .get_all(include_deleted=include_deleted)
            .select_related("source_account", "destination_account", "user")
        )
        if not include_deleted:
            qs = qs.filter(is_active=True)
        if company_id:
            qs = qs.filter(source_account__company_id=company_id)
        if source_account_id:
            qs = qs.filter(source_account_id=source_account_id)
        if destination_account_id:
            qs = qs.filter(destination_account_id=destination_account_id)
        if account_id:
            qs = qs.filter(
                Q(source_account_id=account_id)
                | Q(destination_account_id=account_id)
            )
        if status:
            qs = qs.filter(status=status)
        if start_date:
            qs = qs.filter(transfer_date__gte=start_date)
        if end_date:
            qs = qs.filter(transfer_date__lte=end_date)
        return qs

    @classmethod
    def get_transfer_by_id(
        cls,
        transfer_id: int,
        company_id: Optional[int] = None,
        include_deleted: bool = False,
    ) -> Optional[FinancialTransfer]:
        qs = (
            cls()
            .get_all(include_deleted=include_deleted)
            .select_related("source_account", "destination_account", "user")
            .filter(pk=transfer_id)
        )
        if company_id:
            qs = qs.filter(source_account__company_id=company_id)
        return qs.first()
