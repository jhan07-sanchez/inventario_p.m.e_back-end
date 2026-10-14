from decimal import Decimal
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.categories.models.category import Category
from apps.cash.dto.cash_movement_dto import CashMovementCreateDto
from apps.cash.dto.cash_session_dto import CashSessionCloseDto, CashSessionOpenDto
from apps.cash.models.cash_movement import CashMovement
from apps.cash.models.cash_register import CashRegister
from apps.cash.models.cash_session import CashSession
from apps.cash.models.payment import Payment
from apps.cash.services.cash_movement_service import CashMovementService
from apps.cash.services.cash_session_service import CashSessionService
from apps.core.enums import PaymentMethod, PaymentStatus
from apps.inventory.models import Inventory
from apps.invoices.models import InvoiceTemplate
from apps.products.models import Product
from apps.sales.dto.sale_detail_dto import SaleDetailDto
from apps.sales.dto.sale_dto import SaleCreateDto
from apps.sales.models import Sale
from apps.sales.services.sale_service import SaleService
from apps.users.models import Role, User, UserRole


class CashSessionServiceTests(TestCase):
    """
    Pruebas unitarias de servicios de caja cubriendo los escenarios A al E.
    """

    def setUp(self):
        cache.clear()

        # Usuario cajero 1
        self.user1 = User.objects.create_user(
            username="cajero1",
            password="Password123!",
            email="cajero1@example.com",
            document_number="10000001",
        )
        self.role1 = Role.objects.create(
            role_name="cajero_role",
            permissions={
                "cash.view": True,
                "cash.open": True,
                "cash.close": True,
                "cash.movement": True,
            },
        )
        self.user_role1 = UserRole.objects.create(user=self.user1, role=self.role1)

        # Usuario cajero 2
        self.user2 = User.objects.create_user(
            username="cajero2",
            password="Password123!",
            email="cajero2@example.com",
            document_number="10000002",
        )
        self.user_role2 = UserRole.objects.create(user=self.user2, role=self.role1)

        # Cajas registradoras
        self.register1 = CashRegister.objects.create(
            name="Caja 1 - Principal", description="Caja del mostrador 1"
        )
        self.register2 = CashRegister.objects.create(
            name="Caja 2 - Secundaria", description="Caja del mostrador 2"
        )

    def test_scenario_a_open_session_success(self):
        """
        Escenario A: Apertura exitosa de sesión de caja.
        Verifica: status=OPEN, opening_balance, expected_balance inicializado,
        y asignación correcta de usuario y caja.
        """
        open_dto = CashSessionOpenDto(
            cash_register_id=self.register1.pk,
            opening_balance=Decimal("150.00"),
            notes="Apertura de turno matutino",
        )
        session = CashSessionService.open_session(open_dto, self.user1)

        self.assertIsNotNone(session.pk)
        self.assertEqual(session.status, CashSession.SessionStatus.OPEN)
        self.assertEqual(session.opening_balance, Decimal("150.00"))
        self.assertEqual(session.expected_balance, Decimal("150.00"))
        self.assertEqual(session.user, self.user1)
        self.assertEqual(session.cash_register, self.register1)
        self.assertIsNotNone(session.start_time)
        self.assertIsNone(session.end_time)
        self.assertIsNone(session.counted_balance)
        self.assertIsNone(session.difference)

    def test_scenario_b_prevent_double_open_same_user(self):
        """
        Escenario B: Prevención de doble apertura por el mismo usuario.
        Un cajero no puede tener dos sesiones abiertas en simultáneo.
        """
        # Abrir primera sesión
        open_dto1 = CashSessionOpenDto(
            cash_register_id=self.register1.pk,
            opening_balance=Decimal("100.00"),
        )
        CashSessionService.open_session(open_dto1, self.user1)

        # Intentar abrir segunda sesión en otra caja
        open_dto2 = CashSessionOpenDto(
            cash_register_id=self.register2.pk,
            opening_balance=Decimal("50.00"),
        )
        with self.assertRaises(ValidationError) as ctx:
            CashSessionService.open_session(open_dto2, self.user1)
        self.assertIn("El usuario ya tiene una sesión de caja abierta.", str(ctx.exception))

        # Validar apertura con monto negativo
        open_dto_negative = CashSessionOpenDto(
            cash_register_id=self.register2.pk,
            opening_balance=Decimal("-10.00"),
        )
        with self.assertRaises(ValidationError) as ctx:
            CashSessionService.open_session(open_dto_negative, self.user2)
        self.assertIn("El efectivo inicial no puede ser negativo.", str(ctx.exception))

    def test_scenario_c_prevent_open_register_already_in_use(self):
        """
        Escenario C: Bloqueo de caja ya abierta.
        Dos usuarios no pueden abrir la misma caja física a la vez.
        """
        open_dto1 = CashSessionOpenDto(
            cash_register_id=self.register1.pk,
            opening_balance=Decimal("100.00"),
        )
        CashSessionService.open_session(open_dto1, self.user1)

        open_dto2 = CashSessionOpenDto(
            cash_register_id=self.register1.pk,
            opening_balance=Decimal("100.00"),
        )
        with self.assertRaises(ValidationError) as ctx:
            CashSessionService.open_session(open_dto2, self.user2)
        self.assertIn("La caja seleccionada ya está abierta por otro usuario.", str(ctx.exception))

    def test_scenario_d_close_session_and_difference_calculation(self):
        """
        Escenario D: Cierre de sesión y cálculo de diferencia (cuadre de caja).
        Verifica: status=CLOSED, counted_balance, difference calculada (sobrante y faltante).
        """
        open_dto = CashSessionOpenDto(
            cash_register_id=self.register1.pk,
            opening_balance=Decimal("100.00"),
        )
        session = CashSessionService.open_session(open_dto, self.user1)

        # Cierre con sobrante: contado 120, esperado 100 -> diferencia +20
        close_dto_surplus = CashSessionCloseDto(
            counted_balance=Decimal("120.00"),
            notes="Cierre con sobrante de 20",
        )
        closed_session = CashSessionService.close_session(session, close_dto_surplus)

        self.assertEqual(closed_session.status, CashSession.SessionStatus.CLOSED)
        self.assertEqual(closed_session.counted_balance, Decimal("120.00"))
        self.assertEqual(closed_session.difference, Decimal("20.00"))
        self.assertIsNotNone(closed_session.end_time)

        # Intentar cerrar nuevamente debe fallar
        with self.assertRaises(ValidationError) as ctx:
            CashSessionService.close_session(closed_session, close_dto_surplus)
        self.assertIn("La sesión ya se encuentra cerrada.", str(ctx.exception))

        # Probar faltante en una segunda sesión
        session2 = CashSessionService.open_session(
            CashSessionOpenDto(
                cash_register_id=self.register2.pk,
                opening_balance=Decimal("200.00"),
            ),
            self.user2,
        )
        close_dto_deficit = CashSessionCloseDto(
            counted_balance=Decimal("180.00"),
            notes="Cierre con faltante de 20",
        )
        closed_session2 = CashSessionService.close_session(session2, close_dto_deficit)
        self.assertEqual(closed_session2.difference, Decimal("-20.00"))

        # Validar monto contado negativo
        session3 = CashSessionService.open_session(
            CashSessionOpenDto(
                cash_register_id=self.register1.pk,
                opening_balance=Decimal("50.00"),
            ),
            self.user1,
        )
        with self.assertRaises(ValidationError) as ctx:
            CashSessionService.close_session(
                session3,
                CashSessionCloseDto(counted_balance=Decimal("-5.00")),
            )
        self.assertIn("El efectivo contado no puede ser negativo.", str(ctx.exception))

    def test_scenario_e_manual_cash_movements_in_out_and_limits(self):
        """
        Escenario E: Movimientos manuales de caja (IN / OUT) y validación de saldos.
        Verifica:
          - IN en efectivo incrementa expected_balance.
          - OUT en efectivo disminuye expected_balance.
          - OUT mayor al disponible en gaveta es rechazado.
          - Monto <= 0 es rechazado.
          - Movimiento sobre sesión cerrada es rechazado.
          - Movimiento no-efectivo no altera el saldo en gaveta.
        """
        session = CashSessionService.open_session(
            CashSessionOpenDto(
                cash_register_id=self.register1.pk,
                opening_balance=Decimal("100.00"),
            ),
            self.user1,
        )

        # 1. Movimiento IN manual en efectivo: +$50.00
        mov_in = CashMovementService.create_movement(
            CashMovementCreateDto(
                cash_session_id=session.pk,
                amount=Decimal("50.00"),
                movement_type=CashMovement.MovementType.IN,
                is_cash=True,
                description="Ingreso manual para cambio",
            )
        )
        session.refresh_from_db()
        self.assertEqual(mov_in.movement_type, CashMovement.MovementType.IN)
        self.assertTrue(mov_in.is_cash)
        self.assertEqual(session.expected_balance, Decimal("150.00"))

        # 2. Movimiento OUT manual en efectivo: -$30.00
        mov_out = CashMovementService.create_movement(
            CashMovementCreateDto(
                cash_session_id=session.pk,
                amount=Decimal("30.00"),
                movement_type=CashMovement.MovementType.OUT,
                is_cash=True,
                description="Retiro para compra de insumos",
            )
        )
        session.refresh_from_db()
        self.assertEqual(mov_out.movement_type, CashMovement.MovementType.OUT)
        self.assertEqual(session.expected_balance, Decimal("120.00"))

        # 3. Movimiento OUT que supera el saldo disponible ($200 > $120)
        with self.assertRaises(ValidationError) as ctx:
            CashMovementService.create_movement(
                CashMovementCreateDto(
                    cash_session_id=session.pk,
                    amount=Decimal("200.00"),
                    movement_type=CashMovement.MovementType.OUT,
                    is_cash=True,
                    description="Retiro excesivo",
                )
            )
        self.assertIn("supera el efectivo disponible en caja", str(ctx.exception))

        # 4. Movimiento con monto cero o negativo
        with self.assertRaises(ValidationError) as ctx:
            CashMovementService.create_movement(
                CashMovementCreateDto(
                    cash_session_id=session.pk,
                    amount=Decimal("0.00"),
                    movement_type=CashMovement.MovementType.IN,
                )
            )
        self.assertIn("El monto del movimiento debe ser mayor a cero.", str(ctx.exception))

        # 5. Movimiento no-efectivo (is_cash=False): no altera expected_balance en gaveta
        mov_electronic = CashMovementService.create_movement(
            CashMovementCreateDto(
                cash_session_id=session.pk,
                amount=Decimal("80.00"),
                movement_type=CashMovement.MovementType.IN,
                is_cash=False,
                description="Recepción electrónica externa",
            )
        )
        session.refresh_from_db()
        self.assertFalse(mov_electronic.is_cash)
        self.assertEqual(session.expected_balance, Decimal("120.00"))

        # 6. Movimiento en sesión cerrada
        CashSessionService.close_session(
            session,
            CashSessionCloseDto(counted_balance=Decimal("120.00")),
        )
        with self.assertRaises(ValidationError) as ctx:
            CashMovementService.create_movement(
                CashMovementCreateDto(
                    cash_session_id=session.pk,
                    amount=Decimal("10.00"),
                    movement_type=CashMovement.MovementType.IN,
                )
            )
        self.assertIn("No se pueden registrar movimientos en una sesión cerrada.", str(ctx.exception))


