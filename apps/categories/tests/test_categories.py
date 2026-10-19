from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.categories.models.category import Category
from apps.categories.selectors.category_selector import CategorySelector
from apps.categories.services.category_service import CategoryService
from apps.users.models import Role, User, UserRole


class CategoryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="category_admin",
            password="adminpassword123",
            email="cat_admin@example.com",
            document_number="77889900",
        )
        self.role = Role.objects.create(
            role_name="category_manager",
            permissions={
                "categories.view": True,
                "categories.create": True,
                "categories.update": True,
                "categories.delete": True,
            },
        )
        UserRole.objects.create(user=self.user, role=self.role)

        login_res = self.client.post(
            reverse("auth-login"),
            {"username": "category_admin", "password": "adminpassword123"},
        )
        token = login_res.data["data"]["access_token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        self.category = Category.objects.create(
            name="Pinturas y Solventes",
            description="Línea de acabados",
            is_active=True,
        )

    def test_category_str(self):
        self.assertEqual(str(self.category), "Pinturas y Solventes")

    def test_category_selector_get_by_id_include_deleted(self):
        self.category.delete()
        self.category.refresh_from_db()
        self.assertFalse(self.category.is_active)

        with self.assertRaises(Category.DoesNotExist):
            CategorySelector.get_category_by_id(self.category.pk, include_deleted=False)

        found = CategorySelector.get_category_by_id(self.category.pk, include_deleted=True)
        self.assertEqual(found.pk, self.category.pk)

    def test_category_service_restore(self):
        CategoryService.deactivate_category(self.category)
        self.category.refresh_from_db()
        self.assertFalse(self.category.is_active)

        CategoryService.restore_category(self.category)
        self.category.refresh_from_db()
        self.assertTrue(self.category.is_active)

    def test_api_list_and_create_category(self):
        url = reverse("categories-list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        payload = {
            "name": "Seguridad Industrial",
            "description": "Cascos, guantes y protección",
        }
        create_res = self.client.post(url, payload)
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_res.data["data"]["name"], "Seguridad Industrial")

    def test_api_delete_and_restore_category(self):
        delete_url = reverse("categories-detail", kwargs={"pk": self.category.pk})
        restore_url = reverse("categories-restore", kwargs={"pk": self.category.pk})

        del_res = self.client.delete(delete_url)
        self.assertEqual(del_res.status_code, status.HTTP_200_OK)

        self.category.refresh_from_db()
        self.assertFalse(self.category.is_active)
        self.assertIsNotNone(self.category.deleted_at)

        rest_res = self.client.post(restore_url)
        self.assertEqual(rest_res.status_code, status.HTTP_200_OK)
        self.assertEqual(rest_res.data["code"], "CATEGORY_RESTORED")

        self.category.refresh_from_db()
        self.assertTrue(self.category.is_active)
        self.assertIsNone(self.category.deleted_at)
