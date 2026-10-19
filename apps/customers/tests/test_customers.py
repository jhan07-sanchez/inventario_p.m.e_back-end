from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.customers.models.customer import Customer
from apps.customers.selectors.customer_selector import CustomerSelector
from apps.customers.services.customer_service import CustomerService
from apps.users.models import Role, User, UserRole


class CustomerTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="customer_admin",
            password="adminpassword123",
            email="cust_admin@example.com",
            document_number="11223344",
        )
        self.role = Role.objects.create(
            role_name="customer_manager",
            permissions={
                "customers.view": True,
                "customers.create": True,
                "customers.update": True,
                "customers.delete": True,
            },
        )
        UserRole.objects.create(user=self.user, role=self.role)

        login_res = self.client.post(
            reverse("auth-login"),
            {"username": "customer_admin", "password": "adminpassword123"},
        )
        token = login_res.data["data"]["access_token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        self.customer = Customer.objects.create(
            document_type=Customer.DocumentType.CC,
            document_number="10102020",
            first_name="Carlos",
            last_name="Rodríguez",
            email="carlos@example.com",
            phone="3001234567",
        )

    def test_customer_str_and_properties(self):
        self.assertEqual(str(self.customer), "Carlos Rodríguez")
        self.customer.business_name = "Comercializadora SAS"
        self.assertEqual(str(self.customer), "Comercializadora SAS")

    def test_customer_selector_get_by_id_include_deleted(self):
        self.customer.delete()
        self.customer.refresh_from_db()
        self.assertFalse(self.customer.is_active)

        with self.assertRaises(Customer.DoesNotExist):
            CustomerSelector.get_customer_by_id(self.customer.pk, include_deleted=False)

        found = CustomerSelector.get_customer_by_id(self.customer.pk, include_deleted=True)
        self.assertEqual(found.pk, self.customer.pk)

    def test_customer_service_restore(self):
        CustomerService.deactivate_customer(self.customer)
        self.customer.refresh_from_db()
        self.assertFalse(self.customer.is_active)

        CustomerService.restore_customer(self.customer)
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.is_active)

    def test_api_list_and_create_customer(self):
        url = reverse("customers-list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        payload = {
            "document_type": "NIT",
            "document_number": "900123456-1",
            "business_name": "Empresa ABC S.A.S.",
            "email": "contacto@empresaabc.com",
            "phone": "6011234567",
        }
        create_res = self.client.post(url, payload)
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_res.data["data"]["business_name"], "Empresa ABC S.A.S.")

    def test_api_delete_and_restore_customer(self):
        delete_url = reverse("customers-detail", kwargs={"pk": self.customer.pk})
        restore_url = reverse("customers-restore", kwargs={"pk": self.customer.pk})

        del_res = self.client.delete(delete_url)
        self.assertEqual(del_res.status_code, status.HTTP_200_OK)

        self.customer.refresh_from_db()
        self.assertFalse(self.customer.is_active)
        self.assertIsNotNone(self.customer.deleted_at)

        rest_res = self.client.post(restore_url)
        self.assertEqual(rest_res.status_code, status.HTTP_200_OK)
        self.assertEqual(rest_res.data["code"], "CUSTOMER_RESTORED")

        self.customer.refresh_from_db()
        self.assertTrue(self.customer.is_active)
        self.assertIsNone(self.customer.deleted_at)
