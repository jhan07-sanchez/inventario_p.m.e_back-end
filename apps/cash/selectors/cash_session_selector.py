from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from apps.cash.models.cash_movement import CashMovement
from apps.cash.models.cash_session import CashSession
from apps.core.selectors.base_selector import BaseSelector


class CashSessionSelector(BaseSelector[CashSession]):
    """
    Selector de sesiones de caja.
    """

    def __init__(self):
        super().__init__(CashSession)

    def get_queryset(self, include_deleted: bool = False) -> QuerySet[CashSession]:
        """
        Retorna el queryset base de sesiones optimizando las relaciones
        con caja y usuario.
        """
        return (
            super()
            .get_queryset(include_deleted=include_deleted)
            .select_related("cash_register", "user")
            .order_by("-start_time")
        )

    @staticmethod
    def get_all(qs=None, include_deleted: bool = False) -> QuerySet[CashSession]:
        """
        Retorna todas las sesiones de caja activas.
        """
        if qs is not None:
            return qs.filter(is_active=True) if not include_deleted else qs
        return (
            CashSessionSelector().get_queryset(include_deleted=include_deleted)
            if include_deleted
            else CashSessionSelector().get_queryset().filter(is_active=True)
        )

    @staticmethod
    def get_by_id(session_id: int) -> CashSession:
        return get_object_or_404(
            CashSessionSelector().get_queryset().filter(is_active=True),
            pk=session_id,
        )

    @staticmethod
    def get_current_session(user) -> CashSession | None:
        return (
            CashSession.objects.filter(
                user=user, status=CashSession.SessionStatus.OPEN, is_active=True
            )
            .select_related("cash_register")
            .first()
        )

    @staticmethod
    def get_movements(session_id: int) -> QuerySet[CashMovement]:
        return (
            CashMovement.objects.filter(cash_session_id=session_id, is_active=True)
            .select_related("payment")
            .order_by("-created_at")
        )
