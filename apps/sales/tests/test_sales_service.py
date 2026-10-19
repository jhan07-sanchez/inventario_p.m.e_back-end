from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase

from apps.categories.models import Category
from apps.customers.models import Customer
from apps.inventory.models import Inventory
from apps.invoices.models import InvoiceTemplate
from apps.products.models import Product
from apps.sales.dto.sale_detail_dto import SaleDetailDto
from apps.sales.dto.sale_dto import SaleCreateDto
from apps.sales.models import Sale
from apps.sales.services.sale_service import SaleService
from apps.users.models import User


class SaleServiceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="seller_user",
            password="testpassword123",
            email="seller@example.com",
            document_number="987654321",
        )
        self.category = Category.objects.create(
            name="General",
            description="Categoría general",
        )
        self.product = Product.objects.create(
            code="PRD-001",
            name="Laptop Gamer",
            category=self.category,
            purchase_price=Decimal("800.00"),
            sale_price=Decimal("1200.00"),
        )
        self.inventory = Inventory.objects.create(
            product=self.product,
            current_stock=Decimal("20.00"),
            minimum_stock=Decimal("2.00"),
        )
        self.customer = Customer.objects.create(
            document_type=Customer.DocumentType.CC,
            document_number="1020304050",
            first_name="Carlos",
            last_name="Gómez",
            email="carlos@example.com",
        )
        # Plantilla de factura por defecto requerida para completar ventas
        self.invoice_template = InvoiceTemplate.objects.create(
            name="Plantilla Factura Venta Estándar",
            document_type=InvoiceTemplate.DocumentType.SALE_INVOICE,
            is_default=True,
            is_active=True,
        )

    def test_create_sale_pending(self):
        """Crear una venta en estado PENDING sin descontar inventario aún."""
        dto = SaleCreateDto(
            customer_id=self.customer.pk,
            details=(
                SaleDetailDto(
                    product_id=self.product.pk,
                    quantity=Decimal("2.00"),
                    unit_price=Decimal("1200.00"),
                ),
            ),
            payment_method="CASH",
        )

        sale = SaleService.create_sale(dto=dto, user=self.user)

        self.assertEqual(sale.status, Sale.SaleStatus.PENDING)
        self.assertEqual(sale.customer, self.customer)
        self.assertEqual(sale.subtotal, Decimal("2400.00"))
        self.assertEqual(sale.total, Decimal("2400.00"))
        self.assertEqual(sale.details.count(), 1)

        # El inventario debe permanecer intacto hasta completar
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.current_stock, Decimal("20.00"))

    def test_complete_sale_decrements_inventory(self):
        """Completar una venta debe cambiar su estado a COMPLETED y descontar stock."""
        dto = SaleCreateDto(
            customer_id=self.customer.pk,
            details=(
                SaleDetailDto(
                    product_id=self.product.pk,
                    quantity=Decimal("3.00"),
                    unit_price=Decimal("1200.00"),
                ),
            ),
            payment_method="CASH",
        )

        sale = SaleService.create_sale(dto=dto, user=self.user)
        completed_sale = SaleService.complete_sale(sale=sale, user=self.user)

        self.assertEqual(completed_sale.status, Sale.SaleStatus.COMPLETED)

        # El inventario debe haber disminuido en 3 unidades
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.current_stock, Decimal("17.00"))

    def test_create_sale_consumer_final(self):
        """Una venta POS puede crearse sin cliente (Consumidor Final)."""
        dto = SaleCreateDto(
            customer_id=None,
            details=(
                SaleDetailDto(
                    product_id=self.product.pk,
                    quantity=Decimal("1.00"),
                    unit_price=Decimal("1200.00"),
                ),
            ),
            payment_method="CASH",
            amount_received=Decimal("1500.00"),
        )

        sale = SaleService.create_sale(dto=dto, user=self.user)

        self.assertIsNone(sale.customer)
        self.assertEqual(sale.total, Decimal("1200.00"))
        self.assertEqual(sale.change_amount, Decimal("300.00"))

    def test_create_sale_without_details_raises_error(self):
        """No se puede crear una venta sin líneas de detalle."""
        dto = SaleCreateDto(
            customer_id=self.customer.pk,
            details=(),
        )

        with self.assertRaises(Exception):
            SaleService.create_sale(dto=dto, user=self.user)
