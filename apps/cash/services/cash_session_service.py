from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.core.services.base_service import BaseService
from apps.cash.models.cash_session import CashSession
from apps.cash.models.cash_register import CashRegister
from apps.cash.dto.cash_session_dto import CashSessionOpenDto, CashSessionCloseDto


class CashSessionService(BaseService[CashSession]):
    """
    Servicio para manejar la lógica de las sesiones de caja.
    """
    def __init__(self):
        super().__init__(CashSession)

    @staticmethod
    @transaction.atomic
    def open_session(dto: CashSessionOpenDto, user) -> CashSession:
        if CashSession.objects.filter(user=user, status=CashSession.SessionStatus.OPEN).exists():
            raise ValidationError("El usuario ya tiene una sesión de caja abierta.")

        try:
            register = CashRegister.objects.get(pk=dto.cash_register_id, is_active=True)
        except CashRegister.DoesNotExist:
            raise ValidationError("La caja seleccionada no existe o está inactiva.")

        if CashSession.objects.filter(cash_register=register, status=CashSession.SessionStatus.OPEN).exists():
            raise ValidationError("La caja seleccionada ya está abierta por otro usuario.")

        if dto.opening_balance < Decimal("0.00"):
            raise ValidationError("El efectivo inicial no puede ser negativo.")

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
        if session.status != CashSession.SessionStatus.OPEN:
            raise ValidationError("La sesión ya se encuentra cerrada.")

        if dto.counted_balance < Decimal("0.00"):
            raise ValidationError("El efectivo contado no puede ser negativo.")

        session.end_time = timezone.now()
        session.counted_balance = dto.counted_balance
        session.difference = dto.counted_balance - session.expected_balance
        session.status = CashSession.SessionStatus.CLOSED
        
        if dto.notes:
            session.notes = f"{session.notes}\nCierre: {dto.notes}".strip()

        session.save(
            update_fields=["end_time", "counted_balance", "difference", "status", "notes", "updated_at"]
        )
        return session
