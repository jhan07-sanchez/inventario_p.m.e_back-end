from datetime import date
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.cash.models.cash_register import CashRegister
from apps.cash.models.cash_session import CashSession
from apps.cash.models.payment import Payment
from apps.core.enums import PaymentMethod
from apps.customers.models.customer import Customer
from apps.finance.dto.financial_dto import (
    FinancialAccountCreateDTO,
    FinancialMovementCreateDTO,
    FinancialTransferCreateDTO,
)
from apps.finance.models.financial_account import FinancialAccount
from apps.finance.models.financial_movement import FinancialMovement
from apps.finance.selectors.finance_dashboard_selector import FinanceDashboardSelector
from apps.finance.services.financial_account_service import FinancialAccountService
from apps.finance.services.financial_movement_service import FinancialMovementService
from apps.finance.services.financial_transfer_service import FinancialTransferService
from apps.invoices.models.invoice import Invoice
from apps.invoices.models.invoice_template import InvoiceTemplate
from apps.purchases.models.purchase import Purchase
from apps.sales.models.sale import Sale
from apps.suppliers.models.supplier import Supplier
from apps.users.models import Role, User, UserRole


class FinanceDashboardTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="analista_financiero",
            password="Password123!",
            email="analista@example.com",
            document_number="80005001",
        )
        self.role = Role.objects.create(
            role_name="analista_role",
            permissions={
                "finance.view": True,
                "finance.create": True,
                "finance.transfer": True,
            },
        )
        UserRole.objects.create(user=self.user, role=self.role)
        self.client.force_authenticate(user=self.user)

        # 1. Crear cuentas financieras (Banco y Caja)
        self.bank_account = FinancialAccountService.create_account(
            FinancialAccountCreateDTO(
                name="Bancolombia Tesorería",
                account_type=FinancialAccount.AccountType.BANK,
                initial_balance=Decimal("10000000.00"),
            )
        )
        self.cash_account = FinancialAccountService.create_account(
            FinancialAccountCreateDTO(
                name="Caja Fuerte Oficina",
                account_type=FinancialAccount.AccountType.CASH,
                initial_balance=Decimal("2000000.00"),
            )
        )

        # 2. Registrar movimientos operativos
        today = date.today()
        # Ingreso operativo real de 1,500,000
        FinancialMovementService.record_movement(
            FinancialMovementCreateDTO(
                account_id=self.bank_account.pk,
                movement_type=FinancialMovement.MovementType.INFLOW,
                amount=Decimal("1500000.00"),
                movement_date=today,
                description="Ingreso por servicios",
            ),
            user=self.user,
        )
        # Egreso operativo real de 500,000
        FinancialMovementService.record_movement(
            FinancialMovementCreateDTO(
                account_id=self.bank_account.pk,
                movement_type=FinancialMovement.MovementType.OUTFLOW,
                amount=Decimal("500000.00"),
                movement_date=today,
                description="Pago nómina de apoyo",
            ),
            user=self.user,
        )

        # 3. Realizar transferencia interna entre cuentas de 1,000,000
        # (NO DEBE incrementar ni income ni expense)
        FinancialTransferService.execute_transfer(
            FinancialTransferCreateDTO(
                source_account_id=self.bank_account.pk,
                destination_account_id=self.cash_account.pk,
                amount=Decimal("1000000.00"),
                transfer_date=today,
                reference="TRF-009",
            ),
            user=self.user,
        )

        # 4. Crear caja registradora abierta de punto de venta (efectivo en gavetas)
        self.register = CashRegister.objects.create(name="Caja POS 1")
        CashSession.objects.create(
            cash_register=self.register,
            user=self.user,
            opening_balance=Decimal("100000.00"),
            expected_balance=Decimal("350000.00"),
            status=CashSession.SessionStatus.OPEN,
        )

        # 5. Crear una compra pendiente (cuenta por pagar)
        self.supplier = Supplier.objects.create(
            document_number="900999888",
            business_name="Proveedor Mayorista",
        )
        Purchase.objects.create(
            supplier=self.supplier,
            status=Purchase.Status.PENDING,
            total=Decimal("800000.00"),
        )

        # 6. Crear una factura de venta emitida (cuenta por cobrar)
        self.customer = Customer.objects.create(
            document_number="12345678",
            first_name="Carlos",
            last_name="Gómez",
        )
        self.sale = Sale.objects.create(
            sale_number="VEN-0001",
            customer=self.customer,
            user=self.user,
            total=Decimal("600000.00"),
            status=Sale.SaleStatus.PENDING,
        )
        self.template = InvoiceTemplate.objects.create(
            name="Plantilla Estándar",
            document_type=InvoiceTemplate.DocumentType.SALE_INVOICE,
            header_content="Encabezado",
            footer_content="Pie",
        )
        Invoice.objects.create(
            invoice_number="FAC-0001",
            document_type=Invoice.DocumentType.SALE_INVOICE,
            status=Invoice.Status.ISSUED,
            template=self.template,
            sale=self.sale,
            total=Decimal("600000.00"),
        )

    def test_dashboard_metrics_calculation(self):
        metrics = FinanceDashboardSelector.get_dashboard_metrics()

        # Liquidez
        liquidity = metrics["liquidity"]
        # Cuentas bancarias: 10,000,000 + 1,500,000 - 500,000 - 1,000,000 = 10,000,000
        self.assertEqual(Decimal(liquidity["bank_balances"]), Decimal("10000000.00"))
        # Caja fuerte: 2,000,000 + 1,000,000 = 3,000,000; más gavetas POS: 350,000 = 3,350,000
        self.assertEqual(Decimal(liquidity["cash_in_drawers"]), Decimal("350000.00"))
        self.assertEqual(Decimal(liquidity["total_cash"]), Decimal("3350000.00"))
        # Total disponible global = 10,000,000 + 3,350,000 = 13,350,000
        self.assertEqual(Decimal(liquidity["total_available_money"]), Decimal("13350000.00"))

        # Flujo de caja: las transferencias internas NO deben figurar en ingresos o egresos
        cash_flow = metrics["cash_flow"]
        self.assertEqual(Decimal(cash_flow["period_income"]), Decimal("1500000.00"))
        self.assertEqual(Decimal(cash_flow["period_expense"]), Decimal("500000.00"))
        self.assertEqual(Decimal(cash_flow["net_cash_flow"]), Decimal("1000000.00"))

        # Obligaciones
        obligations = metrics["obligations"]
        self.assertEqual(Decimal(obligations["accounts_payable"]), Decimal("800000.00"))
        self.assertEqual(Decimal(obligations["accounts_receivable"]), Decimal("600000.00"))

    def test_dashboard_endpoint_api(self):
        url = reverse("finance-dashboard")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("liquidity", res.data["data"])
        self.assertIn("cash_flow", res.data["data"])
        self.assertIn("obligations", res.data["data"])
        self.assertIn("accounts", res.data["data"])

