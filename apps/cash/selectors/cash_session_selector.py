from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from apps.cash.models.cash_session import CashSession
from apps.cash.models.cash_movement import CashMovement


class CashSessionSelector:
    """
    Selector de sesiones de caja.
    """

    @staticmethod
    def get_all() -> QuerySet[CashSession]:
        return CashSession.objects.filter(is_active=True).select_related("cash_register", "user").order_by("-start_time")

    @staticmethod
    def get_by_id(session_id: int) -> CashSession:
        return get_object_or_404(
            CashSession.objects.filter(is_active=True).select_related("cash_register", "user"),
            pk=session_id
        )

    @staticmethod
    def get_current_session(user) -> CashSession | None:
        return CashSession.objects.filter(
            user=user,
            status=CashSession.SessionStatus.OPEN,
            is_active=True
        ).select_related("cash_register").first()

    @staticmethod
    def get_movements(session_id: int) -> QuerySet[CashMovement]:
        return CashMovement.objects.filter(
            cash_session_id=session_id,
            is_active=True
        ).select_related("payment").order_by("-created_at")
