from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.suppliers.models.supplier import Supplier
from apps.suppliers.selectors.supplier_selector import SupplierSelector
from apps.suppliers.services.supplier_service import SupplierService
from apps.users.models import Role, User, UserRole


class SupplierTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="supplier_admin",
            password="adminpassword123",
            email="supp_admin@example.com",
            document_number="55443322",
        )
        self.role = Role.objects.create(
            role_name="supplier_manager",
            permissions={
                "suppliers.view": True,
                "suppliers.create": True,
                "suppliers.update": True,
                "suppliers.delete": True,
            },
        )
        UserRole.objects.create(user=self.user, role=self.role)

        login_res = self.client.post(
            reverse("auth-login"),
            {"username": "supplier_admin", "password": "adminpassword123"},
        )
        token = login_res.data["data"]["access_token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        self.supplier = Supplier.objects.create(
            document_type=Supplier.DocumentType.NIT,
            document_number="800123456-7",
            business_name="Distribuidora Mayorista S.A.",
            email="ventas@mayorista.com",
            phone="6019876543",
        )

    def test_supplier_str(self):
        self.assertEqual(str(self.supplier), "Distribuidora Mayorista S.A.")

    def test_supplier_selector_get_by_id_include_deleted(self):
        self.supplier.delete()
        self.supplier.refresh_from_db()
        self.assertFalse(self.supplier.is_active)

        with self.assertRaises(Supplier.DoesNotExist):
            SupplierSelector.get_supplier_by_id(self.supplier.pk, include_deleted=False)

        found = SupplierSelector.get_supplier_by_id(self.supplier.pk, include_deleted=True)
        self.assertEqual(found.pk, self.supplier.pk)

    def test_supplier_service_restore(self):
        SupplierService.deactivate_supplier(self.supplier)
        self.supplier.refresh_from_db()
        self.assertFalse(self.supplier.is_active)

        SupplierService.restore_supplier(self.supplier)
        self.supplier.refresh_from_db()
        self.assertTrue(self.supplier.is_active)

    def test_api_list_and_create_supplier(self):
        url = reverse("suppliers-list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        payload = {
            "document_type": "NIT",
            "document_number": "811222333-4",
            "business_name": "Aceros del Norte",
            "email": "contacto@acerosdelnorte.com",
            "phone": "6045556677",
        }
        create_res = self.client.post(url, payload)
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_res.data["data"]["business_name"], "Aceros del Norte")

    def test_api_delete_and_restore_supplier(self):
        delete_url = reverse("suppliers-detail", kwargs={"pk": self.supplier.pk})
        restore_url = reverse("suppliers-restore", kwargs={"pk": self.supplier.pk})

        del_res = self.client.delete(delete_url)
        self.assertEqual(del_res.status_code, status.HTTP_200_OK)

        self.supplier.refresh_from_db()
        self.assertFalse(self.supplier.is_active)
        self.assertIsNotNone(self.supplier.deleted_at)

        rest_res = self.client.post(restore_url)
        self.assertEqual(rest_res.status_code, status.HTTP_200_OK)
        self.assertEqual(rest_res.data["code"], "SUPPLIER_RESTORED")

        self.supplier.refresh_from_db()
        self.assertTrue(self.supplier.is_active)
        self.assertIsNone(self.supplier.deleted_at)
