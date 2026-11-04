from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.core.exceptions.custom_exceptions import (
    FinancialAccountNotFoundException,
    FinancialReconciliationAlreadyClosedException,
    FinancialReconciliationNotFoundException,
    InvalidFinancialReconciliationDatesException,
)
from apps.core.services.base_service import BaseService
from apps.finance.dto.financial_dto import FinancialReconciliationCreateDTO
from apps.finance.models.financial_account import FinancialAccount
from apps.finance.models.financial_reconciliation import FinancialReconciliation


class FinancialReconciliationService(BaseService[FinancialReconciliation]):
    """
    Servicio de negocio para conciliaciones financieras y arqueos de cuentas.
    """

    def __init__(self):
        super().__init__(FinancialReconciliation)

    @classmethod
    @transaction.atomic
    def create_reconciliation(
        cls,
        dto: FinancialReconciliationCreateDTO,
        user,
    ) -> FinancialReconciliation:
        if dto.start_date > dto.end_date:
            raise InvalidFinancialReconciliationDatesException(
                "La fecha de inicio no puede ser posterior a la fecha de corte."
            )

        try:
            account = FinancialAccount.objects.get(pk=dto.account_id, is_active=True)
        except FinancialAccount.DoesNotExist:
            raise FinancialAccountNotFoundException(
                "La cuenta financiera especificada no existe o está inactiva."
            )

        # El saldo en libros actual según el sistema
        book_balance = account.current_balance
        difference = dto.statement_balance - book_balance

        reconciliation = FinancialReconciliation.objects.create(
            account=account,
            start_date=dto.start_date,
            end_date=dto.end_date,
            statement_balance=dto.statement_balance,
            book_balance=book_balance,
            difference=difference,
            status=FinancialReconciliation.ReconciliationStatus.DRAFT,
            user=user,
            notes=dto.notes.strip(),
        )
        return reconciliation

    @classmethod
    @transaction.atomic
    def close_reconciliation(
        cls,
        reconciliation_id: int,
        user,
    ) -> FinancialReconciliation:
        try:
            reconciliation = FinancialReconciliation.objects.select_for_update().get(
                pk=reconciliation_id, is_active=True
            )
        except FinancialReconciliation.DoesNotExist:
            raise FinancialReconciliationNotFoundException(
                "La conciliación financiera no existe o está inactiva."
            )

        if reconciliation.status == FinancialReconciliation.ReconciliationStatus.RECONCILED:
            raise FinancialReconciliationAlreadyClosedException(
                "La conciliación ya se encuentra cerrada y conciliada."
            )

        # Recalcular diferencia final
        account = reconciliation.account
        reconciliation.book_balance = account.current_balance
        reconciliation.difference = (
            reconciliation.statement_balance - reconciliation.book_balance
        )
        reconciliation.status = (
            FinancialReconciliation.ReconciliationStatus.RECONCILED
        )
        reconciliation.reconciled_at = timezone.now()
        reconciliation.save(
            update_fields=[
                "book_balance",
                "difference",
                "status",
                "reconciled_at",
                "updated_at",
            ]
        )
        return reconciliation
