from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.core.enums import PaymentMethod
from apps.core.services.base_service import BaseService
from apps.cash.models.cash_movement import CashMovement
from apps.cash.models.cash_session import CashSession
from apps.cash.models.payment import Payment
from apps.cash.dto.cash_movement_dto import CashMovementCreateDto


class CashMovementService(BaseService[CashMovement]):
    """
    Servicio para registrar movimientos de caja.
    """
    def __init__(self):
        super().__init__(CashMovement)

    @staticmethod
    @transaction.atomic
    def create_movement(dto: CashMovementCreateDto) -> CashMovement:
        try:
            session = CashSession.objects.select_for_update().get(pk=dto.cash_session_id)
        except CashSession.DoesNotExist:
            raise ValidationError("La sesión de caja no existe.")

        if session.status != CashSession.SessionStatus.OPEN:
            raise ValidationError("No se pueden registrar movimientos en una sesión cerrada.")

        payment = None
        if dto.payment_id:
            try:
                payment = Payment.objects.get(pk=dto.payment_id)
            except Payment.DoesNotExist:
                raise ValidationError("El pago asociado no existe.")

            import dataclasses
            is_cash = PaymentMethod.is_cash(payment.payment_method)
            dto = dataclasses.replace(dto, is_cash=is_cash)

        if dto.amount <= Decimal("0.00"):
            raise ValidationError("El monto del movimiento debe ser mayor a cero.")

        if dto.is_cash and dto.movement_type == CashMovement.MovementType.OUT:
            if dto.amount > session.expected_balance:
                raise ValidationError(
                    f"El monto del retiro (${dto.amount}) supera el efectivo disponible en caja (${session.expected_balance})."
                )

        movement = CashMovement.objects.create(
            cash_session=session,
            payment=payment,
            amount=dto.amount,
            movement_type=dto.movement_type,
            is_cash=dto.is_cash,
            reference=dto.reference,
            description=dto.description,
        )

        if dto.is_cash:
            if dto.movement_type == CashMovement.MovementType.IN:
                session.expected_balance += dto.amount
            elif dto.movement_type == CashMovement.MovementType.OUT:
                session.expected_balance -= dto.amount
            
            session.save(update_fields=["expected_balance", "updated_at"])

        return movement
