from decimal import Decimal

from django.db import models, transaction
from django.utils import timezone

from apps.cash.dto.cash_session_dto import CashSessionCloseDto, CashSessionOpenDto
from apps.cash.models.cash_movement import CashMovement
from apps.cash.models.cash_register import CashRegister
from apps.cash.models.cash_session import CashSession
from apps.core.exceptions.custom_exceptions import (
    CashRegisterAlreadyOpenException,
    CashRegisterNotFoundException,
    CashSessionAlreadyOpenException,
    CashSessionClosedException,
    InvalidCashAmountException,
)
from apps.core.services.base_service import BaseService


class CashSessionService(BaseService[CashSession]):
    """
    Servicio para manejar la lógica de las sesiones de caja.
    """

    def __init__(self):
        super().__init__(CashSession)

    @staticmethod
    @transaction.atomic
    def open_session(dto: CashSessionOpenDto, user) -> CashSession:
        if CashSession.objects.filter(
            user=user, status=CashSession.SessionStatus.OPEN, is_active=True
        ).exists():
            raise CashSessionAlreadyOpenException()

        try:
            register = CashRegister.objects.select_for_update().get(
                pk=dto.cash_register_id, is_active=True
            )
        except CashRegister.DoesNotExist:
            raise CashRegisterNotFoundException()

        if CashSession.objects.filter(
            cash_register=register,
            status=CashSession.SessionStatus.OPEN,
            is_active=True,
        ).exists():
            raise CashRegisterAlreadyOpenException()

        if dto.opening_balance < Decimal("0.00"):
            raise InvalidCashAmountException(
                "El efectivo inicial no puede ser negativo."
            )

        session = CashSession.objects.create(
            cash_register=register,
            user=user,
            opening_balance=dto.opening_balance,
            expected_balance=dto.opening_balance,
            status=CashSession.SessionStatus.OPEN,
            notes=dto.notes,
        )

        return session

    @staticmethod
    @transaction.atomic
    def close_session(session: CashSession, dto: CashSessionCloseDto) -> CashSession:
        # Bloqueo pesimista para sincronizar con movimientos concurrentes de venta
        session = CashSession.objects.select_for_update().get(pk=session.pk)

        if session.status != CashSession.SessionStatus.OPEN:
            raise CashSessionClosedException()

        if dto.counted_balance < Decimal("0.00"):
            raise InvalidCashAmountException(
                "El efectivo contado no puede ser negativo."
            )

        # Recálculo exacto del saldo esperado en base a movimientos reales en efectivo
        cash_in = (
            session.movements.filter(
                is_active=True,
                is_cash=True,
                movement_type=CashMovement.MovementType.IN,
            ).aggregate(total=models.Sum("amount"))["total"]
            or Decimal("0.00")
        )
        cash_out = (
            session.movements.filter(
                is_active=True,
                is_cash=True,
                movement_type=CashMovement.MovementType.OUT,
            ).aggregate(total=models.Sum("amount"))["total"]
            or Decimal("0.00")
        )
        real_expected = session.opening_balance + cash_in - cash_out
        session.expected_balance = real_expected

        session.end_time = timezone.now()
        session.counted_balance = dto.counted_balance
        session.difference = dto.counted_balance - session.expected_balance
        session.status = CashSession.SessionStatus.CLOSED

        notes_parts = []
        if session.notes:
            notes_parts.append(session.notes)
        if dto.notes:
            notes_parts.append(f"Cierre: {dto.notes}")
        if dto.denominations:
            import json

            notes_parts.append(f"DENOMINATIONS: {json.dumps(dto.denominations)}")

        session.notes = "\n".join(notes_parts).strip()

        session.save(
            update_fields=[
                "end_time",
                "expected_balance",
                "counted_balance",
                "difference",
                "status",
                "notes",
                "updated_at",
            ]
        )
        return session
