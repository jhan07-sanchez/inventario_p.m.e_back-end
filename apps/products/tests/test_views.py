from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.categories.models.category import Category
from apps.products.models.product import Product
from apps.users.models import Role, User, UserRole


class ProductViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="product_admin",
            password="adminpassword123",
            email="prod_admin@example.com",
            document_number="99887766",
        )
        self.role = Role.objects.create(
            role_name="product_manager",
            permissions={
                "products.view": True,
                "products.create": True,
                "products.update": True,
                "products.delete": True,
            },
        )
        UserRole.objects.create(user=self.user, role=self.role)

        login_res = self.client.post(
            reverse("auth-login"),
            {"username": "product_admin", "password": "adminpassword123"},
        )
        token = login_res.data["data"]["access_token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        self.category = Category.objects.create(name="Tornillería", is_active=True)
        self.product = Product.objects.create(
            code="TORN-001",
            name="Tornillo 1 pulgada",
            category=self.category,
            purchase_price=Decimal("0.50"),
            sale_price=Decimal("1.00"),
        )

    def test_list_products(self):
        url = reverse("products-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

    def test_create_product(self):
        url = reverse("products-list")
        payload = {
            "code": "TORN-002",
            "name": "Tornillo 2 pulgadas",
            "category": self.category.pk,
            "purchase_price": "0.80",
            "sale_price": "1.50",
            "unit": "UNIT",
        }
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["code"], "TORN-002")

    def test_delete_and_restore_product_via_api(self):
        delete_url = reverse("products-detail", kwargs={"pk": self.product.pk})
        restore_url = reverse("products-restore", kwargs={"pk": self.product.pk})

        # 1. Soft delete
        delete_res = self.client.delete(delete_url)
        self.assertEqual(delete_res.status_code, status.HTTP_200_OK)

        self.product.refresh_from_db()
        self.assertFalse(self.product.is_active)
        self.assertIsNotNone(self.product.deleted_at)

        # 2. Restore soft-deleted product
        restore_res = self.client.post(restore_url)
        self.assertEqual(restore_res.status_code, status.HTTP_200_OK)
        self.assertTrue(restore_res.data["success"])
        self.assertEqual(restore_res.data["code"], "PRODUCT_RESTORED")

        self.product.refresh_from_db()
        self.assertTrue(self.product.is_active)
        self.assertIsNone(self.product.deleted_at)
