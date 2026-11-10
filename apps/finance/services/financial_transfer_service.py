from decimal import Decimal

from django.db import transaction

from apps.core.enums import PaymentMethod
from apps.core.exceptions.custom_exceptions import (
    FinancialAccountNotFoundException,
    FinancialTransferNotFoundException,
    InsufficientAccountFundsException,
    InvalidFinancialAmountException,
    InvalidFinancialTransferException,
    InvalidFinancialTransferStateException,
)
from apps.core.services.base_service import BaseService
from apps.finance.services.finance_cache_service import FinanceCacheService
from apps.finance.dto.financial_dto import FinancialTransferCreateDTO
from apps.finance.models.financial_account import FinancialAccount
from apps.finance.models.financial_movement import FinancialMovement
from apps.finance.models.financial_transfer import FinancialTransfer


class FinancialTransferService(BaseService[FinancialTransfer]):
    """
    Servicio de negocio para transferencias entre cuentas financieras propias.
    Garantiza consistencia transaccional, prevención de deadlocks y neutralidad contable.
    """

    def __init__(self):
        super().__init__(FinancialTransfer)

    @classmethod
    @transaction.atomic
    def execute_transfer(
        cls,
        dto: FinancialTransferCreateDTO,
        user,
        company_id: int | None = None,
    ) -> FinancialTransfer:
        if dto.source_account_id == dto.destination_account_id:
            raise InvalidFinancialTransferException(
                "La cuenta de origen y destino no pueden ser la misma."
            )

        if dto.amount <= Decimal("0.00"):
            raise InvalidFinancialAmountException(
                "El monto a transferir debe ser mayor a cero."
            )

        # Ordenar los IDs al bloquear para prevenir deadlocks en transacciones concurrentes
        ids = sorted([dto.source_account_id, dto.destination_account_id])
        accounts = {
            acc.pk: acc
            for acc in FinancialAccount.objects.select_for_update()
            .filter(pk__in=ids, is_active=True)
        }

        if dto.source_account_id not in accounts:
            raise FinancialAccountNotFoundException(
                "La cuenta de origen no existe o está inactiva."
            )
        if dto.destination_account_id not in accounts:
            raise FinancialAccountNotFoundException(
                "La cuenta de destino no existe o está inactiva."
            )

        source_acc = accounts[dto.source_account_id]
        dest_acc = accounts[dto.destination_account_id]

        if source_acc.company_id != dest_acc.company_id:
            raise InvalidFinancialTransferException(
                "No se pueden realizar transferencias entre cuentas pertenecientes a diferentes empresas."
            )
        if company_id is not None and source_acc.company_id != company_id:
            raise FinancialAccountNotFoundException(
                "Las cuentas financieras especificadas no pertenecen a la empresa activa."
            )

        if source_acc.account_type != FinancialAccount.AccountType.CREDIT:
            if dto.amount > source_acc.current_balance:
                raise InsufficientAccountFundsException(
                    f"Fondos insuficientes en la cuenta origen '{source_acc.name}'. "
                    f"Saldo disponible: ${source_acc.current_balance:,.2f}, Monto requerido: ${dto.amount:,.2f}."
                )

        # Actualizar saldos
        source_acc.current_balance -= dto.amount
        dest_acc.current_balance += dto.amount

        source_acc.save(update_fields=["current_balance", "updated_at"])
        dest_acc.save(update_fields=["current_balance", "updated_at"])

        # Crear registro de transferencia
        transfer = FinancialTransfer.objects.create(
            source_account=source_acc,
            destination_account=dest_acc,
            amount=dto.amount,
            transfer_date=dto.transfer_date,
            reference=dto.reference.strip(),
            notes=dto.notes.strip(),
            status=FinancialTransfer.TransferStatus.COMPLETED,
            user=user,
        )

        # Crear movimiento de egreso en cuenta origen
        FinancialMovement.objects.create(
            account=source_acc,
            movement_type=FinancialMovement.MovementType.OUTFLOW,
            amount=dto.amount,
            payment_method=PaymentMethod.TRANSFER,
            status=FinancialMovement.MovementStatus.COMPLETED,
            movement_date=dto.transfer_date,
            description=f"Transferencia enviada a {dest_acc.name}",
            reference=dto.reference.strip(),
            origin_type=FinancialMovement.OriginType.TRANSFER,
            origin_id=transfer.id_financial_transfer,
            transfer=transfer,
            user=user,
            notes=dto.notes.strip(),
        )

        # Crear movimiento de ingreso en cuenta destino
        FinancialMovement.objects.create(
            account=dest_acc,
            movement_type=FinancialMovement.MovementType.INFLOW,
            amount=dto.amount,
            payment_method=PaymentMethod.TRANSFER,
            status=FinancialMovement.MovementStatus.COMPLETED,
            movement_date=dto.transfer_date,
            description=f"Transferencia recibida desde {source_acc.name}",
            reference=dto.reference.strip(),
            origin_type=FinancialMovement.OriginType.TRANSFER,
            origin_id=transfer.id_financial_transfer,
            transfer=transfer,
            user=user,
            notes=dto.notes.strip(),
        )

        # Romper la cache del dashboard financiero para reflejar la nueva transferencia
        FinanceCacheService.invalidate_dashboard_cache(
            company_id=source_acc.company_id,
        )

        return transfer

    @classmethod
    @transaction.atomic
    def cancel_transfer(
        cls,
        transfer_id: int,
        reason: str,
        user,
    ) -> FinancialTransfer:
        """
        Cancela una transferencia previa restaurando los fondos de forma atómica.
        """
        try:
            transfer = FinancialTransfer.objects.select_for_update().get(
                pk=transfer_id, is_active=True
            )
        except FinancialTransfer.DoesNotExist:
            raise FinancialTransferNotFoundException(
                "La transferencia financiera no existe o está inactiva."
            )

        if transfer.status != FinancialTransfer.TransferStatus.COMPLETED:
            raise InvalidFinancialTransferStateException(
                f"No se puede cancelar una transferencia con estado '{transfer.get_status_display()}'."
            )

        ids = sorted([transfer.source_account_id, transfer.destination_account_id])
        accounts = {
            acc.pk: acc
            for acc in FinancialAccount.objects.select_for_update().filter(pk__in=ids)
        }

        source_acc = accounts[transfer.source_account_id]
        dest_acc = accounts[transfer.destination_account_id]

        if dest_acc.account_type != FinancialAccount.AccountType.CREDIT:
            if transfer.amount > dest_acc.current_balance:
                raise InsufficientAccountFundsException(
                    f"No se puede cancelar la transferencia porque la cuenta destino '{dest_acc.name}' "
                    f"ya no cuenta con saldo suficiente (${dest_acc.current_balance:,.2f}) para devolver ${transfer.amount:,.2f}."
                )

        dest_acc.current_balance -= transfer.amount
        source_acc.current_balance += transfer.amount

        dest_acc.save(update_fields=["current_balance", "updated_at"])
        source_acc.save(update_fields=["current_balance", "updated_at"])

        transfer.status = FinancialTransfer.TransferStatus.CANCELLED
        transfer.notes = f"{transfer.notes}\nCancelada por {user.username}: {reason}".strip()
        transfer.save(update_fields=["status", "notes", "updated_at"])

        # Marcar movimientos asociados como CANCELLED
        transfer.movements.update(status=FinancialMovement.MovementStatus.CANCELLED)

        # Romper la cache del dashboard financiero para reflejar la transferencia cancelada
        FinanceCacheService.invalidate_dashboard_cache(
            company_id=source_acc.company_id,
        )

        return transfer
