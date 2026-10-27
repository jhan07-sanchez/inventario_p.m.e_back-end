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

    @staticmethod
    def get_last_closed_session(cash_register_id: int) -> CashSession | None:
        """
        Retorna la última sesión cerrada para una caja registradora específica,
        permitiendo el arrastre de saldo (carry-over).
        """
        return (
            CashSession.objects.filter(
                cash_register_id=cash_register_id,
                status=CashSession.SessionStatus.CLOSED,
                is_active=True,
            )
            .order_by("-end_time")
            .first()
        )

    @staticmethod
    def get_session_audit_summary(session_id: int) -> dict:
        """
        Retorna un resumen financiero y de auditoría detallado para una sesión.
        """
        import json
        from decimal import Decimal
        from django.db.models import Q, Sum

        session = CashSessionSelector.get_by_id(session_id)
        movements = session.movements.filter(is_active=True).select_related("payment")

        # Sumatorias generales
        cash_in = (
            movements.filter(is_cash=True, movement_type="IN").aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )
        cash_out = (
            movements.filter(is_cash=True, movement_type="OUT").aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )
        elec_in = (
            movements.filter(is_cash=False, movement_type="IN").aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )
        elec_out = (
            movements.filter(is_cash=False, movement_type="OUT").aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )

        # Ventas (con payment asociado)
        sales_cash = (
            movements.filter(
                is_cash=True,
                movement_type="IN",
                payment__isnull=False,
                payment__sale__isnull=False,
            ).aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        sales_electronic = (
            movements.filter(
                is_cash=False,
                movement_type="IN",
                payment__isnull=False,
                payment__sale__isnull=False,
            ).aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        # Pagos de compras a proveedores
        purchases_cash = (
            movements.filter(
                is_cash=True,
                movement_type="OUT",
            )
            .filter(
                Q(reference__icontains="COMPRA")
                | Q(description__icontains="COMPRA")
                | Q(payment__reference__icontains="COMPRA")
            )
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        purchases_electronic = (
            movements.filter(
                is_cash=False,
                movement_type="OUT",
            )
            .filter(
                Q(reference__icontains="COMPRA")
                | Q(description__icontains="COMPRA")
                | Q(payment__reference__icontains="COMPRA")
            )
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        # Movimientos manuales
        manual_income = cash_in - sales_cash
        manual_expenses = cash_out - purchases_cash

        # Denominaciones guardadas
        denominations = None
        if session.notes and "DENOMINATIONS:" in session.notes:
            try:
                denominations = json.loads(
                    session.notes.split("DENOMINATIONS:", 1)[1].strip()
                )
            except Exception:
                pass

        recalculated_expected = session.opening_balance + cash_in - cash_out

        return {
            "session_id": session.id_cash_session,
            "cash_register_id": session.cash_register_id,
            "cash_register_name": session.cash_register.name,
            "user_id": session.user_id,
            "user_name": session.user.get_full_name() or session.user.username,
            "status": session.status,
            "start_time": session.start_time,
            "end_time": session.end_time,
            "opening_balance": str(session.opening_balance),
            "expected_balance": str(session.expected_balance),
            "recalculated_expected_balance": str(recalculated_expected),
            "counted_balance": (
                str(session.counted_balance)
                if session.counted_balance is not None
                else None
            ),
            "difference": (
                str(session.difference) if session.difference is not None else None
            ),
            "cash_in_total": str(cash_in),
            "cash_out_total": str(cash_out),
            "net_cash_movement": str(cash_in - cash_out),
            "sales_cash": str(sales_cash),
            "sales_electronic": str(sales_electronic),
            "total_sales": str(sales_cash + sales_electronic),
            "purchases_cash": str(purchases_cash),
            "purchases_electronic": str(purchases_electronic),
            "total_purchases_paid": str(purchases_cash + purchases_electronic),
            "manual_income": str(
                manual_income if manual_income > 0 else Decimal("0.00")
            ),
            "manual_expenses": str(
                manual_expenses if manual_expenses > 0 else Decimal("0.00")
            ),
            "movements_count": movements.count(),
            "denominations": denominations,
            "notes": session.notes,
        }

    @staticmethod
    def get_financial_summary() -> dict:
        """
        Retorna resumen financiero global de cajas y flujo de dinero.
        """
        from decimal import Decimal
        from django.db.models import Sum
        from django.utils import timezone

        open_sessions = CashSession.objects.filter(
            status=CashSession.SessionStatus.OPEN,
            is_active=True,
        ).select_related("cash_register", "user")

        total_open_expected = (
            open_sessions.aggregate(total=Sum("expected_balance"))["total"]
            or Decimal("0.00")
        )
        total_open_count = open_sessions.count()

        # Resumen del día de hoy
        today = timezone.localdate()
        today_movements = CashMovement.objects.filter(
            created_at__date=today,
            is_active=True,
        )

        today_cash_in = (
            today_movements.filter(is_cash=True, movement_type="IN").aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )
        today_cash_out = (
            today_movements.filter(is_cash=True, movement_type="OUT").aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )
        today_elec_in = (
            today_movements.filter(is_cash=False, movement_type="IN").aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )

        # Sesiones cerradas hoy y diferencias
        closed_today = CashSession.objects.filter(
            status=CashSession.SessionStatus.CLOSED,
            end_time__date=today,
            is_active=True,
        )
        total_difference_today = (
            closed_today.aggregate(total=Sum("difference"))["total"]
            or Decimal("0.00")
        )

        return {
            "open_sessions_count": total_open_count,
            "total_cash_in_drawers": str(total_open_expected),
            "today": {
                "date": str(today),
                "cash_in": str(today_cash_in),
                "cash_out": str(today_cash_out),
                "net_cash": str(today_cash_in - today_cash_out),
                "electronic_in": str(today_elec_in),
                "closed_sessions_count": closed_today.count(),
                "total_discrepancy": str(total_difference_today),
            },
            "active_sessions": [
                {
                    "session_id": s.id_cash_session,
                    "register_name": s.cash_register.name,
                    "user_name": s.user.get_full_name() or s.user.username,
                    "opening_balance": str(s.opening_balance),
                    "expected_balance": str(s.expected_balance),
                    "start_time": s.start_time,
                }
                for s in open_sessions
            ],
        }
