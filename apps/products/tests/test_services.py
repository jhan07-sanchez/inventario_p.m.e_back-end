from decimal import Decimal

from django.test import TestCase

from apps.categories.models.category import Category
from apps.core.exceptions.custom_exceptions import (
    CategoryInactiveException,
    ProductAlreadyExistsException,
)
from apps.products.models.product import Product
from apps.products.selectors.product_selector import ProductSelector
from apps.products.services.product_service import ProductService


class ProductServiceTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Materiales Eléctricos", is_active=True)
        self.service = ProductService()

    def test_create_product_success(self):
        data = {
            "code": "ELEC-001",
            "name": "Cable 12 AWG",
            "category": self.category,
            "purchase_price": Decimal("25.00"),
            "sale_price": Decimal("35.00"),
            "unit": Product.Unit.METER,
        }
        product = ProductService.create_product(data)
        self.assertIsNotNone(product.pk)
        self.assertEqual(product.code, "ELEC-001")
        self.assertTrue(product.is_active)

    def test_create_product_inactive_category_fails(self):
        self.category.is_active = False
        self.category.save()

        data = {
            "code": "ELEC-002",
            "name": "Cable 14 AWG",
            "category": self.category,
            "purchase_price": Decimal("20.00"),
            "sale_price": Decimal("30.00"),
        }
        with self.assertRaises(CategoryInactiveException):
            ProductService.create_product(data)

    def test_create_product_duplicate_code_fails(self):
        ProductService.create_product({
            "code": "DUP-001",
            "name": "Producto Original",
            "category": self.category,
            "purchase_price": Decimal("10.00"),
            "sale_price": Decimal("15.00"),
        })

        with self.assertRaises(ProductAlreadyExistsException):
            ProductService.create_product({
                "code": "DUP-001",
                "name": "Otro Producto",
                "category": self.category,
                "purchase_price": Decimal("10.00"),
                "sale_price": Decimal("15.00"),
            })

    def test_deactivate_and_restore_product(self):
        product = ProductService.create_product({
            "code": "REST-001",
            "name": "Producto a Restaurar",
            "category": self.category,
            "purchase_price": Decimal("5.00"),
            "sale_price": Decimal("10.00"),
        })

        ProductService.deactivate_product(product)
        product.refresh_from_db()
        self.assertFalse(product.is_active)

        # Base selector without include_deleted does not find it
        with self.assertRaises(Exception):
            ProductSelector.get_by_id(product.pk, include_deleted=False)

        # Selector with include_deleted finds it
        found = ProductSelector.get_by_id(product.pk, include_deleted=True)
        self.assertEqual(found.pk, product.pk)

        # Restore product
        ProductService.restore_product(found)
        found.refresh_from_db()
        self.assertTrue(found.is_active)
        self.assertIsNone(found.deleted_at)
