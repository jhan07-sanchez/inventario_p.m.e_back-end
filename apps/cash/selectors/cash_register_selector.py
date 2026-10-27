from django.db.models import QuerySet

from apps.cash.models.cash_register import CashRegister
from apps.core.selectors.base_selector import BaseSelector


class CashRegisterSelector(BaseSelector[CashRegister]):
    """
    Selector de cajas registradoras.
    """

    def __init__(self):
        super().__init__(CashRegister)

    def get_queryset(self, include_deleted: bool = False) -> QuerySet[CashRegister]:
        """
        Retorna el queryset base de cajas registradoras ordenadas por nombre.
        """
        return (
            super()
            .get_queryset(include_deleted=include_deleted)
            .order_by("name")
        )

    @staticmethod
    def get_all(qs=None, include_deleted: bool = False) -> QuerySet[CashRegister]:
        """
        Retorna todas las cajas registradoras activas.
        """
        if qs is not None:
            return qs.filter(is_active=True) if not include_deleted else qs
        return (
            CashRegisterSelector().get_queryset(include_deleted=include_deleted)
            if include_deleted
            else CashRegisterSelector().get_queryset().filter(is_active=True)
        )