class CashSaleFinancialFlowTests(TestCase):
    """
    Pruebas de integración del flujo financiero entre Ventas y Caja:
    Escenarios F, G y H.
    """

    def setUp(self):
        cache.clear()

        # Usuario cajero
        self.user = User.objects.create_user(
            username="vendedor1",
            password="Password123!",
            email="vendedor@example.com",
            document_number="20000001",
        )
        self.role = Role.objects.create(
            role_name="vendedor_role",
            permissions={
                "cash.view": True,
                "cash.open": True,
                "cash.close": True,
                "cash.movement": True,
                "sales.view": True,
                "sales.create": True,
                "sales.complete": True,
                "sales.cancel": True,
            },
        )
        UserRole.objects.create(user=self.user, role=self.role)

        # Plantilla obligatoria para emisión de facturas/tickets
        self.template = InvoiceTemplate.objects.create(
            name="Plantilla Estándar de Venta",
            document_type=InvoiceTemplate.DocumentType.SALE_INVOICE,
            is_default=True,
            is_active=True,
        )

        # Catálogo e Inventario
        self.category = Category.objects.create(name="Abarrotes", description="Productos generales")
        self.product = Product.objects.create(
            code="P001",
            name="Arroz Premium 1kg",
            category=self.category,
            purchase_price=Decimal("2000.00"),
            sale_price=Decimal("3500.00"),
        )
        self.inventory = Inventory.objects.create(
            product=self.product,
            current_stock=Decimal("100.00"),
            minimum_stock=Decimal("5.00"),
        )

        # Caja y sesión abierta con saldo inicial de $10,000.00
        self.register = CashRegister.objects.create(name="Caja POS 1")
        self.session = CashSessionService.open_session(
            CashSessionOpenDto(
                cash_register_id=self.register.pk,
                opening_balance=Decimal("10000.00"),
            ),
            self.user,
        )

    def test_scenario_f_cash_and_card_sale_integration(self):
        """
        Escenario F: Integración venta de contado (CASH y CARD).
        - Venta CASH: Genera Payment COMPLETED, CashMovement con is_cash=True,
          incrementa expected_balance, calcula change_amount correctamente.
        - Venta CARD: Genera Payment COMPLETED, CashMovement con is_cash=False,
          NO incrementa expected_balance (no es gaveta de efectivo).
        """
        # 1. Venta POS en EFECTIVO: Total = 2 * 3500 = $7,000. Recibido = $10,000 -> Cambio = $3,000
        cash_sale_dto = SaleCreateDto(
            details=(
                SaleDetailDto(
                    product_id=self.product.pk,
                    quantity=Decimal("2.00"),
                    unit_price=Decimal("3500.00"),
                ),
            ),
            payment_method=PaymentMethod.CASH,
            sale_type=Sale.SaleType.POS,
            amount_received=Decimal("10000.00"),
            generate_invoice=False,
        )

        cash_sale = SaleService.quick_sale(cash_sale_dto, self.user)

        self.assertEqual(cash_sale.status, Sale.SaleStatus.COMPLETED)
        self.assertEqual(cash_sale.total, Decimal("7000.00"))
        self.assertEqual(cash_sale.amount_received, Decimal("10000.00"))
        self.assertEqual(cash_sale.change_amount, Decimal("3000.00"))

        # Verificar Payment generado
        payment = Payment.objects.filter(sale=cash_sale).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.status, PaymentStatus.COMPLETED)
        self.assertEqual(payment.amount, Decimal("7000.00"))
        self.assertEqual(payment.payment_method, PaymentMethod.CASH)

        # Verificar CashMovement generado
        movement = CashMovement.objects.filter(payment=payment).first()
        self.assertIsNotNone(movement)
        self.assertEqual(movement.cash_session, self.session)
        self.assertEqual(movement.movement_type, CashMovement.MovementType.IN)
        self.assertTrue(movement.is_cash)
        self.assertEqual(movement.amount, Decimal("7000.00"))

        # Verificar incremento de saldo en sesión: 10000 + 7000 = 17000
        self.session.refresh_from_db()
        self.assertEqual(self.session.expected_balance, Decimal("17000.00"))

        # 2. Venta POS con TARJETA (CARD): Total = 1 * 3500 = $3,500
        card_sale_dto = SaleCreateDto(
            details=(
                SaleDetailDto(
                    product_id=self.product.pk,
                    quantity=Decimal("1.00"),
                    unit_price=Decimal("3500.00"),
                ),
            ),
            payment_method=PaymentMethod.CARD,
            sale_type=Sale.SaleType.POS,
            generate_invoice=False,
        )

        card_sale = SaleService.quick_sale(card_sale_dto, self.user)

        self.assertEqual(card_sale.status, Sale.SaleStatus.COMPLETED)
        self.assertEqual(card_sale.total, Decimal("3500.00"))

        card_payment = Payment.objects.filter(sale=card_sale).first()
        self.assertIsNotNone(card_payment)
        self.assertEqual(card_payment.status, PaymentStatus.COMPLETED)
        self.assertEqual(card_payment.payment_method, PaymentMethod.CARD)

        card_movement = CashMovement.objects.filter(payment=card_payment).first()
        self.assertIsNotNone(card_movement)
        self.assertFalse(card_movement.is_cash)
        self.assertEqual(card_movement.amount, Decimal("3500.00"))

        # Saldo en efectivo se mantiene en 17000 (el pago fue electrónico)
        self.session.refresh_from_db()
        self.assertEqual(self.session.expected_balance, Decimal("17000.00"))

    def test_scenario_g_credit_sale_does_not_affect_cash(self):
        """
        Escenario G: Tratamiento de venta a crédito.
        - Genera Payment con status PENDING (para cartera/cobranza).
        - NO genera movimientos en CashMovement.
        - NO altera expected_balance de la sesión de caja.
        """
        initial_balance = self.session.expected_balance

        credit_sale_dto = SaleCreateDto(
            details=(
                SaleDetailDto(
                    product_id=self.product.pk,
                    quantity=Decimal("3.00"),
                    unit_price=Decimal("3500.00"),
                ),
            ),
            payment_method=PaymentMethod.CREDIT,
            sale_type=Sale.SaleType.POS,
            generate_invoice=False,
        )

        credit_sale = SaleService.quick_sale(credit_sale_dto, self.user)

        self.assertEqual(credit_sale.status, Sale.SaleStatus.COMPLETED)
        self.assertEqual(credit_sale.payment_method, PaymentMethod.CREDIT)

        # Payment en estado PENDING
        payment = Payment.objects.filter(sale=credit_sale).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.status, PaymentStatus.PENDING)
        self.assertEqual(payment.payment_method, PaymentMethod.CREDIT)

        # Ningún movimiento de caja asociado
        movements_count = CashMovement.objects.filter(payment=payment).count()
        self.assertEqual(movements_count, 0)

        # Saldo de caja intacto
        self.session.refresh_from_db()
        self.assertEqual(self.session.expected_balance, initial_balance)

    def test_scenario_h_sale_cancellation_and_reversal(self):
        """
        Escenario H: Reversión y cancelación de ventas.
        - Se crea y completa una venta CASH de $3,500.
        - expected_balance sube a $13,500.
        - Al cancelar la venta:
          - Payment pasa a CANCELLED.
          - Se genera CashMovement OUT con is_cash=True por $3,500.
          - expected_balance regresa a los $10,000 iniciales.
        """
        sale_dto = SaleCreateDto(
            details=(
                SaleDetailDto(
                    product_id=self.product.pk,
                    quantity=Decimal("1.00"),
                    unit_price=Decimal("3500.00"),
                ),
            ),
            payment_method=PaymentMethod.CASH,
            sale_type=Sale.SaleType.POS,
            generate_invoice=False,
        )

        sale = SaleService.quick_sale(sale_dto, self.user)
        self.session.refresh_from_db()
        self.assertEqual(self.session.expected_balance, Decimal("13500.00"))

        payment = Payment.objects.filter(sale=sale).first()
        self.assertEqual(payment.status, PaymentStatus.COMPLETED)

        # Cancelación de la venta
        cancelled_sale = SaleService.cancel_sale(sale, self.user)

        self.assertEqual(cancelled_sale.status, Sale.SaleStatus.CANCELLED)

        # Payment pasa a CANCELLED
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.CANCELLED)

        # Debe existir un movimiento de salida (OUT) que revierte el cobro
        reversal_movement = CashMovement.objects.filter(
            cash_session=self.session,
            movement_type=CashMovement.MovementType.OUT,
            payment=payment,
        ).first()

        self.assertIsNotNone(reversal_movement)
        self.assertEqual(reversal_movement.amount, Decimal("3500.00"))
        self.assertTrue(reversal_movement.is_cash)

        # Saldo en caja regresa a $10,000
        self.session.refresh_from_db()
        self.assertEqual(self.session.expected_balance, Decimal("10000.00"))


