from datetime import date
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.enums import PaymentMethod
from apps.core.exceptions.custom_exceptions import (
    FinancialAccountNotFoundException,
    FinancialCategoryNotFoundException,
    FinancialMovementAlreadyReversedException,
    FinancialMovementNotFoundException,
    InsufficientAccountFundsException,
    InvalidFinancialAmountException,
    InvalidFinancialMovementStateException,
)
from apps.finance.dto.financial_dto import (
    FinancialAccountCreateDTO,
    FinancialMovementCreateDTO,
)
from apps.finance.models.financial_account import FinancialAccount
from apps.finance.models.financial_category import FinancialCategory
from apps.finance.models.financial_movement import FinancialMovement
from apps.finance.services.financial_account_service import FinancialAccountService
from apps.finance.services.financial_movement_service import FinancialMovementService
from apps.users.models import Role, User, UserRole


class FinancialMovementTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="tesorero_mov",
            password="Password123!",
            email="tesorero_mov@example.com",
            document_number="80002001",
        )
        self.role = Role.objects.create(
            role_name="tesoreria_mov_role",
            permissions={
                "finance.view": True,
                "finance.create": True,
                "finance.update": True,
            },
        )
        UserRole.objects.create(user=self.user, role=self.role)
        self.client.force_authenticate(user=self.user)

        self.account = FinancialAccountService.create_account(
            FinancialAccountCreateDTO(
                name="Bancolombia Principal",
                account_type=FinancialAccount.AccountType.BANK,
                initial_balance=Decimal("1000000.00"),
            )
        )
        self.category = FinancialCategory.objects.create(
            name="Venta Servicios",
            category_type=FinancialCategory.CategoryType.INFLOW,
        )

    def test_record_inflow_movement_increases_balance(self):
        dto = FinancialMovementCreateDTO(
            account_id=self.account.pk,
            category_id=self.category.pk,
            movement_type=FinancialMovement.MovementType.INFLOW,
            amount=Decimal("500000.00"),
            payment_method=PaymentMethod.TRANSFER,
            movement_date=date.today(),
            description="Cobro por consultoría",
        )
        movement = FinancialMovementService.record_movement(dto, user=self.user)

        self.account.refresh_from_db()
        self.assertEqual(movement.status, FinancialMovement.MovementStatus.COMPLETED)
        self.assertEqual(self.account.current_balance, Decimal("1500000.00"))

    def test_record_outflow_movement_decreases_balance(self):
        dto = FinancialMovementCreateDTO(
            account_id=self.account.pk,
            category_id=self.category.pk,
            movement_type=FinancialMovement.MovementType.OUTFLOW,
            amount=Decimal("300000.00"),
            payment_method=PaymentMethod.TRANSFER,
            movement_date=date.today(),
            description="Pago servicios públicos",
        )
        movement = FinancialMovementService.record_movement(dto, user=self.user)

        self.account.refresh_from_db()
        self.assertEqual(movement.status, FinancialMovement.MovementStatus.COMPLETED)
        self.assertEqual(self.account.current_balance, Decimal("700000.00"))

    def test_record_outflow_insufficient_funds_raises_error(self):
        dto = FinancialMovementCreateDTO(
            account_id=self.account.pk,
            movement_type=FinancialMovement.MovementType.OUTFLOW,
            amount=Decimal("2000000.00"),  # Mayor al saldo disponible
            movement_date=date.today(),
            description="Egreso excesivo",
        )
        with self.assertRaises(InsufficientAccountFundsException):
            FinancialMovementService.record_movement(dto, user=self.user)

        self.account.refresh_from_db()
        self.assertEqual(self.account.current_balance, Decimal("1000000.00"))

    def test_record_movement_zero_or_negative_amount_raises_error(self):
        dto = FinancialMovementCreateDTO(
            account_id=self.account.pk,
            movement_type=FinancialMovement.MovementType.INFLOW,
            amount=Decimal("0.00"),
            movement_date=date.today(),
            description="Monto cero",
        )
        with self.assertRaises(InvalidFinancialAmountException):
            FinancialMovementService.record_movement(dto, user=self.user)

    def test_record_movement_non_existent_account_raises_error(self):
        dto = FinancialMovementCreateDTO(
            account_id=999999,
            movement_type=FinancialMovement.MovementType.INFLOW,
            amount=Decimal("100.00"),
            movement_date=date.today(),
            description="Cuenta inexistente",
        )
        with self.assertRaises(FinancialAccountNotFoundException):
            FinancialMovementService.record_movement(dto, user=self.user)

    def test_reverse_movement_creates_counter_movement_and_restores_balance(self):
        # 1. Registrar un egreso de 200,000 (saldo baja a 800,000)
        dto = FinancialMovementCreateDTO(
            account_id=self.account.pk,
            movement_type=FinancialMovement.MovementType.OUTFLOW,
            amount=Decimal("200000.00"),
            movement_date=date.today(),
            description="Pago erróneo",
        )
        original_mov = FinancialMovementService.record_movement(dto, user=self.user)
        self.account.refresh_from_db()
        self.assertEqual(self.account.current_balance, Decimal("800000.00"))

        # 2. Reversar el egreso (debe devolver el saldo a 1,000,000)
        counter_mov = FinancialMovementService.reverse_movement(
            movement_id=original_mov.pk,
            reason="Error en el destinatario del pago",
            user=self.user,
        )

        original_mov.refresh_from_db()
        self.account.refresh_from_db()

        self.assertEqual(original_mov.status, FinancialMovement.MovementStatus.REVERSED)
        self.assertEqual(counter_mov.movement_type, FinancialMovement.MovementType.INFLOW)
        self.assertEqual(counter_mov.reversal_of, original_mov)
        self.assertEqual(self.account.current_balance, Decimal("1000000.00"))

    def test_reverse_already_reversed_movement_raises_error(self):
        dto = FinancialMovementCreateDTO(
            account_id=self.account.pk,
            movement_type=FinancialMovement.MovementType.OUTFLOW,
            amount=Decimal("50000.00"),
            movement_date=date.today(),
            description="Pago reversible",
        )
        original_mov = FinancialMovementService.record_movement(dto, user=self.user)
        FinancialMovementService.reverse_movement(
            movement_id=original_mov.pk,
            reason="Primer reverso",
            user=self.user,
        )

        with self.assertRaises(InvalidFinancialMovementStateException):
            FinancialMovementService.reverse_movement(
                movement_id=original_mov.pk,
                reason="Segundo reverso",
                user=self.user,
            )

    def test_movement_endpoints(self):
        url = reverse("financial-movements-list")
        payload = {
            "account_id": self.account.pk,
            "movement_type": "INFLOW",
            "amount": "150000.00",
            "movement_date": str(date.today()),
            "description": "Ingreso extra",
        }
        res = self.client.post(url, data=payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        mov_id = res.data["data"]["id_financial_movement"]

        # Reversar via API
        rev_url = reverse("financial-movements-reverse", kwargs={"pk": mov_id})
        res_rev = self.client.post(rev_url, data={"reason": "Ajuste"}, format="json")
        self.assertEqual(res_rev.status_code, status.HTTP_200_OK)
