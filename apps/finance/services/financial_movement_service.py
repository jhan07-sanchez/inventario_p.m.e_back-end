from decimal import Decimal

from django.db import transaction

from apps.core.exceptions.custom_exceptions import (
    FinancialAccountNotFoundException,
    FinancialCategoryNotFoundException,
    FinancialMovementAlreadyReversedException,
    FinancialMovementNotFoundException,
    InsufficientAccountFundsException,
    InvalidFinancialAmountException,
    InvalidFinancialMovementStateException,
    InvalidFinancialMovementTypeException,
)
from apps.core.services.base_service import BaseService
from apps.finance.dto.financial_dto import FinancialMovementCreateDTO
from apps.finance.models.financial_account import FinancialAccount
from apps.finance.models.financial_category import FinancialCategory
from apps.finance.models.financial_movement import FinancialMovement


class FinancialMovementService(BaseService[FinancialMovement]):
    """
    Servicio de negocio para movimientos financieros (ingresos, egresos, reversos).
    Garantiza consistencia transaccional y actualización segura de saldos.
    """

    def __init__(self):
        super().__init__(FinancialMovement)

    @classmethod
    @transaction.atomic
    def record_movement(
        cls,
        dto: FinancialMovementCreateDTO,
        user,
    ) -> FinancialMovement:
        if dto.amount <= Decimal("0.00"):
            raise InvalidFinancialAmountException(
                "El monto del movimiento debe ser estrictamente mayor a cero."
            )

        try:
            account = FinancialAccount.objects.select_for_update().get(
                pk=dto.account_id, is_active=True
            )
        except FinancialAccount.DoesNotExist:
            raise FinancialAccountNotFoundException(
                "La cuenta financiera especificada no existe o se encuentra inactiva."
            )

        category = None
        if dto.category_id:
            try:
                category = FinancialCategory.objects.get(
                    pk=dto.category_id, is_active=True
                )
            except FinancialCategory.DoesNotExist:
                raise FinancialCategoryNotFoundException(
                    "La categoría financiera especificada no existe o está inactiva."
                )

        # Validaciones de saldo para egresos
        if dto.movement_type == FinancialMovement.MovementType.OUTFLOW:
            if account.account_type != FinancialAccount.AccountType.CREDIT:
                if dto.amount > account.current_balance:
                    raise InsufficientAccountFundsException(
                        f"Fondos insuficientes en la cuenta '{account.name}'. "
                        f"Saldo disponible: ${account.current_balance:,.2f}, Monto requerido: ${dto.amount:,.2f}."
                    )
            account.current_balance -= dto.amount
        elif dto.movement_type == FinancialMovement.MovementType.INFLOW:
            account.current_balance += dto.amount
        else:
            raise InvalidFinancialMovementTypeException(
                f"Tipo de movimiento '{dto.movement_type}' inválido."
            )

        account.save(update_fields=["current_balance", "updated_at"])

        movement = FinancialMovement.objects.create(
            account=account,
            category=category,
            movement_type=dto.movement_type,
            amount=dto.amount,
            payment_method=dto.payment_method,
            status=FinancialMovement.MovementStatus.COMPLETED,
            movement_date=dto.movement_date,
            description=dto.description.strip(),
            reference=dto.reference.strip(),
            origin_type=dto.origin_type,
            origin_id=dto.origin_id,
            user=user,
            notes=dto.notes.strip(),
        )
        return movement

    @classmethod
    @transaction.atomic
    def reverse_movement(
        cls,
        movement_id: int,
        reason: str,
        user,
    ) -> FinancialMovement:
        """
        Reversa un movimiento financiero previamente completado de forma auditable.
        No elimina el registro original; crea un contra-movimiento inverso vinculado.
        """
        try:
            original = FinancialMovement.objects.select_for_update().get(
                pk=movement_id, is_active=True
            )
        except FinancialMovement.DoesNotExist:
            raise FinancialMovementNotFoundException(
                "El movimiento financiero a reversar no existe o está inactivo."
            )

        if original.status != FinancialMovement.MovementStatus.COMPLETED:
            raise InvalidFinancialMovementStateException(
                f"No se puede reversar un movimiento con estado '{original.get_status_display()}'."
            )

        if hasattr(original, "reversed_by") and original.reversed_by is not None:
            raise FinancialMovementAlreadyReversedException(
                "Este movimiento ya ha sido reversado previamente."
            )

        account = FinancialAccount.objects.select_for_update().get(pk=original.account_id)

        # Determinar el tipo del contra-movimiento
        if original.movement_type == FinancialMovement.MovementType.INFLOW:
            # Reversar un ingreso requiere un egreso
            counter_type = FinancialMovement.MovementType.OUTFLOW
            if (
                account.account_type != FinancialAccount.AccountType.CREDIT
                and original.amount > account.current_balance
            ):
                raise InsufficientAccountFundsException(
                    f"No es posible reversar el ingreso porque la cuenta '{account.name}' "
                    f"tiene saldo menor (${account.current_balance:,.2f}) al importe a descontar (${original.amount:,.2f})."
                )
            account.current_balance -= original.amount
        else:
            # Reversar un egreso requiere un ingreso
            counter_type = FinancialMovement.MovementType.INFLOW
            account.current_balance += original.amount

        account.save(update_fields=["current_balance", "updated_at"])

        # Marcar original como REVERSED
        original.status = FinancialMovement.MovementStatus.REVERSED
        original.save(update_fields=["status", "updated_at"])

        # Crear contra-movimiento vinculado
        counter_movement = FinancialMovement.objects.create(
            account=account,
            category=original.category,
            movement_type=counter_type,
            amount=original.amount,
            payment_method=original.payment_method,
            status=FinancialMovement.MovementStatus.COMPLETED,
            movement_date=original.movement_date,
            description=f"REVERSO de #{original.id_financial_movement}: {reason.strip()}",
            reference=f"REV-{original.id_financial_movement}",
            origin_type=FinancialMovement.OriginType.ADJUSTMENT,
            origin_id=original.id_financial_movement,
            reversal_of=original,
            user=user,
            notes=f"Reverso justificado por {user.username}: {reason.strip()}",
        )

        return counter_movement
