from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.exceptions.custom_exceptions import (
    FinancialCategoryAlreadyExistsException,
    FinancialCategoryNotFoundException,
)
from apps.finance.models.financial_category import FinancialCategory
from apps.finance.services.financial_category_service import FinancialCategoryService
from apps.users.models import Role, User, UserRole


class FinancialCategoryTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="tesorero_cat",
            password="Password123!",
            email="tesorero_cat@example.com",
            document_number="80005001",
        )
        self.role = Role.objects.create(
            role_name="tesoreria_cat_role",
            permissions={
                "finance.view": True,
                "finance.create": True,
                "finance.update": True,
            },
        )
        UserRole.objects.create(user=self.user, role=self.role)
        self.client.force_authenticate(user=self.user)

    def test_create_category_service_success(self):
        cat = FinancialCategoryService.create_category(
            name="Venta Mostrador",
            category_type=FinancialCategory.CategoryType.INFLOW,
            description="Ingresos de venta directa",
        )
        self.assertIsNotNone(cat.pk)
        self.assertEqual(cat.name, "Venta Mostrador")
        self.assertEqual(cat.category_type, FinancialCategory.CategoryType.INFLOW)

    def test_create_duplicate_category_raises_error(self):
        FinancialCategoryService.create_category(
            name="Nómina",
            category_type=FinancialCategory.CategoryType.OUTFLOW,
        )
        with self.assertRaises(FinancialCategoryAlreadyExistsException):
            FinancialCategoryService.create_category(
                name="Nómina",
                category_type=FinancialCategory.CategoryType.OUTFLOW,
            )

    def test_update_category_service(self):
        cat = FinancialCategoryService.create_category(
            name="Servicios",
            category_type=FinancialCategory.CategoryType.OUTFLOW,
        )
        updated = FinancialCategoryService.update_category(
            category_id=cat.pk,
            name="Servicios Públicos",
            description="Agua, luz e internet",
        )
        self.assertEqual(updated.name, "Servicios Públicos")
        self.assertEqual(updated.description, "Agua, luz e internet")

    def test_update_non_existent_category_raises_error(self):
        with self.assertRaises(FinancialCategoryNotFoundException):
            FinancialCategoryService.update_category(
                category_id=999999,
                name="Nueva",
            )

    def test_deactivate_category_soft_delete(self):
        cat = FinancialCategoryService.create_category(
            name="Categoría Temporal",
            category_type=FinancialCategory.CategoryType.INFLOW,
        )
        FinancialCategoryService.deactivate_category(cat.pk)
        cat.refresh_from_db()
        self.assertFalse(cat.is_active)
        self.assertIsNotNone(cat.deleted_at)

    def test_category_endpoints_crud(self):
        url = reverse("financial-categories-list")
        payload = {
            "name": "Arrendamiento",
            "category_type": "OUTFLOW",
            "description": "Pago mensual de local",
        }
        res = self.client.post(url, data=payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        cat_id = res.data["data"]["id_financial_category"]

        # List
        res_list = self.client.get(url)
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)

        # Retrieve
        detail_url = reverse("financial-categories-detail", kwargs={"pk": cat_id})
        res_detail = self.client.get(detail_url)
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(res_detail.data["data"]["name"], "Arrendamiento")

