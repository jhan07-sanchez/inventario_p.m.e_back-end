"""
Suite de Pruebas de Concurrencia para PostgreSQL — P.M.E.
Valida la integridad de operaciones críticas bajo concurrencia real mediante
TransactionTestCase, hilos concurrentes, barreras de sincronización y select_for_update.

Escenarios:
- Escenario A: Consecutivos empresariales concurrentes sin duplicados.
- Escenario B: Descuento simultáneo de existencias de inventario sin sobreventa.
- Escenario C: Pagos concurrentes sobre la misma orden de compra sin sobrepago.
- Escenario D: Recepción concurrente de compras sin doble procesamiento de stock.
- Escenario E: Operaciones concurrentes multi-tenant aisladas sin contención cruzada.
"""

import threading
from decimal import Decimal
from typing import List

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.test import TestCase, TransactionTestCase

from apps.categories.models import Category
from apps.company_info.models import CompanyInfo
from apps.core.enums import PaymentMethod
from apps.core.models.company_sequence import CompanySequence
from apps.core.services.company_sequence_service import CompanySequenceService
from apps.inventory.models import Inventory
from apps.inventory.services.inventory_service import InventoryService
from apps.products.models import Product
from apps.purchases.dto.purchase_dto import (
    PurchaseCreateDTO,
    PurchaseDetailCreateDTO,
    PurchasePayDTO,
)
from apps.purchases.models import Purchase
from apps.purchases.selectors.purchase_selector import PurchaseSelector
from apps.purchases.services.purchase_payment_service import PurchasePaymentService
from apps.purchases.services.purchase_service import PurchaseService
from apps.sales.dto.sale_detail_dto import SaleDetailDto
from apps.sales.dto.sale_dto import SaleCreateDto
from apps.sales.models import Sale
from apps.sales.services.sale_service import SaleService
from apps.suppliers.models import Supplier
from apps.users.models import CompanyMembership, Role

User = get_user_model()


