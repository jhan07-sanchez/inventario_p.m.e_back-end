from datetime import date
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.exceptions.custom_exceptions import (
    FinancialAccountNotFoundException,
    FinancialReconciliationAlreadyClosedException,
    FinancialReconciliationNotFoundException,
    InvalidFinancialReconciliationDatesException,
)
from apps.finance.dto.financial_dto import (
    FinancialAccountCreateDTO,
    FinancialReconciliationCreateDTO,
)
from apps.finance.models.financial_account import FinancialAccount
from apps.finance.models.financial_reconciliation import FinancialReconciliation
from apps.finance.services.financial_account_service import FinancialAccountService
from apps.finance.services.financial_reconciliation_service import (
    FinancialReconciliationService,
)
from apps.users.models import Role, User, UserRole


class FinancialReconciliationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="auditor_recon",
            password="Password123!",
            email="auditor_recon@example.com",
            document_number="80004001",
        )
        self.role = Role.objects.create(
            role_name="auditor_recon_role",
            permissions={
                "finance.view": True,
                "finance.reconcile": True,
            },
        )
        UserRole.objects.create(user=self.user, role=self.role)
        self.client.force_authenticate(user=self.user)

        self.account = FinancialAccountService.create_account(
            FinancialAccountCreateDTO(
                name="Davivienda Operativa",
                account_type=FinancialAccount.AccountType.BANK,
                initial_balance=Decimal("3500000.00"),
            )
        )

    def test_create_and_close_reconciliation_service(self):
        dto = FinancialReconciliationCreateDTO(
            account_id=self.account.pk,
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 31),
            statement_balance=Decimal("3520000.00"),  # 20,000 más que libros
            notes="Diferencia de $20,000 por intereses a favor",
        )
        recon = FinancialReconciliationService.create_reconciliation(dto, user=self.user)

        self.assertEqual(
            recon.status, FinancialReconciliation.ReconciliationStatus.DRAFT
        )
        self.assertEqual(recon.book_balance, Decimal("3500000.00"))
        self.assertEqual(recon.difference, Decimal("20000.00"))

        # Cerrar conciliación
        closed_recon = FinancialReconciliationService.close_reconciliation(
            reconciliation_id=recon.pk, user=self.user
        )
        self.assertEqual(
            closed_recon.status, FinancialReconciliation.ReconciliationStatus.RECONCILED
        )
        self.assertIsNotNone(closed_recon.reconciled_at)

    def test_reconciliation_invalid_dates_raises_error(self):
        dto = FinancialReconciliationCreateDTO(
            account_id=self.account.pk,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 10, 1),  # Fecha inicio > fin
            statement_balance=Decimal("3500000.00"),
        )
        with self.assertRaises(InvalidFinancialReconciliationDatesException):
            FinancialReconciliationService.create_reconciliation(dto, user=self.user)

    def test_reconciliation_non_existent_account_raises_error(self):
        dto = FinancialReconciliationCreateDTO(
            account_id=999999,
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 31),
            statement_balance=Decimal("10000.00"),
        )
        with self.assertRaises(FinancialAccountNotFoundException):
            FinancialReconciliationService.create_reconciliation(dto, user=self.user)

    def test_close_already_closed_reconciliation_raises_error(self):
        dto = FinancialReconciliationCreateDTO(
            account_id=self.account.pk,
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 31),
            statement_balance=Decimal("3500000.00"),
        )
        recon = FinancialReconciliationService.create_reconciliation(dto, user=self.user)
        FinancialReconciliationService.close_reconciliation(
            reconciliation_id=recon.pk, user=self.user
        )

        with self.assertRaises(FinancialReconciliationAlreadyClosedException):
            FinancialReconciliationService.close_reconciliation(
                reconciliation_id=recon.pk, user=self.user
            )

    def test_close_non_existent_reconciliation_raises_error(self):
        with self.assertRaises(FinancialReconciliationNotFoundException):
            FinancialReconciliationService.close_reconciliation(
                reconciliation_id=999999, user=self.user
            )

    def test_reconciliation_endpoints(self):
        url = reverse("financial-reconciliations-list")
        payload = {
            "account_id": self.account.pk,
            "start_date": "2026-10-01",
            "end_date": "2026-10-31",
            "statement_balance": "3500000.00",
            "notes": "Sin diferencias",
        }
        res = self.client.post(url, data=payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recon_id = res.data["data"]["id_reconciliation"]

        # Cerrar via API
        close_url = reverse("financial-reconciliations-close", kwargs={"pk": recon_id})
        res_close = self.client.post(close_url)
        self.assertEqual(res_close.status_code, status.HTTP_200_OK)
        self.assertEqual(
            res_close.data["data"]["status"],
            FinancialReconciliation.ReconciliationStatus.RECONCILED,
        )
