from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.company_info.models import CompanyInfo
from apps.finance.models.financial_account import FinancialAccount
from apps.finance.models.financial_category import FinancialCategory
from apps.finance.models.financial_movement import FinancialMovement
from apps.finance.selectors.finance_dashboard_selector import FinanceDashboardSelector
from apps.finance.selectors.financial_account_selector import FinancialAccountSelector
from apps.finance.selectors.financial_movement_selector import FinancialMovementSelector
from apps.finance.views.financial_account_viewset import FinancialAccountViewSet
from apps.finance.views.financial_movement_viewset import FinancialMovementViewSet
from apps.finance.views.finance_dashboard_view import FinanceDashboardView
from apps.users.models import CompanyMembership, Role, User


class FinanceTenantIsolationTests(TestCase):
    """
    Pruebas de aislamiento multi-tenant estricto para el módulo de Finanzas y Tesorería.
    Garantiza que la Empresa A y la Empresa B manejen sus saldos, cuentas y movimientos
    con estricta separación de datos (Zero Leakage).
    """

    def setUp(self):
        self.factory = APIRequestFactory()

        # Crear dos empresas
        self.company_a = CompanyInfo.objects.create(
            business_name="Empresa A SAS",
            trade_name="Empresa A",
            tax_id="NIT-AAA-01",
            is_active=True,
        )
        self.company_b = CompanyInfo.objects.create(
            business_name="Empresa B Ltda",
            trade_name="Empresa B",
            tax_id="NIT-BBB-02",
            is_active=True,
        )

        # Rol y usuarios
        self.role_admin = Role.objects.create(
            role_name="Admin Tesorería",
            role_description="Administrador de Finanzas",
        )
        self.user_a = User.objects.create_superuser(
            username="user_fin_a",
            email="fin_a@test.com",
            password="Password123!",
            document_number="DOC-FIN-A",
        )
        CompanyMembership.objects.create(
            user=self.user_a,
            company=self.company_a,
            role=self.role_admin,
            is_owner=True,
            is_active=True,
        )

        self.user_b = User.objects.create_superuser(
            username="user_fin_b",
            email="fin_b@test.com",
            password="Password123!",
            document_number="DOC-FIN-B",
        )
        CompanyMembership.objects.create(
            user=self.user_b,
            company=self.company_b,
            role=self.role_admin,
            is_owner=True,
            is_active=True,
        )

        # Cuentas financieras de Empresa A
        self.account_a1 = FinancialAccount.objects.create(
            name="Caja Principal Empresa A",
            account_type=FinancialAccount.AccountType.CASH,
            initial_balance=Decimal("100000.00"),
            current_balance=Decimal("150000.00"),
            company=self.company_a,
            is_active=True,
        )
        self.account_a2 = FinancialAccount.objects.create(
            name="Banco Empresa A",
            account_type=FinancialAccount.AccountType.BANK,
            initial_balance=Decimal("200000.00"),
            current_balance=Decimal("250000.00"),
            company=self.company_a,
            is_active=True,
        )

        # Categoría y movimiento sólo en Empresa A
        self.cat_a = FinancialCategory.objects.create(
            name="Ventas A",
            category_type=FinancialCategory.CategoryType.INFLOW,
            company=self.company_a,
            is_active=True,
        )
        self.mov_a = FinancialMovement.objects.create(
            account=self.account_a1,
            category=self.cat_a,
            movement_type=FinancialMovement.MovementType.INFLOW,
            amount=Decimal("50000.00"),
            movement_date="2026-11-09",
            description="Ingreso por ventas Empresa A",
            status=FinancialMovement.MovementStatus.COMPLETED,
            user=self.user_a,
            is_active=True,
        )

        # Cuentas financieras de Empresa B
        self.account_b = FinancialAccount.objects.create(
            name="Caja Única Empresa B",
            account_type=FinancialAccount.AccountType.CASH,
            initial_balance=Decimal("10000.00"),
            current_balance=Decimal("10000.00"),
            company=self.company_b,
            is_active=True,
        )

    def test_account_selector_isolation(self):
        """Verifica que el selector de cuentas filtre estrictamente por company_id."""
        accounts_a = FinancialAccountSelector.get_accounts(company_id=self.company_a.id_company)
        accounts_b = FinancialAccountSelector.get_accounts(company_id=self.company_b.id_company)

        self.assertEqual(accounts_a.count(), 2)
        self.assertEqual(accounts_b.count(), 1)
        self.assertEqual(accounts_b.first().name, "Caja Única Empresa B")

    def test_movement_selector_isolation(self):
        """Verifica que los movimientos se aíslen por empresa a través de la cuenta."""
        movs_a = FinancialMovementSelector.get_movements(company_id=self.company_a.id_company)
        movs_b = FinancialMovementSelector.get_movements(company_id=self.company_b.id_company)

        self.assertEqual(movs_a.count(), 1)
        self.assertEqual(movs_b.count(), 0)

    def test_dashboard_metrics_strict_isolation(self):
        """Verifica que el dashboard financiero no mezcle liquidez ni flujos de caja."""
        m_a = FinanceDashboardSelector.get_dashboard_metrics(company_id=self.company_a.id_company)
        m_b = FinanceDashboardSelector.get_dashboard_metrics(company_id=self.company_b.id_company)

        # Empresa A: Liquidez = 150000 + 250000 = 400000; Inflow = 50000
        self.assertEqual(Decimal(m_a["summary"]["total_liquid_balance"]), Decimal("400000.00"))
        self.assertEqual(Decimal(m_a["summary"]["total_inflow"]), Decimal("50000.00"))
        self.assertEqual(len(m_a["accounts"]), 2)

        # Empresa B: Liquidez = 10000; Inflow = 0.00
        self.assertEqual(Decimal(m_b["summary"]["total_liquid_balance"]), Decimal("10000.00"))
        self.assertEqual(Decimal(m_b["summary"]["total_inflow"]), Decimal("0.00"))
        self.assertEqual(len(m_b["accounts"]), 1)
        self.assertEqual(len(m_b["recent_movements"]), 0)

    def test_account_viewset_isolation(self):
        """Verifica que el endpoint GET /api/v1/finance/accounts/ filtre por company_id."""
        view = FinancialAccountViewSet.as_view({"get": "list"})

        # Request Empresa B
        request = self.factory.get("/api/v1/finance/accounts/")
        force_authenticate(request, user=self.user_b)
        request.company_id = self.company_b.id_company
        response = view(request)

        self.assertEqual(response.status_code, 200)
        results = response.data.get("data", {}).get("results", [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Caja Única Empresa B")