class PostgresConcurrencyTestSuite(TransactionTestCase):
    """
    TransactionTestCase permite probar transacciones reales y conexiones
    concurrentes separadas (hilos que abren su propia conexión).

    Diseñado específicamente para el motor PostgreSQL (Supabase / Render).
    Bajo SQLite, este caso de prueba se omite porque SQLite no soporta escrituras
    concurrentes multi-hilo y bloquea el archivo entero con 'database table is locked'.
    """

    def setUp(self):
        if connection.vendor == "sqlite":
            self.skipTest(
                "Escenario de concurrencia real diseñado exclusivamente para PostgreSQL (Row-Level Locking). "
                "SQLite bloquea la base de datos completa a nivel de archivo/tabla ('database table is locked'). "
                "Para ejecutar este test en PostgreSQL, configure una base de datos PostgreSQL de prueba o ejecute "
                "scripts/run_postgres_concurrency_tests.py."
            )

        # Empresa 1
        self.c1 = CompanyInfo.objects.create(
            business_name="Empresa Concurrencia A", tax_id="900111222-1"
        )
        # Empresa 2
        self.c2 = CompanyInfo.objects.create(
            business_name="Empresa Concurrencia B", tax_id="900333444-2"
        )

        self.user = User.objects.create_user(
            username="concurrent_user",
            email="concurrent@test.com",
            password="Password123!",
            document_number="99887766",
        )
        self.role = Role.objects.create(
            role_name="Admin",
            permissions={"all": True},
        )
        CompanyMembership.objects.create(
            user=self.user,
            company=self.c1,
            role=self.role,
            is_active=True,
            status=CompanyMembership.MembershipStatus.ACTIVE,
        )
        CompanyMembership.objects.create(
            user=self.user,
            company=self.c2,
            role=self.role,
            is_active=True,
            status=CompanyMembership.MembershipStatus.ACTIVE,
        )

        # Catálogo para C1
        self.cat1 = Category.objects.create(name="Cat Concurrente C1", company=self.c1)
        self.prod1 = Product.objects.create(
            name="Item Concurrente C1",
            code="CONC-01",
            company=self.c1,
            category=self.cat1,
            purchase_price=Decimal("10.00"),
            sale_price=Decimal("20.00"),
        )
        self.inv1 = Inventory.objects.create(
            product=self.prod1,
            current_stock=Decimal("10.00"),
            minimum_stock=Decimal("1.00"),
        )

        # Catálogo para C2
        self.cat2 = Category.objects.create(name="Cat Concurrente C2", company=self.c2)
        self.prod2 = Product.objects.create(
            name="Item Concurrente C2",
            code="CONC-02",
            company=self.c2,
            category=self.cat2,
            purchase_price=Decimal("15.00"),
            sale_price=Decimal("30.00"),
        )
        self.inv2 = Inventory.objects.create(
            product=self.prod2,
            current_stock=Decimal("10.00"),
            minimum_stock=Decimal("1.00"),
        )

    def test_scenario_a_concurrent_company_sequences(self):
        """
        Escenario A: Múltiples hilos concurrentes solicitan consecutivos de venta
        para la misma empresa.
        Resultado: No existen números duplicados y el contador final es exacto.
        """
        num_threads = 5
        barrier = threading.Barrier(num_threads)
        results: List[str] = []
        errors: List[Exception] = []
        lock = threading.Lock()

        def worker():
            try:
                # Cada hilo cierra la conexión residual para abrir su propio canal a la BD
                connection.close()
                barrier.wait()
                _, assigned_number = CompanySequenceService.get_next_number(
                    company_id=self.c1.pk,
                    document_type=CompanySequence.DocumentType.SALE,
                    prefix="VTA",
                    padding=6,
                )
                with lock:
                    results.append(assigned_number)
            except Exception as e:
                with lock:
                    errors.append(e)
            finally:
                connection.close()

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Errores en concurrencia: {errors}")
        self.assertEqual(len(results), num_threads)
        # Todos los números deben ser estrictamente únicos
        self.assertEqual(
            len(set(results)), num_threads, f"Colisión detectada: {results}"
        )

    def test_scenario_b_concurrent_inventory_exit_prevents_negative_stock(self):
        """
        Escenario B: Dos hilos intentan vender simultáneamente más stock del disponible.
        Stock inicial = 10. Cada hilo solicita 8 (total 16 > 10).
        Resultado: Una transacción triunfa y la otra falla por stock insuficiente.
        """
        num_threads = 2
        barrier = threading.Barrier(num_threads)
        successes = []
        failures = []
        lock = threading.Lock()

        def sell_worker():
            connection.close()
            try:
                barrier.wait()
                with transaction.atomic():
                    # Intenta descontar 8 unidades con select_for_update
                    InventoryService.register_exit(
                        inventory=self.inv1,
                        data={
                            "quantity": Decimal("8.00"),
                            "reference": "TEST-CONCURRENT-EXIT",
                            "notes": "Prueba de salida concurrente",
                        },
                        user=self.user,
                    )
                with lock:
                    successes.append(True)
            except (ValidationError, Exception) as e:
                with lock:
                    failures.append(e)
            finally:
                connection.close()

        threads = [threading.Thread(target=sell_worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Debe haber exactamente 1 éxito y 1 fallo por saldo insuficiente
        self.assertEqual(len(successes), 1)
        self.assertEqual(len(failures), 1)

        # Stock final debe ser exactamente 2.00, jamás negativo
        self.inv1.refresh_from_db()
        self.assertEqual(self.inv1.current_stock, Decimal("2.00"))

    def test_scenario_c_concurrent_payments_prevent_overpayment(self):
        """
        Escenario C: Pagos concurrentes sobre una misma orden de compra.
        Total de compra: $100.
        Dos hilos intentan pagar simultáneamente $70 cada uno (total $140 > $100).
        Resultado: Uno se aplica con éxito y el otro es rechazado por exceder el saldo.
        """
        sup = Supplier.objects.create(
            business_name="Proveedor Concurrente",
            document_number="SUP-CONC-1",
            company=self.c1,
        )
        pur = PurchaseService.create_purchase(
            PurchaseCreateDTO(
                supplier_id=sup.pk,
                company_id=self.c1.pk,
                issue_date=None,
                notes="Compra para test concurrente",
                details=[
                    PurchaseDetailCreateDTO(
                        product_id=self.prod1.pk,
                        quantity=Decimal("10"),
                        unit_price=Decimal("10.00"),
                    )
                ],
            )
        )
        pur.status = Purchase.Status.PENDING
        pur.save(update_fields=["status"])

        num_threads = 2
        barrier = threading.Barrier(num_threads)
        successes = []
        failures = []
        lock = threading.Lock()

        def pay_worker(worker_id):
            connection.close()
            try:
                barrier.wait()
                PurchasePaymentService.pay_purchase(
                    purchase_id=pur.pk,
                    dto=PurchasePayDTO(
                        amount=Decimal("70.00"),
                        payment_method=PaymentMethod.TRANSFER,
                        reference=f"TRF-CONC-{worker_id}",
                    ),
                    user=self.user,
                )
                with lock:
                    successes.append(worker_id)
            except (ValidationError, Exception) as e:
                with lock:
                    failures.append(e)
            finally:
                connection.close()

        threads = [
            threading.Thread(target=pay_worker, args=(1,)),
            threading.Thread(target=pay_worker, args=(2,)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(successes), 1)
        self.assertEqual(len(failures), 1)
        self.assertIn("supera el saldo pendiente", str(failures[0]))

    def test_scenario_d_concurrent_purchase_receptions_prevent_duplicate_entry(self):
        """
        Escenario D: Dos hilos intentan recibir concurrentemente la misma orden de compra.
        Resultado: Solo uno transita a RECEIVED y el otro falla por transición inválida.
        """
        sup = Supplier.objects.create(
            business_name="Proveedor Concurrente D",
            document_number="SUP-CONC-D",
            company=self.c1,
        )
        pur = PurchaseService.create_purchase(
            PurchaseCreateDTO(
                supplier_id=sup.pk,
                company_id=self.c1.pk,
                issue_date=None,
                notes="Compra recepción concurrente",
                details=[
                    PurchaseDetailCreateDTO(
                        product_id=self.prod1.pk,
                        quantity=Decimal("5"),
                        unit_price=Decimal("10.00"),
                    )
                ],
            )
        )
        pur.status = Purchase.Status.PENDING
        pur.save(update_fields=["status"])

        num_threads = 2
        barrier = threading.Barrier(num_threads)
        successes = []
        failures = []
        lock = threading.Lock()

        def receive_worker():
            connection.close()
            try:
                barrier.wait()
                # Recargar compra fresca con bloqueo dentro de la llamada del servicio
                PurchaseService.receive_purchase(pur, user=self.user)
                with lock:
                    successes.append(True)
            except Exception as e:
                with lock:
                    failures.append(e)
            finally:
                connection.close()

        threads = [threading.Thread(target=receive_worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(successes), 1)
        self.assertEqual(len(failures), 1)

    def test_scenario_e_concurrent_multi_tenant_isolation(self):
        """
        Escenario E: Dos empresas ejecutan transacciones simultáneas de venta.
        Resultado: Ambas triunfan, sus consecutivos inician independientemente en VTA-000001
        y no hay interferencia cruzada.
        """
        barrier = threading.Barrier(2)
        results = {}
        errors = []
        lock = threading.Lock()

        def tenant_sale_worker(company, product):
            connection.close()
            try:
                barrier.wait()
                dto = SaleCreateDto(
                    customer_id=None,
                    company_id=company.pk,
                    sale_type=Sale.SaleType.ADMIN,
                    payment_method=PaymentMethod.CASH,
                    discount=Decimal("0.00"),
                    tax=Decimal("0.00"),
                    notes="Venta simultánea multi-tenant",
                    details=(
                        SaleDetailDto(
                            product_id=product.pk,
                            quantity=Decimal("1.00"),
                            unit_price=product.sale_price,
                            discount=Decimal("0.00"),
                        ),
                    ),
                )
                sale = SaleService.create_sale(dto, user=self.user)
                with lock:
                    results[company.pk] = sale.sale_number
            except Exception as e:
                with lock:
                    errors.append(e)
            finally:
                connection.close()

        t1 = threading.Thread(target=tenant_sale_worker, args=(self.c1, self.prod1))
        t2 = threading.Thread(target=tenant_sale_worker, args=(self.c2, self.prod2))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(len(errors), 0, f"Errores en ventas multi-tenant: {errors}")
        self.assertEqual(len(results), 2)
        # Ambas empresas deben haber generado VTA-000001 para su primera venta respectiva
        self.assertEqual(results[self.c1.pk], "VTA-000001")
        self.assertEqual(results[self.c2.pk], "VTA-000001")


class CompanySequenceSequentialTests(TestCase):
    """
    Pruebas unitarias secuenciales de CompanySequenceService y generación
    de consecutivos independientes por empresa. Se ejecutan tanto en SQLite
    como en PostgreSQL.
    """

    def setUp(self):
        self.c1 = CompanyInfo.objects.create(
            business_name="Seq Tenant Alpha", tax_id="800111111-1"
        )
        self.c2 = CompanyInfo.objects.create(
            business_name="Seq Tenant Beta", tax_id="800222222-2"
        )
        self.user = User.objects.create_user(
            username="seq_user",
            email="seq@test.com",
            password="Password123!",
            document_number="11223344",
        )
        self.role = Role.objects.create(role_name="Admin", permissions={"all": True})
        CompanyMembership.objects.create(
            user=self.user,
            company=self.c1,
            role=self.role,
            is_active=True,
            status=CompanyMembership.MembershipStatus.ACTIVE,
        )
        CompanyMembership.objects.create(
            user=self.user,
            company=self.c2,
            role=self.role,
            is_active=True,
            status=CompanyMembership.MembershipStatus.ACTIVE,
        )

    def test_first_sequence_starts_at_one(self):
        """Primera llamada genera 1 con formato VTA-000001."""
        current_val, formatted = CompanySequenceService.get_next_number(
            company_id=self.c1.pk,
            document_type=CompanySequence.DocumentType.SALE,
            prefix="VTA",
            padding=6,
        )
        self.assertEqual(current_val, 1)
        self.assertEqual(formatted, "VTA-000001")

    def test_subsequent_sequence_increments_monotonically(self):
        """Generaciones sucesivas incrementan 1, 2, 3."""
        _, f1 = CompanySequenceService.get_next_number(
            company_id=self.c1.pk,
            document_type=CompanySequence.DocumentType.SALE,
            prefix="VTA",
            padding=6,
        )
        _, f2 = CompanySequenceService.get_next_number(
            company_id=self.c1.pk,
            document_type=CompanySequence.DocumentType.SALE,
            prefix="VTA",
            padding=6,
        )
        current_val, f3 = CompanySequenceService.get_next_number(
            company_id=self.c1.pk,
            document_type=CompanySequence.DocumentType.SALE,
            prefix="VTA",
            padding=6,
        )
        self.assertEqual(f1, "VTA-000001")
        self.assertEqual(f2, "VTA-000002")
        self.assertEqual(f3, "VTA-000003")
        self.assertEqual(current_val, 3)

    def test_independent_sequences_between_companies(self):
        """Cada empresa tiene su propio contador independiente."""
        _, c1_num1 = CompanySequenceService.get_next_number(
            company_id=self.c1.pk,
            document_type=CompanySequence.DocumentType.SALE,
            prefix="VTA",
        )
        _, c2_num1 = CompanySequenceService.get_next_number(
            company_id=self.c2.pk,
            document_type=CompanySequence.DocumentType.SALE,
            prefix="VTA",
        )
        _, c1_num2 = CompanySequenceService.get_next_number(
            company_id=self.c1.pk,
            document_type=CompanySequence.DocumentType.SALE,
            prefix="VTA",
        )

        self.assertEqual(c1_num1, "VTA-000001")
        self.assertEqual(c2_num1, "VTA-000001")
        self.assertEqual(c1_num2, "VTA-000002")

    def test_legacy_seed_detection_prevents_collision(self):
        """
        Si existen ventas previas con numeración global legacy (ej. VTA-000045),
        la semilla inicial arranca en 46 para evitar colisiones.
        """
        Sale.objects.create(
            company=self.c1,
            user=self.user,
            sale_number="VTA-000045",
            total=Decimal("100.00"),
            payment_method=PaymentMethod.CASH,
        )

        current_val, formatted = CompanySequenceService.get_next_number(
            company_id=self.c1.pk,
            document_type=CompanySequence.DocumentType.SALE,
            prefix="VTA",
            padding=6,
        )
        self.assertEqual(current_val, 46)
        self.assertEqual(formatted, "VTA-000046")

    def test_legacy_seed_ignores_other_companies(self):
        """Ventas legacy en Empresa 2 no alteran la semilla de Empresa 1."""
        Sale.objects.create(
            company=self.c2,
            user=self.user,
            sale_number="VTA-000099",
            total=Decimal("200.00"),
            payment_method=PaymentMethod.CASH,
        )

        current_val, formatted = CompanySequenceService.get_next_number(
            company_id=self.c1.pk,
            document_type=CompanySequence.DocumentType.SALE,
            prefix="VTA",
            padding=6,
        )
        # Empresa 1 no tenía ventas, debe arrancar en 1
        self.assertEqual(current_val, 1)
        self.assertEqual(formatted, "VTA-000001")


class PurchasePaymentForeignKeyTests(TestCase):
    """
    Pruebas unitarias de la relación explícita ForeignKey Payment.purchase
    y compatibilidad con selectores y servicios.
    """

    def setUp(self):
        self.company = CompanyInfo.objects.create(
            business_name="Purchasing Co", tax_id="901999888-1"
        )
        self.user = User.objects.create_user(
            username="purchase_user",
            email="pur@test.com",
            password="Password123!",
            document_number="55443322",
        )
        self.role = Role.objects.create(role_name="Admin", permissions={"all": True})
        CompanyMembership.objects.create(
            user=self.user,
            company=self.company,
            role=self.role,
            is_active=True,
            status=CompanyMembership.MembershipStatus.ACTIVE,
        )
        self.cat = Category.objects.create(name="Materiales", company=self.company)
        self.prod = Product.objects.create(
            name="Materia Prima A",
            code="MP-01",
            company=self.company,
            category=self.cat,
            purchase_price=Decimal("50.00"),
            sale_price=Decimal("100.00"),
        )
        self.sup = Supplier.objects.create(
            business_name="Distribuidora Mayorista",
            document_number="SUP-9988",
            company=self.company,
        )

    def test_pay_purchase_assigns_explicit_foreign_key(self):
        """El servicio PurchasePaymentService asigna purchase_id al Payment."""
        purchase = PurchaseService.create_purchase(
            PurchaseCreateDTO(
                supplier_id=self.sup.pk,
                company_id=self.company.pk,
                issue_date=None,
                notes="Compra FK test",
                details=[
                    PurchaseDetailCreateDTO(
                        product_id=self.prod.pk,
                        quantity=Decimal("2"),
                        unit_price=Decimal("50.00"),
                    )
                ],
            )
        )
        purchase.status = Purchase.Status.PENDING
        purchase.save(update_fields=["status"])

        result = PurchasePaymentService.pay_purchase(
            purchase_id=purchase.pk,
            dto=PurchasePayDTO(
                amount=Decimal("40.00"),
                payment_method=PaymentMethod.TRANSFER,
                reference="PAGO-PARCIAL-1",
            ),
            user=self.user,
        )

        from apps.cash.models.payment import Payment

        payment = Payment.objects.get(pk=result["payment_id"])
        self.assertIsNotNone(payment.purchase_id)
        self.assertEqual(payment.purchase_id, purchase.pk)
        self.assertEqual(payment.purchase, purchase)
        self.assertEqual(purchase.payments.count(), 1)
        self.assertEqual(purchase.payments.first().id_payment, payment.id_payment)

    def test_purchase_selector_calculates_with_fk_and_legacy(self):
        """
        PurchaseSelector soporta tanto pagos con FK purchase_id como
        pagos legacy vinculados por referencia estricta 'COMPRA #ID'.
        """
        from apps.cash.models.payment import Payment

        purchase = PurchaseService.create_purchase(
            PurchaseCreateDTO(
                supplier_id=self.sup.pk,
                company_id=self.company.pk,
                issue_date=None,
                notes="Compra Dual Query test",
                details=[
                    PurchaseDetailCreateDTO(
                        product_id=self.prod.pk,
                        quantity=Decimal("4"),
                        unit_price=Decimal("25.00"),
                    )
                ],
            )
        )
        purchase.status = Purchase.Status.PENDING
        purchase.save(update_fields=["status"])

        # Pago 1 con FK explícita
        Payment.objects.create(
            purchase=purchase,
            amount=Decimal("30.00"),
            payment_method=PaymentMethod.CASH,
            reference="ABONO-FK",
        )

        # Pago 2 legacy sin FK pero con referencia delimitada estricta
        Payment.objects.create(
            purchase=None,
            amount=Decimal("20.00"),
            payment_method=PaymentMethod.TRANSFER,
            reference=f"COMPRA #{purchase.pk} - Pago legado",
        )

        # 1. Probar que el filtro del selector recupera ambos pagos (FK y legacy)
        payments = Payment.objects.filter(
            PurchaseSelector.get_purchase_payment_filter(purchase.pk)
        )
        self.assertEqual(payments.count(), 2)

        # 2. Probar attach_payment_totals (usado en vistas/listas para evitar N+1)
        PurchaseSelector.attach_payment_totals([purchase])
        self.assertEqual(purchase._cached_paid, Decimal("50.00"))

        # 3. Probar get_purchase_payment_summary
        summary = PurchasePaymentService.get_purchase_payment_summary(purchase.pk)
        self.assertEqual(Decimal(summary["total_paid"]), Decimal("50.00"))
        self.assertEqual(Decimal(summary["pending_balance"]), Decimal("50.00"))
