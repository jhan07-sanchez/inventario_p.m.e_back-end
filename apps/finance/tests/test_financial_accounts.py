from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.exceptions.custom_exceptions import (
    FinancialAccountAlreadyExistsException,
    FinancialAccountNotFoundException,
    InvalidFinancialAmountException,
)
from apps.finance.dto.financial_dto import (
    FinancialAccountCreateDTO,
    FinancialAccountUpdateDTO,
)
from apps.finance.models.financial_account import FinancialAccount
from apps.finance.services.financial_account_service import FinancialAccountService
from apps.users.models import Role, User, UserRole


class FinancialAccountTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="tesorero",
            password="Password123!",
            email="tesorero@example.com",
            document_number="80001001",
        )
        self.role = Role.objects.create(
            role_name="tesoreria_role",
            permissions={
                "finance.view": True,
                "finance.create": True,
                "finance.update": True,
                "finance.delete": True,
            },
        )
        UserRole.objects.create(user=self.user, role=self.role)
        self.client.force_authenticate(user=self.user)

    def test_create_account_service_success(self):
        dto = FinancialAccountCreateDTO(
            name="Bancolombia Ahorros",
            account_type=FinancialAccount.AccountType.BANK,
            account_number="123456789",
            bank_name="Bancolombia",
            currency="COP",
            initial_balance=Decimal("5000000.00"),
            description="Cuenta principal operativa",
        )
        account = FinancialAccountService.create_account(dto)

        self.assertIsNotNone(account.pk)
        self.assertEqual(account.name, "Bancolombia Ahorros")
        self.assertEqual(account.current_balance, Decimal("5000000.00"))
        self.assertTrue(account.is_active)

    def test_create_account_negative_initial_balance_raises_error(self):
        dto = FinancialAccountCreateDTO(
            name="Caja Negativa",
            account_type=FinancialAccount.AccountType.CASH,
            initial_balance=Decimal("-100.00"),
        )
        with self.assertRaises(InvalidFinancialAmountException):
            FinancialAccountService.create_account(dto)

    def test_create_duplicate_account_name_raises_error(self):
        dto = FinancialAccountCreateDTO(
            name="Davivienda",
            account_type=FinancialAccount.AccountType.BANK,
            initial_balance=Decimal("1000.00"),
        )
        FinancialAccountService.create_account(dto)

        with self.assertRaises(FinancialAccountAlreadyExistsException):
            FinancialAccountService.create_account(dto)

    def test_update_account_service(self):
        dto = FinancialAccountCreateDTO(
            name="Cuenta Test",
            account_type=FinancialAccount.AccountType.BANK,
            initial_balance=Decimal("1000.00"),
        )
        account = FinancialAccountService.create_account(dto)

        update_dto = FinancialAccountUpdateDTO(
            name="Cuenta Test Modificada",
            bank_name="Banco de Bogotá",
        )
        updated = FinancialAccountService.update_account(account.pk, update_dto)
        self.assertEqual(updated.name, "Cuenta Test Modificada")
        self.assertEqual(updated.bank_name, "Banco de Bogotá")

    def test_update_duplicate_name_raises_error(self):
        acc1 = FinancialAccountService.create_account(
            FinancialAccountCreateDTO(
                name="Cuenta 1",
                account_type=FinancialAccount.AccountType.BANK,
                initial_balance=Decimal("1000.00"),
            )
        )
        acc2 = FinancialAccountService.create_account(
            FinancialAccountCreateDTO(
                name="Cuenta 2",
                account_type=FinancialAccount.AccountType.BANK,
                initial_balance=Decimal("1000.00"),
            )
        )
        with self.assertRaises(FinancialAccountAlreadyExistsException):
            FinancialAccountService.update_account(
                acc2.pk, FinancialAccountUpdateDTO(name="Cuenta 1")
            )

    def test_deactivate_account_soft_delete(self):
        dto = FinancialAccountCreateDTO(
            name="Caja Menor",
            account_type=FinancialAccount.AccountType.CASH,
            initial_balance=Decimal("500.00"),
        )
        account = FinancialAccountService.create_account(dto)
        FinancialAccountService.deactivate_account(account.pk)

        account.refresh_from_db()
        self.assertFalse(account.is_active)
        self.assertIsNotNone(account.deleted_at)

    def test_deactivate_non_existent_account_raises_error(self):
        with self.assertRaises(FinancialAccountNotFoundException):
            FinancialAccountService.deactivate_account(999999)

    def test_account_endpoints_crud(self):
        # 1. Crear via API
        payload = {
            "name": "Nequi Empresarial",
            "account_type": "DIGITAL_WALLET",
            "account_number": "3001234567",
            "bank_name": "Nequi",
            "initial_balance": "250000.00",
        }
        url = reverse("financial-accounts-list")
        res = self.client.post(url, data=payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        account_id = res.data["data"]["id_financial_account"]

        # 2. Listar
        res_list = self.client.get(url)
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        accounts_data = res_list.data.get("data", res_list.data.get("results", []))
        self.assertTrue(len(accounts_data) >= 1)

        # 3. Detalle
        detail_url = reverse("financial-accounts-detail", kwargs={"pk": account_id})
        res_detail = self.client.get(detail_url)
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(res_detail.data["data"]["name"], "Nequi Empresarial")

        # 4. Actualizar
        res_update = self.client.put(
            detail_url, data={"name": "Nequi Oficial"}, format="json"
        )
        self.assertEqual(res_update.status_code, status.HTTP_200_OK)
        self.assertEqual(res_update.data["data"]["name"], "Nequi Oficial")

        # 5. Desactivar
        res_delete = self.client.delete(detail_url)
        self.assertEqual(res_delete.status_code, status.HTTP_200_OK)

        # 6. Listar sin include_deleted no debe retornar la cuenta desactivada
        res_list_active = self.client.get(url)
        data_active = res_list_active.data.get("data", {})
        results_active = (
            data_active.get("results", []) if isinstance(data_active, dict) else data_active
        )
        active_ids = [a["id_financial_account"] for a in results_active]
        self.assertNotIn(account_id, active_ids)

        # 7. Listar con include_deleted=true sí la debe incluir
        res_list_all = self.client.get(f"{url}?include_deleted=true")
        data_all = res_list_all.data.get("data", {})
        results_all = (
            data_all.get("results", []) if isinstance(data_all, dict) else data_all
        )
        all_ids = [a["id_financial_account"] for a in results_all]
        self.assertIn(account_id, all_ids)

        # 8. Restaurar via API
        restore_url = reverse("financial-accounts-restore", kwargs={"pk": account_id})
        res_restore = self.client.post(restore_url)
        self.assertEqual(res_restore.status_code, status.HTTP_200_OK)
        self.assertTrue(res_restore.data["data"]["is_active"])

    def test_restore_account_service(self):
        dto = FinancialAccountCreateDTO(
            name="Caja Chica Sucursal",
            account_type=FinancialAccount.AccountType.CASH,
            initial_balance=Decimal("200000.00"),
        )
        account = FinancialAccountService.create_account(dto)
        FinancialAccountService.deactivate_account(account.pk)

        account.refresh_from_db()
        self.assertFalse(account.is_active)

        restored = FinancialAccountService.restore_account(account.pk)
        self.assertTrue(restored.is_active)
        self.assertIsNone(restored.deleted_at)

    def test_restore_account_duplicate_name_conflict(self):
        # 1. Crear y desactivar cuenta "Bancolombia Principal"
        acc1 = FinancialAccountService.create_account(
            FinancialAccountCreateDTO(
                name="Bancolombia Principal",
                account_type=FinancialAccount.AccountType.BANK,
                initial_balance=Decimal("1000.00"),
            )
        )
        FinancialAccountService.deactivate_account(acc1.pk)

        # 2. Crear una nueva cuenta activa con el mismo nombre
        FinancialAccountService.create_account(
            FinancialAccountCreateDTO(
                name="Bancolombia Principal",
                account_type=FinancialAccount.AccountType.BANK,
                initial_balance=Decimal("2000.00"),
            )
        )

        # 3. Intentar restaurar la primera debe lanzar conflicto de nombre
        with self.assertRaises(FinancialAccountAlreadyExistsException):
            FinancialAccountService.restore_account(acc1.pk)

    def test_account_unauthorized_access(self):
        unauth_client = APIClient()
        url = reverse("financial-accounts-list")
        res = unauth_client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
