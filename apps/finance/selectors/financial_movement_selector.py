from datetime import date
from decimal import Decimal
from typing import Optional

from django.db.models import Q, QuerySet, Sum

from apps.core.selectors.base_selector import BaseSelector
from apps.finance.models.financial_movement import FinancialMovement


class FinancialMovementSelector(BaseSelector[FinancialMovement]):
    """
    Selector para consultas de lectura sobre Movimientos Financieros.
    """

    def __init__(self):
        super().__init__(FinancialMovement)

    @classmethod
    def get_movements(
        cls,
        account_id: Optional[int] = None,
        movement_type: Optional[str] = None,
        category_id: Optional[int] = None,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        include_deleted: bool = False,
    ) -> QuerySet[FinancialMovement]:
        qs = (
            cls()
            .get_all(include_deleted=include_deleted)
            .select_related("account", "category", "user", "transfer")
        )
        if not include_deleted:
            qs = qs.filter(is_active=True)
        if account_id:
            qs = qs.filter(account_id=account_id)
        if movement_type:
            qs = qs.filter(movement_type=movement_type)
        if category_id:
            qs = qs.filter(category_id=category_id)
        if status:
            qs = qs.filter(status=status)
        if start_date:
            qs = qs.filter(movement_date__gte=start_date)
        if end_date:
            qs = qs.filter(movement_date__lte=end_date)
        return qs

    @classmethod
    def get_movement_by_id(
        cls,
        movement_id: int,
        include_deleted: bool = False,
    ) -> Optional[FinancialMovement]:
        return (
            cls()
            .get_all(include_deleted=include_deleted)
            .select_related("account", "category", "user", "transfer", "reversal_of")
            .filter(pk=movement_id)
            .first()
        )

    @classmethod
    def get_period_totals(
        cls,
        account_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        exclude_transfers: bool = True,
    ) -> dict[str, Decimal]:
        """
        Calcula ingresos y egresos completados en un período.
        Por defecto excluye transferencias internas entre cuentas propias para no inflar ingresos o gastos.
        """
        qs = cls.get_movements(
            account_id=account_id,
            status=FinancialMovement.MovementStatus.COMPLETED,
            start_date=start_date,
            end_date=end_date,
        )
        if exclude_transfers:
            qs = qs.filter(~Q(origin_type=FinancialMovement.OriginType.TRANSFER))

        income = (
            qs.filter(movement_type=FinancialMovement.MovementType.INFLOW).aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )

        expense = (
            qs.filter(movement_type=FinancialMovement.MovementType.OUTFLOW).aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )

        return {
            "income": income,
            "expense": expense,
            "net": income - expense,
        }

