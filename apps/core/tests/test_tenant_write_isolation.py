from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.categories.models import Category
from apps.company_info.models import CompanyInfo
from apps.customers.models import Customer
from apps.products.models import Product
from apps.suppliers.models import Supplier
from apps.users.models import CompanyMembership, Role, User, UserRole


class TenantWriteIsolationTests(TestCase):
    """
    Tests de aislamiento de escritura Multi-Tenant.
    Verifica que la inyección de company_id sea automática, transparente para el Frontend,
    y que bloquee vulnerabilidades de Mass Assignment e IDOR.
    """

    def setUp(self):
        self.client = APIClient()

        # Empresas
        self.company_1 = CompanyInfo.objects.create(
            business_name="Empresa A",
            tax_id="11111111-1",
            is_active=True,
        )
        self.company_2 = CompanyInfo.objects.create(
            business_name="Empresa B",
            tax_id="22222222-2",
            is_active=True,
        )

        # Usuario multiempresa
        self.user = User.objects.create_user(
            username="tenant_operator",
            password="password123",
            email="operator@test.com",
            document_number="77889900",
        )

        # Rol con permisos amplios
        self.role = Role.objects.create(
            role_name="operator_role",
            permissions={
                "categories.view": True,
                "categories.create": True,
                "categories.update": True,
                "categories.delete": True,
                "products.view": True,
                "products.create": True,
                "products.update": True,
                "customers.view": True,
                "customers.create": True,
                "customers.update": True,
                "suppliers.view": True,
                "suppliers.create": True,
                "suppliers.update": True,
            },
        )
        UserRole.objects.create(user=self.user, role=self.role)

        # Membresías activas en ambas empresas (para requerir header explícito)
        self.membership_1 = CompanyMembership.objects.create(
            user=self.user,
            company=self.company_1,
            role=self.role,
            is_active=True,
        )
        self.membership_2 = CompanyMembership.objects.create(
            user=self.user,
            company=self.company_2,
            role=self.role,
            is_active=True,
        )

        # Autenticación JWT
        login_res = self.client.post(
            reverse("auth-login"),
            {"username": "tenant_operator", "password": "password123"},
        )
        token = login_res.data["data"]["access_token"]
        self.token = token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_post_auto_injects_company_id_without_frontend_sending_it(self):
        """
        El Frontend NO envía company_id en el payload.
        El backend debe inyectar automáticamente company_id de la empresa activa (Empresa A).
        """
        url = reverse("categories-list")
        payload = {
            "name": "Bebidas",
            "description": "Categoría de bebidas",
        }
        res = self.client.post(
            url,
            data=payload,
            format="json",
            HTTP_X_COMPANY_ID=str(self.company_1.pk),
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        cat_id = res.data["data"]["id_category"]

        # Verificar directamente en BD
        category = Category.objects.get(pk=cat_id)
        self.assertEqual(category.company_id, self.company_1.pk)
        self.assertEqual(category.name, "Bebidas")

    def test_post_blocks_mass_assignment_injection(self):
        """
        Un atacante intenta inyectar 'company': 2 o 'company_id': 2 en el JSON
        mientras opera con el header de Empresa 1.
        El backend debe ignorar el payload malicioso y persistir en Empresa 1.
        """
        url = reverse("categories-list")
        payload = {
            "name": "Snacks",
            "description": "Intento de Mass Assignment",
            "company": self.company_2.pk,
            "company_id": self.company_2.pk,
        }
        res = self.client.post(
            url,
            data=payload,
            format="json",
            HTTP_X_COMPANY_ID=str(self.company_1.pk),
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        cat_id = res.data["data"]["id_category"]

        category = Category.objects.get(pk=cat_id)
        # Debe pertenecer estrictamente a la empresa activa en el header, no a la inyectada
        self.assertEqual(category.company_id, self.company_1.pk)
        self.assertNotEqual(category.company_id, self.company_2.pk)

    def test_put_prevents_idor_changing_company_id(self):
        """
        Una actualización (PUT/PATCH) no debe permitir transferir un registro a otra empresa.
        """
        cat = Category.objects.create(
            name="Lácteos",
            company=self.company_1,
            is_active=True,
        )

        url = reverse("categories-detail", kwargs={"pk": cat.pk})
        payload = {
            "name": "Lácteos Modificados",
            "company": self.company_2.pk,
            "company_id": self.company_2.pk,
        }
        res = self.client.put(
            url,
            data=payload,
            format="json",
            HTTP_X_COMPANY_ID=str(self.company_1.pk),
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        cat.refresh_from_db()
        self.assertEqual(cat.name, "Lácteos Modificados")
        # El company_id se mantiene inviolable
        self.assertEqual(cat.company_id, self.company_1.pk)

    def test_post_without_company_header_raises_permission_denied_for_multi_tenant_user(self):
        """
        Si un usuario que pertenece a varias empresas intenta crear un recurso
        sin especificar X-Company-ID, debe ser rechazado con 403 Forbidden.
        """
        url = reverse("categories-list")
        payload = {
            "name": "Categoría Sin Header",
        }
        res = self.client.post(
            url,
            data=payload,
            format="json",
            # Sin HTTP_X_COMPANY_ID
        )

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_cross_tenant_relational_integrity_in_products(self):
        """
        Verifica que no se pueda asociar una categoría de la Empresa B a un producto de la Empresa A.
        """
        cat_company_b = Category.objects.create(
            name="Categoría Empresa B",
            company=self.company_2,
            is_active=True,
        )

        url = reverse("products-list")
        payload = {
            "code": "PROD-CROSS-01",
            "name": "Producto Cross Tenant",
            "category": cat_company_b.pk,
            "purchase_price": "10.00",
            "sale_price": "20.00",
            "unit": "UNIT",
        }

        res = self.client.post(
            url,
            data=payload,
            format="json",
            HTTP_X_COMPANY_ID=str(self.company_1.pk),
        )

        # Debe rechazar con error de validación relacional cross-tenant
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Product.objects.filter(code="PROD-CROSS-01").exists())

    def test_customer_creation_auto_injects_company_id(self):
        """
        Al registrar un cliente sin company_id en el payload,
        se debe guardar con la empresa del header X-Company-ID.
        """
        url = reverse("customers-list")
        payload = {
            "document_type": "NIT",
            "document_number": "901234567-8",
            "business_name": "Cliente Empresa A S.A.S.",
            "email": "contacto@cliente-a.com",
            "phone": "3001234567",
        }
        res = self.client.post(
            url,
            data=payload,
            format="json",
            HTTP_X_COMPANY_ID=str(self.company_1.pk),
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        cust_id = res.data["data"]["id_customer"]
        customer = Customer.objects.get(pk=cust_id)
        self.assertEqual(customer.company_id, self.company_1.pk)

    def test_supplier_creation_auto_injects_company_id(self):
        """
        Al registrar un proveedor sin company_id en el payload,
        se debe guardar con la empresa del header X-Company-ID.
        """
        url = reverse("suppliers-list")
        payload = {
            "document_type": "NIT",
            "document_number": "800987654-3",
            "business_name": "Proveedor Insumos A",
            "email": "ventas@proveedor-a.com",
            "phone": "6017654321",
        }
        res = self.client.post(
            url,
            data=payload,
            format="json",
            HTTP_X_COMPANY_ID=str(self.company_1.pk),
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        supp_id = res.data["data"]["id_supplier"]
        supplier = Supplier.objects.get(pk=supp_id)
        self.assertEqual(supplier.company_id, self.company_1.pk)
