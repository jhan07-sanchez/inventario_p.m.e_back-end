from decimal import Decimal

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.cash.dto.cash_movement_dto import CashMovementCreateDto
from apps.cash.dto.cash_session_dto import CashSessionCloseDto, CashSessionOpenDto
from apps.cash.models.cash_movement import CashMovement
from apps.cash.models.cash_register import CashRegister
from apps.cash.models.cash_session import CashSession
from apps.cash.models.payment import Payment
from apps.cash.selectors.cash_session_selector import CashSessionSelector
from apps.cash.services.cash_movement_service import CashMovementService
from apps.cash.services.cash_session_service import CashSessionService
from apps.categories.models.category import Category
from apps.core.enums import PaymentMethod, PaymentStatus
from apps.core.exceptions.custom_exceptions import (
    BusinessException,
    CashSessionClosedException,
    InsufficientCashException,
)
from apps.products.models import Product
from apps.purchases.dto.purchase_dto import (
    PurchaseCreateDTO,
    PurchaseDetailCreateDTO,
    PurchasePayDTO,
)
from apps.purchases.models.purchase import Purchase
from apps.purchases.services.purchase_payment_service import PurchasePaymentService
from apps.purchases.services.purchase_service import PurchaseService
from apps.suppliers.models.supplier import Supplier
from apps.users.models import Role, User, UserRole


