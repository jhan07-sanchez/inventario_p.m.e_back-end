from decimal import Decimal
from django.test import TestCase

from apps.categories.models.category import Category
from apps.products.models.product import Product
from apps.products.serializers.product_serializer import (
    ProductCreateSerializer,
    ProductListSerializer,
)


class ProductSerializerTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Herramientas", is_active=True)
        self.product = Product.objects.create(
            code="HERR-001",
            name="Destornillador Phillips",
            category=self.category,
            purchase_price=Decimal("4.00"),
            sale_price=Decimal("8.00"),
            unit=Product.Unit.UNIT,
        )

    def test_product_list_serializer(self):
        serializer = ProductListSerializer(self.product)
        data = serializer.data
        self.assertEqual(data["code"], "HERR-001")
        self.assertEqual(data["category_name"], "Herramientas")
        self.assertEqual(Decimal(data["profit_amount"]), Decimal("4.00"))
        self.assertEqual(Decimal(data["profit_margin_percentage"]), Decimal("100.00"))

    def test_product_create_serializer_valid(self):
        payload = {
            "code": "HERR-002",
            "name": "Llave Inglesa",
            "category": self.category.pk,
            "purchase_price": "12.00",
            "sale_price": "18.00",
            "unit": "UNIT",
        }
        serializer = ProductCreateSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)
