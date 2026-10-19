from django.db.models import QuerySet

from apps.cash.models.cash_register import CashRegister


class CashRegisterSelector:
    """
    Selector de cajas registradoras.
    """

    @staticmethod
    def get_all() -> QuerySet[CashRegister]:
        return CashRegister.objects.filter(is_active=True).order_by("name")
