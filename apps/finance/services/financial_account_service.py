from decimal import Decimal

from django.db import transaction

from apps.core.exceptions.custom_exceptions import (
    FinancialAccountAlreadyExistsException,
    FinancialAccountNotFoundException,
    InvalidFinancialAmountException,
)
from apps.core.services.base_service import BaseService
from apps.finance.dto.financial_dto import (
    FinancialAccountCreateDTO,
    FinancialAccountUpdateDTO,
)
from apps.finance.models.financial_account import FinancialAccount


class FinancialAccountService(BaseService[FinancialAccount]):
    """
    Servicio de negocio para la gestión de cuentas financieras.
    """

    def __init__(self):
        super().__init__(FinancialAccount)

    @classmethod
    @transaction.atomic
    def create_account(cls, dto: FinancialAccountCreateDTO) -> FinancialAccount:
        if dto.initial_balance < Decimal("0.00"):
            raise InvalidFinancialAmountException(
                "El saldo inicial de la cuenta no puede ser negativo."
            )

        # Verificar unicidad de nombre activo
        existing = FinancialAccount.objects.filter(
            name__iexact=dto.name.strip(),
            is_active=True,
        )
        if dto.company_id:
            existing = existing.filter(company_id=dto.company_id)
        if existing.exists():
            raise FinancialAccountAlreadyExistsException(
                f"Ya existe una cuenta financiera activa con el nombre '{dto.name}'."
            )

        account = FinancialAccount.objects.create(
            name=dto.name.strip(),
            account_type=dto.account_type,
            account_number=dto.account_number.strip(),
            bank_name=dto.bank_name.strip(),
            currency=dto.currency.upper(),
            initial_balance=dto.initial_balance,
            current_balance=dto.initial_balance,
            description=dto.description.strip(),
            company_id=dto.company_id,
        )
        return account

    @classmethod
    @transaction.atomic
    def update_account(
        cls, account_id: int, dto: FinancialAccountUpdateDTO
    ) -> FinancialAccount:
        try:
            account = FinancialAccount.objects.select_for_update().get(
                pk=account_id, is_active=True
            )
        except FinancialAccount.DoesNotExist:
            raise FinancialAccountNotFoundException()

        if dto.name and dto.name.strip() != account.name:
            existing = (
                FinancialAccount.objects.filter(
                    name__iexact=dto.name.strip(),
                    is_active=True,
                )
                .exclude(pk=account_id)
            )
            if account.company_id:
                existing = existing.filter(company_id=account.company_id)
            if existing.exists():
                raise FinancialAccountAlreadyExistsException(
                    f"Ya existe otra cuenta activa con el nombre '{dto.name}'."
                )
            account.name = dto.name.strip()

        if dto.account_type:
            account.account_type = dto.account_type
        if dto.account_number is not None:
            account.account_number = dto.account_number.strip()
        if dto.bank_name is not None:
            account.bank_name = dto.bank_name.strip()
        if dto.description is not None:
            account.description = dto.description.strip()

        account.save()
        return account

    @classmethod
    @transaction.atomic
    def deactivate_account(cls, account_id: int) -> None:
        try:
            account = FinancialAccount.objects.select_for_update().get(
                pk=account_id, is_active=True
            )
        except FinancialAccount.DoesNotExist:
            raise FinancialAccountNotFoundException()

        account.soft_delete()

    @classmethod
    @transaction.atomic
    def restore_account(cls, account_id: int) -> FinancialAccount:
        """
        Restaura una cuenta financiera previamente desactivada (soft delete).
        Valida que no exista otra cuenta activa con el mismo nombre.
        """
        try:
            account = FinancialAccount.all_objects.select_for_update().get(pk=account_id)
        except FinancialAccount.DoesNotExist:
            raise FinancialAccountNotFoundException()

        if account.is_active:
            return account

        # Verificar unicidad de nombre con cuentas activas
        existing = FinancialAccount.objects.filter(
            name__iexact=account.name.strip(),
            is_active=True,
        ).exclude(pk=account_id)
        if account.company_id:
            existing = existing.filter(company_id=account.company_id)
        if existing.exists():
            raise FinancialAccountAlreadyExistsException(
                f"Ya existe una cuenta financiera activa con el nombre '{account.name}'."
            )

        account.restore()
        return account