class CashFinancialAuditTests(TestCase):
    """
    Pruebas integrales del fortalecimiento del sistema de caja, arqueo,
    reconciliación matemática, carry-over y pagos de compras a proveedores.
    """

    def setUp(self):
        cache.clear()
        self.client = APIClient()

        # Usuario cajero / compras
        self.user = User.objects.create_user(
            username="cajero_financiero",
            password="Password123!",
            email="financiero@example.com",
            document_number="50000001",
        )
        self.role = Role.objects.create(
            role_name="financiero_role",
            permissions={
                "cash.view": True,
                "cash.open": True,
                "cash.close": True,
                "cash.movement": True,
                "purchases.view": True,
                "purchases.create": True,
                "purchases.update": True,
            },
        )
        UserRole.objects.create(user=self.user, role=self.role)

        # Caja registradora
        self.register = CashRegister.objects.create(
            name="Caja Principal Auditoría", description="Caja para pruebas"
        )

        # Proveedor y Producto para compras
        self.supplier = Supplier.objects.create(
            document_number="900123456",
            business_name="Distribuidora Mayorista S.A.S.",
            phone="3001234567",
        )
        self.category = Category.objects.create(name="Insumos")
        self.product = Product.objects.create(
            code="INS-01",
            name="Insumo A",
            category=self.category,
            purchase_price=Decimal("500.00"),
            sale_price=Decimal("1000.00"),
        )

    def test_recalculation_on_close_corrects_expected_balance(self):
        """
        Verifica que al cerrar la sesión, el sistema recalcule matemáticamente
        el saldo esperado en base a la suma real de movimientos de efectivo,
        corrigiendo cualquier desvío en el acumulador expected_balance.
        """
        # Abrir sesión con $1,000.00
        session = CashSessionService.open_session(
            CashSessionOpenDto(
                cash_register_id=self.register.pk,
                opening_balance=Decimal("1000.00"),
            ),
            self.user,
        )

        # Movimiento IN de $200.00 (Efectivo)
        CashMovementService.create_movement(
            CashMovementCreateDto(
                cash_session_id=session.pk,
                amount=Decimal("200.00"),
                movement_type=CashMovement.MovementType.IN,
                is_cash=True,
            )
        )

        # Movimiento OUT de $150.00 (Efectivo)
        CashMovementService.create_movement(
            CashMovementCreateDto(
                cash_session_id=session.pk,
                amount=Decimal("150.00"),
                movement_type=CashMovement.MovementType.OUT,
                is_cash=True,
            )
        )

        # Movimiento IN electrónico de $500.00 (no afecta efectivo)
        CashMovementService.create_movement(
            CashMovementCreateDto(
                cash_session_id=session.pk,
                amount=Decimal("500.00"),
                movement_type=CashMovement.MovementType.IN,
                is_cash=False,
            )
        )

        # Simular una alteración/deriva artificial en expected_balance
        CashSession.objects.filter(pk=session.pk).update(
            expected_balance=Decimal("9999.00")
        )

        # Cierre: contado = $1,050.00 (esperado real: 1000 + 200 - 150 = 1050)
        close_dto = CashSessionCloseDto(
            counted_balance=Decimal("1050.00"),
            notes="Cierre auditado",
        )
        closed_session = CashSessionService.close_session(session, close_dto)

        # El expected_balance debe haberse corregido a 1050.00 y la diferencia debe ser 0.00
        self.assertEqual(closed_session.expected_balance, Decimal("1050.00"))
        self.assertEqual(closed_session.difference, Decimal("0.00"))
        self.assertEqual(closed_session.status, CashSession.SessionStatus.CLOSED)

    def test_denominations_stored_and_retrieved(self):
        """
        Verifica que el desglose de denominaciones (billetes y monedas) se guarde
        correctamente al cerrar la sesión y se entregue en serializers y auditoría.
        """
        session = CashSessionService.open_session(
            CashSessionOpenDto(
                cash_register_id=self.register.pk,
                opening_balance=Decimal("500.00"),
            ),
            self.user,
        )

        denominations_data = {
            "100000": 2,  # 200,000
            "50000": 4,   # 200,000
            "20000": 5,   # 100,000
        }  # Total = 500,000

        close_dto = CashSessionCloseDto(
            counted_balance=Decimal("500000.00"),
            notes="Arqueo con conteo físico",
            denominations=denominations_data,
        )
        closed = CashSessionService.close_session(session, close_dto)

        # Verificar notas y resumen de auditoría
        self.assertIn("DENOMINATIONS:", closed.notes)

        summary = CashSessionSelector.get_session_audit_summary(closed.pk)
        self.assertIsNotNone(summary["denominations"])
        self.assertEqual(summary["denominations"]["100000"], 2)
        self.assertEqual(summary["denominations"]["50000"], 4)

    def test_carry_over_last_closing_balance_endpoint(self):
        """
        Verifica el endpoint GET /api/v1/cash-sessions/last-closing-balance/
        para sugerir el saldo de arrastre (carry-over) en la apertura.
        """
        self.client.force_authenticate(user=self.user)

        # Sin sesiones previas -> 0.00
        url = reverse("cash-session-last-closing-balance")
        res1 = self.client.get(f"{url}?cash_register_id={self.register.pk}")
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertEqual(res1.data["data"]["last_closing_balance"], "0.00")

        # Abrir y cerrar sesión con $350.00
        session = CashSessionService.open_session(
            CashSessionOpenDto(
                cash_register_id=self.register.pk,
                opening_balance=Decimal("350.00"),
            ),
            self.user,
        )
        CashSessionService.close_session(
            session,
            CashSessionCloseDto(counted_balance=Decimal("350.00")),
        )

        # Consultar de nuevo
        res2 = self.client.get(f"{url}?cash_register_id={self.register.pk}")
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(res2.data["data"]["last_closing_balance"]), Decimal("350.00"))
        self.assertEqual(res2.data["data"]["session_id"], session.pk)

    def test_purchase_cash_payment_integration(self):
        """
        Verifica el flujo completo de pago de una compra a proveedor en EFECTIVO:
        1. Crea orden de compra por $1,500.00 y la confirma (PENDING).
        2. Cajero tiene caja abierta con $2,000.00.
        3. Se paga la compra en efectivo:
           - Se genera un Payment COMPLETED con referencia a la compra.
           - Se genera un CashMovement OUT (egreso de efectivo en la sesión).
           - El expected_balance de la sesión disminuye de $2,000.00 a $500.00.
           - El estado de la compra refleja que está liquidada.
        """
        # Crear y confirmar compra
        create_dto = PurchaseCreateDTO(
            supplier_id=self.supplier.pk,
            issue_date=None,
            notes="Compra de insumos urgentes",
            details=[
                PurchaseDetailCreateDTO(
                    product_id=self.product.pk,
                    quantity=Decimal("3.00"),
                    unit_price=Decimal("500.00"),
                )
            ],
        )
        purchase = PurchaseService.create_purchase(create_dto)
        purchase = PurchaseService.confirm_purchase(purchase)
        self.assertEqual(purchase.total, Decimal("1500.00"))

        # Abrir caja con $2,000.00
        session = CashSessionService.open_session(
            CashSessionOpenDto(
                cash_register_id=self.register.pk,
                opening_balance=Decimal("2000.00"),
            ),
            self.user,
        )

        # Realizar pago en efectivo de la compra
        pay_dto = PurchasePayDTO(
            amount=Decimal("1500.00"),
            payment_method=PaymentMethod.CASH,
            notes="Pago contado en caja",
        )
        result = PurchasePaymentService.pay_purchase(
            purchase_id=purchase.pk,
            dto=pay_dto,
            user=self.user,
        )

        self.assertEqual(result["purchase_id"], purchase.pk)
        self.assertEqual(Decimal(result["amount_paid"]), Decimal("1500.00"))
        self.assertTrue(result["is_fully_paid"])
        self.assertEqual(Decimal(result["pending_balance"]), Decimal("0.00"))

        # Verificar Payment en BD
        payment = Payment.objects.get(pk=result["payment_id"])
        self.assertEqual(payment.amount, Decimal("1500.00"))
        self.assertEqual(payment.payment_method, PaymentMethod.CASH)
        self.assertEqual(payment.status, PaymentStatus.COMPLETED)
        self.assertIn(f"COMPRA #{purchase.pk}", payment.reference)

        # Verificar CashMovement en BD
        movement = CashMovement.objects.get(payment=payment)
        self.assertEqual(movement.cash_session, session)
        self.assertEqual(movement.movement_type, CashMovement.MovementType.OUT)
        self.assertTrue(movement.is_cash)
        self.assertEqual(movement.amount, Decimal("1500.00"))

        # Verificar decremento del saldo en sesión
        session.refresh_from_db()
        self.assertEqual(session.expected_balance, Decimal("500.00"))

    def test_purchase_payment_insufficient_cash_rejected(self):
        """
        Verifica que si se intenta pagar una compra en efectivo con un monto
        superior al saldo en caja, se rechace con InsufficientCashException.
        """
        create_dto = PurchaseCreateDTO(
            supplier_id=self.supplier.pk,
            issue_date=None,
            notes="Compra costosa",
            details=[
                PurchaseDetailCreateDTO(
                    product_id=self.product.pk,
                    quantity=Decimal("10.00"),
                    unit_price=Decimal("500.00"),
                )
            ],
        )
        purchase = PurchaseService.create_purchase(create_dto)
        purchase = PurchaseService.confirm_purchase(purchase)
        self.assertEqual(purchase.total, Decimal("5000.00"))

        # Abrir caja con solo $1,000.00
        CashSessionService.open_session(
            CashSessionOpenDto(
                cash_register_id=self.register.pk,
                opening_balance=Decimal("1000.00"),
            ),
            self.user,
        )

        pay_dto = PurchasePayDTO(
            amount=Decimal("5000.00"),
            payment_method=PaymentMethod.CASH,
        )
        with self.assertRaises((InsufficientCashException, BusinessException)) as ctx:
            PurchasePaymentService.pay_purchase(
                purchase_id=purchase.pk,
                dto=pay_dto,
                user=self.user,
            )
        self.assertIn("supera el efectivo disponible en caja", str(ctx.exception))

    def test_purchase_electronic_payment_does_not_affect_physical_cash(self):
        """
        Verifica que pagar una compra vía TRANSFERENCIA bancaria genera el
        pago correspondiente pero NO disminuye el saldo en gaveta física.
        """
        create_dto = PurchaseCreateDTO(
            supplier_id=self.supplier.pk,
            issue_date=None,
            notes="Compra con transferencia",
            details=[
                PurchaseDetailCreateDTO(
                    product_id=self.product.pk,
                    quantity=Decimal("2.00"),
                    unit_price=Decimal("500.00"),
                )
            ],
        )
        purchase = PurchaseService.create_purchase(create_dto)
        purchase = PurchaseService.confirm_purchase(purchase)

        session = CashSessionService.open_session(
            CashSessionOpenDto(
                cash_register_id=self.register.pk,
                opening_balance=Decimal("1000.00"),
            ),
            self.user,
        )

        pay_dto = PurchasePayDTO(
            amount=Decimal("1000.00"),
            payment_method=PaymentMethod.TRANSFER,
            reference="TR-998877",
        )
        result = PurchasePaymentService.pay_purchase(
            purchase_id=purchase.pk,
            dto=pay_dto,
            user=self.user,
        )

        self.assertEqual(result["payment_method"], PaymentMethod.TRANSFER)

        # Saldo en efectivo sigue intacto
        session.refresh_from_db()
        self.assertEqual(session.expected_balance, Decimal("1000.00"))

    def test_purchase_payment_closed_cash_session_rejected(self):
        """
        Verifica que si no hay sesion de caja abierta y se intenta pagar en efectivo,
        se lance CashSessionClosedException y la API retorne 400 con codigo CASH_SESSION_CLOSED.
        """
        create_dto = PurchaseCreateDTO(
            supplier_id=self.supplier.pk,
            issue_date=None,
            notes="Compra sin caja abierta",
            details=[
                PurchaseDetailCreateDTO(
                    product_id=self.product.pk,
                    quantity=Decimal("1.00"),
                    unit_price=Decimal("100.00"),
                )
            ],
        )
        purchase = PurchaseService.create_purchase(create_dto)
        purchase = PurchaseService.confirm_purchase(purchase)

        # No abrimos caja para el usuario
        pay_dto = PurchasePayDTO(
            amount=Decimal("100.00"),
            payment_method=PaymentMethod.CASH,
        )
        with self.assertRaises(CashSessionClosedException):
            PurchasePaymentService.pay_purchase(
                purchase_id=purchase.pk,
                dto=pay_dto,
                user=self.user,
            )

        # Probar a traves del endpoint de API
        self.client.force_authenticate(user=self.user)
        url = reverse("purchases-pay", kwargs={"pk": purchase.pk})
        response = self.client.post(
            url,
            {
                "amount": "100.00",
                "payment_method": PaymentMethod.CASH,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "CASH_SESSION_CLOSED")
        self.assertIn("caja abierta", response.data["message"])

    def test_financial_summary_endpoint(self):
        """
        Verifica el endpoint GET /api/v1/cash-sessions/financial-summary/.
        """
        self.client.force_authenticate(user=self.user)

        # Abrir sesión
        CashSessionService.open_session(
            CashSessionOpenDto(
                cash_register_id=self.register.pk,
                opening_balance=Decimal("750.00"),
            ),
            self.user,
        )

        url = reverse("cash-session-financial-summary")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertGreaterEqual(data["open_sessions_count"], 1)
        self.assertIn("total_cash_in_drawers", data)
        self.assertIn("today", data)
        self.assertIn("active_sessions", data)

    def test_purchase_payment_status_in_serializers(self):
        """
        Verifica que PurchaseRetrieveSerializer y PurchaseListSerializer
        calculen correctamente total_paid, pending_balance, is_fully_paid
        y payment_status en transiciones: UNPAID -> PARTIAL -> PAID.
        """
        create_dto = PurchaseCreateDTO(
            supplier_id=self.supplier.pk,
            issue_date=None,
            notes="Compra seguimiento pagos",
            details=[
                PurchaseDetailCreateDTO(
                    product_id=self.product.pk,
                    quantity=Decimal("2.00"),
                    unit_price=Decimal("500.00"),
                )
            ],
        )
        purchase = PurchaseService.create_purchase(create_dto)
        purchase = PurchaseService.confirm_purchase(purchase)
        self.assertEqual(purchase.total, Decimal("1000.00"))

        # 1. Estado inicial: UNPAID
        self.client.force_authenticate(user=self.user)
        url = reverse("purchases-detail", kwargs={"pk": purchase.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        d = resp.data["data"]
        self.assertEqual(Decimal(d["total_paid"]), Decimal("0.00"))
        self.assertEqual(Decimal(d["pending_balance"]), Decimal("1000.00"))
        self.assertFalse(d["is_fully_paid"])
        self.assertEqual(d["payment_status"], "UNPAID")

        # 2. Pago parcial: $400.00 -> PARTIAL
        pay_dto_1 = PurchasePayDTO(
            amount=Decimal("400.00"),
            payment_method=PaymentMethod.TRANSFER,
            reference="TR-ABONO-1",
        )
        PurchasePaymentService.pay_purchase(purchase.pk, pay_dto_1, self.user)

        resp = self.client.get(url)
        d = resp.data["data"]
        self.assertEqual(Decimal(d["total_paid"]), Decimal("400.00"))
        self.assertEqual(Decimal(d["pending_balance"]), Decimal("600.00"))
        self.assertFalse(d["is_fully_paid"])
        self.assertEqual(d["payment_status"], "PARTIAL")

        # 3. Pago restante: $600.00 -> PAID
        pay_dto_2 = PurchasePayDTO(
            amount=Decimal("600.00"),
            payment_method=PaymentMethod.TRANSFER,
            reference="TR-ABONO-2",
        )
        PurchasePaymentService.pay_purchase(purchase.pk, pay_dto_2, self.user)

        resp = self.client.get(url)
        d = resp.data["data"]
        self.assertEqual(Decimal(d["total_paid"]), Decimal("1000.00"))
        self.assertEqual(Decimal(d["pending_balance"]), Decimal("0.00"))
        self.assertTrue(d["is_fully_paid"])
        self.assertEqual(d["payment_status"], "PAID")
        self.assertEqual(len(d["payments_summary"]), 2)

        # 4. Verificar que la Factura de compra refleje el estado de pago
        invoice = purchase.invoices.filter(is_active=True).first()
        if invoice:
            inv_url = reverse("invoices-detail", kwargs={"pk": invoice.pk})
            inv_resp = self.client.get(inv_url)
            self.assertEqual(inv_resp.status_code, status.HTTP_200_OK)
            inv_data = inv_resp.data["data"]
            self.assertEqual(inv_data["payment_status"], "PAID")
            self.assertEqual(Decimal(inv_data["total_paid"]), Decimal("1000.00"))
            self.assertEqual(Decimal(inv_data["pending_balance"]), Decimal("0.00"))
