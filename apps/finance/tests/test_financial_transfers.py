from datetime import date
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.exceptions.custom_exceptions import (
    FinancialAccountNotFoundException,
    FinancialTransferNotFoundException,
    InsufficientAccountFundsException,
    InvalidFinancialAmountException,
    InvalidFinancialTransferException,
    InvalidFinancialTransferStateException,
)
from apps.finance.dto.financial_dto import (
    FinancialAccountCreateDTO,
    FinancialTransferCreateDTO,
)
from apps.finance.models.financial_account import FinancialAccount
from apps.finance.models.financial_movement import FinancialMovement
from apps.finance.models.financial_transfer import FinancialTransfer
from apps.finance.services.financial_account_service import FinancialAccountService
from apps.finance.services.financial_transfer_service import FinancialTransferService
from apps.users.models import Role, User, UserRole


class FinancialTransferTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="tesorero_transf",
            password="Password123!",
            email="tesorero_transf@example.com",
            document_number="80003001",
        )
        self.role = Role.objects.create(
            role_name="tesoreria_transf_role",
            permissions={
                "finance.view": True,
                "finance.transfer": True,
            },
        )
        UserRole.objects.create(user=self.user, role=self.role)
        self.client.force_authenticate(user=self.user)

        self.account_a = FinancialAccountService.create_account(
            FinancialAccountCreateDTO(
                name="Cuenta Origen A",
                account_type=FinancialAccount.AccountType.BANK,
                initial_balance=Decimal("2000000.00"),
            )
        )
        self.account_b = FinancialAccountService.create_account(
            FinancialAccountCreateDTO(
                name="Cuenta Destino B",
                account_type=FinancialAccount.AccountType.BANK,
                initial_balance=Decimal("500000.00"),
            )
        )

    def test_execute_transfer_success_and_neutral_integrity(self):
        dto = FinancialTransferCreateDTO(
            source_account_id=self.account_a.pk,
            destination_account_id=self.account_b.pk,
            amount=Decimal("400000.00"),
            transfer_date=date.today(),
            reference="TRF-001",
            notes="Traslado de fondos operativos",
        )
        transfer = FinancialTransferService.execute_transfer(dto, user=self.user)

        self.account_a.refresh_from_db()
        self.account_b.refresh_from_db()

        # Cuenta origen debitada
        self.assertEqual(self.account_a.current_balance, Decimal("1600000.00"))
        # Cuenta destino acreditada
        self.assertEqual(self.account_b.current_balance, Decimal("900000.00"))

        # El dinero global total permanece idéntico: 2,500,000
        total_balance = self.account_a.current_balance + self.account_b.current_balance
        self.assertEqual(total_balance, Decimal("2500000.00"))

        # Se crearon exactamente 2 movimientos vinculados de tipo TRANSFER
        movements = FinancialMovement.objects.filter(transfer=transfer)
        self.assertEqual(movements.count(), 2)

        outflow = movements.get(movement_type=FinancialMovement.MovementType.OUTFLOW)
        inflow = movements.get(movement_type=FinancialMovement.MovementType.INFLOW)

        self.assertEqual(outflow.account, self.account_a)
        self.assertEqual(inflow.account, self.account_b)
        self.assertEqual(outflow.origin_type, FinancialMovement.OriginType.TRANSFER)
        self.assertEqual(inflow.origin_type, FinancialMovement.OriginType.TRANSFER)

    def test_transfer_same_account_raises_error(self):
        dto = FinancialTransferCreateDTO(
            source_account_id=self.account_a.pk,
            destination_account_id=self.account_a.pk,
            amount=Decimal("10000.00"),
            transfer_date=date.today(),
        )
        with self.assertRaises(InvalidFinancialTransferException):
            FinancialTransferService.execute_transfer(dto, user=self.user)

    def test_transfer_negative_or_zero_amount_raises_error(self):
        dto = FinancialTransferCreateDTO(
            source_account_id=self.account_a.pk,
            destination_account_id=self.account_b.pk,
            amount=Decimal("0.00"),
            transfer_date=date.today(),
        )
        with self.assertRaises(InvalidFinancialAmountException):
            FinancialTransferService.execute_transfer(dto, user=self.user)

    def test_transfer_non_existent_source_raises_error(self):
        dto = FinancialTransferCreateDTO(
            source_account_id=999999,
            destination_account_id=self.account_b.pk,
            amount=Decimal("1000.00"),
            transfer_date=date.today(),
        )
        with self.assertRaises(FinancialAccountNotFoundException):
            FinancialTransferService.execute_transfer(dto, user=self.user)

    def test_transfer_insufficient_funds_raises_error(self):
        dto = FinancialTransferCreateDTO(
            source_account_id=self.account_a.pk,
            destination_account_id=self.account_b.pk,
            amount=Decimal("3000000.00"),  # Supera los 2,000,000 disponibles
            transfer_date=date.today(),
        )
        with self.assertRaises(InsufficientAccountFundsException):
            FinancialTransferService.execute_transfer(dto, user=self.user)

    def test_cancel_transfer_restores_balances(self):
        dto = FinancialTransferCreateDTO(
            source_account_id=self.account_a.pk,
            destination_account_id=self.account_b.pk,
            amount=Decimal("500000.00"),
            transfer_date=date.today(),
        )
        transfer = FinancialTransferService.execute_transfer(dto, user=self.user)

        # Cancelar la transferencia
        FinancialTransferService.cancel_transfer(
            transfer_id=transfer.pk,
            reason="Cancelación por solicitud de gerencia",
            user=self.user,
        )

        self.account_a.refresh_from_db()
        self.account_b.refresh_from_db()
        transfer.refresh_from_db()

        self.assertEqual(transfer.status, FinancialTransfer.TransferStatus.CANCELLED)
        self.assertEqual(self.account_a.current_balance, Decimal("2000000.00"))
        self.assertEqual(self.account_b.current_balance, Decimal("500000.00"))

    def test_cancel_already_cancelled_transfer_raises_error(self):
        dto = FinancialTransferCreateDTO(
            source_account_id=self.account_a.pk,
            destination_account_id=self.account_b.pk,
            amount=Decimal("100000.00"),
            transfer_date=date.today(),
        )
        transfer = FinancialTransferService.execute_transfer(dto, user=self.user)
        FinancialTransferService.cancel_transfer(
            transfer_id=transfer.pk,
            reason="Primera cancelación",
            user=self.user,
        )

        with self.assertRaises(InvalidFinancialTransferStateException):
            FinancialTransferService.cancel_transfer(
                transfer_id=transfer.pk,
                reason="Segunda cancelación",
                user=self.user,
            )

    def test_transfer_endpoints(self):
        url = reverse("financial-transfers-list")
        payload = {
            "source_account_id": self.account_a.pk,
            "destination_account_id": self.account_b.pk,
            "amount": "100000.00",
            "transfer_date": str(date.today()),
            "reference": "API-TRF-01",
        }
        res = self.client.post(url, data=payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        transfer_id = res.data["data"]["id_financial_transfer"]

        # Cancelar via API
        cancel_url = reverse("financial-transfers-cancel", kwargs={"pk": transfer_id})
        res_cancel = self.client.post(
            cancel_url, data={"reason": "Cancelación prueba"}, format="json"
        )
        self.assertEqual(res_cancel.status_code, status.HTTP_200_OK)
        self.assertEqual(
            res_cancel.data["data"]["status"],
            FinancialTransfer.TransferStatus.CANCELLED,
        )
