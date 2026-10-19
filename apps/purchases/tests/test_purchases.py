from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.categories.models import Category
from apps.products.models import Product
from apps.purchases.dto.purchase_dto import PurchaseCreateDTO, PurchaseDetailCreateDTO
from apps.purchases.models import Purchase
from apps.purchases.services.purchase_service import PurchaseService
from apps.suppliers.models import Supplier


class PurchaseServiceTests(TestCase):
    def setUp(self):
        self.supplier = Supplier.objects.create(
            document_type=Supplier.DocumentType.NIT,
            document_number="900123456-1",
            business_name="Proveedor Mayorista S.A.S.",
            email="contacto@proveedor.com",
        )
        self.category = Category.objects.create(
            name="Insumos",
            description="Categoría de insumos",
        )
        self.product = Product.objects.create(
            code="INS-001",
            name="Teclado USB",
            category=self.category,
            purchase_price=Decimal("15.50"),
            sale_price=Decimal("25.00"),
        )

    def test_create_purchase(self):
        dto = PurchaseCreateDTO(
            supplier_id=self.supplier.pk,
            issue_date=timezone.now().date(),
            notes="Prueba de compra",
            details=[
                PurchaseDetailCreateDTO(
                    product_id=self.product.pk,
                    quantity=Decimal("10.00"),
                    unit_price=Decimal("15.50"),
                )
            ],
        )

        purchase = PurchaseService.create_purchase(dto)

        self.assertIsNotNone(purchase)
        self.assertEqual(purchase.status, Purchase.Status.DRAFT)
        self.assertEqual(purchase.subtotal, Decimal("155.00"))
        self.assertEqual(purchase.total, Decimal("155.00"))
        self.assertEqual(purchase.details.count(), 1)

    def test_confirm_purchase(self):
        dto = PurchaseCreateDTO(
            supplier_id=self.supplier.pk,
            issue_date=timezone.now().date(),
            notes="Prueba de compra",
            details=[
                PurchaseDetailCreateDTO(
                    product_id=self.product.pk,
                    quantity=Decimal("5.00"),
                    unit_price=Decimal("10.00"),
                )
            ],
        )
        purchase = PurchaseService.create_purchase(dto)
        purchase = PurchaseService.confirm_purchase(purchase)

        self.assertEqual(purchase.status, Purchase.Status.PENDING)
