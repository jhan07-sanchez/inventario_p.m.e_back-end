from decimal import Decimal

from django.test import TestCase

from apps.categories.models.category import Category
from apps.products.models.product import Product


class ProductModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Ferretería")
        self.product = Product.objects.create(
            code="PRD-001",
            barcode="7701234567890",
            name="Martillo de Uña",
            description="Martillo de acero",
            category=self.category,
            purchase_price=Decimal("10.00"),
            sale_price=Decimal("15.00"),
            unit=Product.Unit.UNIT,
        )

    def test_product_str(self):
        self.assertEqual(str(self.product), "PRD-001 - Martillo de Uña")

    def test_profit_calculations(self):
        self.assertEqual(self.product.profit_amount, Decimal("5.00"))
        self.assertEqual(self.product.profit_margin_percentage, Decimal("50.00"))

    def test_profit_margin_zero_purchase_price(self):
        free_product = Product.objects.create(
            code="PRD-002",
            name="Muestra Gratis",
            category=self.category,
            purchase_price=Decimal("0.00"),
            sale_price=Decimal("1.00"),
        )
        self.assertEqual(free_product.profit_margin_percentage, Decimal("0.00"))

    def test_soft_delete_and_restore(self):
        self.assertTrue(self.product.is_active)
        self.assertIsNone(self.product.deleted_at)

        self.product.delete()
        self.product.refresh_from_db()
        self.assertFalse(self.product.is_active)
        self.assertIsNotNone(self.product.deleted_at)

        # BaseManager filters it out
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())
        # all_objects includes it
        self.assertTrue(Product.all_objects.filter(pk=self.product.pk).exists())

        # Restore
        self.product.restore()
        self.product.refresh_from_db()
        self.assertTrue(self.product.is_active)
        self.assertIsNone(self.product.deleted_at)
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())