class CashSessionApiTests(TestCase):
    """
    Pruebas de la capa API (Endpoints REST) para sesiones de caja y autorización horizontal.
    """

    def setUp(self):
        cache.clear()
        self.client = APIClient()

        # Cajero 1 (Dueño de la sesión)
        self.user1 = User.objects.create_user(
            username="api_cajero1",
            password="Password123!",
            email="api1@example.com",
            document_number="30000001",
        )
        self.role_cajero = Role.objects.create(
            role_name="api_cajero_role",
            permissions={
                "cash.view": True,
                "cash.open": True,
                "cash.close": True,
                "cash.movement": True,
            },
        )
        UserRole.objects.create(user=self.user1, role=self.role_cajero)

        # Cajero 2 (Tercero)
        self.user2 = User.objects.create_user(
            username="api_cajero2",
            password="Password123!",
            email="api2@example.com",
            document_number="30000002",
        )
        UserRole.objects.create(user=self.user2, role=self.role_cajero)

        self.register = CashRegister.objects.create(name="Caja API 1")

    def test_current_session_endpoint_when_closed_and_open(self):
        """
        Prueba GET /api/cash/sessions/current/:
        - Retorna 404 NO_OPEN_SESSION cuando no hay sesión.
        - Retorna 200 con datos de sesión cuando está abierta.
        """
        self.client.force_authenticate(user=self.user1)

        # Sin sesión abierta
        response_closed = self.client.get(reverse("cash-session-current"))
        self.assertEqual(response_closed.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response_closed.data.get("code"), "NO_OPEN_SESSION")

        # Abrir sesión vía API
        open_payload = {
            "cash_register_id": self.register.pk,
            "opening_balance": "50.00",
            "notes": "Apertura desde API",
        }
        response_open = self.client.post(reverse("cash-session-open"), open_payload, format="json")
        self.assertEqual(response_open.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response_open.data.get("code"), "CASH_SESSION_OPENED")

        # Con sesión abierta
        response_current = self.client.get(reverse("cash-session-current"))
        self.assertEqual(response_current.status_code, status.HTTP_200_OK)
        self.assertEqual(response_current.data["data"]["status"], CashSession.SessionStatus.OPEN)
        self.assertEqual(Decimal(response_current.data["data"]["opening_balance"]), Decimal("50.00"))

    def test_add_movement_and_list_movements_endpoints(self):
        """
        Prueba POST /api/cash/sessions/<pk>/movements/ y GET /movements/list/.
        """
        self.client.force_authenticate(user=self.user1)

        session = CashSessionService.open_session(
            CashSessionOpenDto(
                cash_register_id=self.register.pk,
                opening_balance=Decimal("100.00"),
            ),
            self.user1,
        )

        # Registrar movimiento manual de ingreso
        add_mov_url = reverse("cash-session-add-movement", kwargs={"pk": session.pk})
        mov_payload = {
            "amount": "25.00",
            "movement_type": "IN",
            "is_cash": True,
            "description": "Base adicional para monedas",
        }
        response_mov = self.client.post(add_mov_url, mov_payload, format="json")
        self.assertEqual(response_mov.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response_mov.data.get("code"), "CASH_MOVEMENT_CREATED")

        # Listar movimientos
        list_mov_url = reverse("cash-session-movements", kwargs={"pk": session.pk})
        response_list = self.client.get(list_mov_url)
        self.assertEqual(response_list.status_code, status.HTTP_200_OK)
        movements_data = response_list.data.get("data", [])
        self.assertEqual(len(movements_data), 1)
        self.assertEqual(movements_data[0]["movement_type"], "IN")
        self.assertIsNone(movements_data[0]["payment"])
        self.assertIsNone(movements_data[0]["payment_method"])
        self.assertIsNone(movements_data[0]["payment_reference"])

    def test_horizontal_security_prevent_other_user_modifying_session(self):
        """
        Prueba de autorización horizontal:
        Un usuario cajero no puede cerrar ni agregar movimientos a la sesión
        de otro cajero, retornando HTTP 403 Forbidden.
        """
        session_user1 = CashSessionService.open_session(
            CashSessionOpenDto(
                cash_register_id=self.register.pk,
                opening_balance=Decimal("100.00"),
            ),
            self.user1,
        )

        # Autenticar como Cajero 2
        self.client.force_authenticate(user=self.user2)

        # Intentar cerrar la sesión de Cajero 1
        close_url = reverse("cash-session-close", kwargs={"pk": session_user1.pk})
        response_close = self.client.post(
            close_url,
            {"counted_balance": "100.00"},
            format="json",
        )
        self.assertEqual(response_close.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response_close.data.get("code"), "FORBIDDEN_SESSION_CLOSE")

        # Intentar registrar movimiento en la sesión de Cajero 1
        mov_url = reverse("cash-session-add-movement", kwargs={"pk": session_user1.pk})
        response_mov = self.client.post(
            mov_url,
            {"amount": "10.00", "movement_type": "IN", "is_cash": True},
            format="json",
        )
        self.assertEqual(response_mov.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response_mov.data.get("code"), "FORBIDDEN_SESSION_MOVEMENT")
