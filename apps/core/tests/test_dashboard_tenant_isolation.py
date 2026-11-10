from decimal import Decimal

from django.core.cache import cache as django_cache
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.categories.models import Category
from apps.company_info.models import CompanyInfo
from apps.core.security.services.dashboard_metrics_service import (
    DashboardMetricsService,
)
from apps.customers.models import Customer
from apps.inventory.models import Inventory
from apps.products.models import Product
from apps.sales.models.sale import Sale
from apps.users.models import CompanyMembership, Role, User
from apps.users.views.security_view import SecurityDashboardView


class DashboardTenantIsolationTests(TestCase):
    """
    Pruebas exhaustivas para verificar el aislamiento estricto multi-tenant del Dashboard
    y la prevención de envenenamiento de caché (Cache Poisoning) entre empresas.
    """

    def setUp(self):
        django_cache.clear()
        self.factory = APIRequestFactory()

        # 1. Crear Empresa A y Empresa B
        self.company_a = CompanyInfo.objects.create(
            business_name="Empresa A SAS",
            trade_name="Empresa A",
            tax_id="NIT-111-A",
            is_active=True,
        )
        self.company_b = CompanyInfo.objects.create(
            business_name="Empresa B Ltda",
            trade_name="Empresa B",
            tax_id="NIT-222-B",
            is_active=True,
        )

        # 2. Roles y usuarios asociados a cada empresa
        self.role_admin = Role.objects.create(
            role_name="Administrador A",
            role_description="Admin Empresa A",
        )
        self.user_a = User.objects.create_user(
            username="user_a",
            email="usera@test.com",
            password="Password123!",
            document_number="DOC-A-01",
        )
        CompanyMembership.objects.create(
            user=self.user_a,
            company=self.company_a,
            role=self.role_admin,
            is_owner=True,
            is_active=True,
        )

        self.user_b = User.objects.create_user(
            username="user_b",
            email="userb@test.com",
            password="Password123!",
            document_number="DOC-B-01",
        )
        CompanyMembership.objects.create(
            user=self.user_b,
            company=self.company_b,
            role=self.role_admin,
            is_owner=True,
            is_active=True,
        )

        # 3. Categoría y producto sólo en Empresa A
        self.category_a = Category.objects.create(
            name="Categoría A",
            company=self.company_a,
        )
        self.product_a = Product.objects.create(
            company=self.company_a,
            code="PRD-A-001",
            name="Producto A",
            category=self.category_a,
            purchase_price=Decimal("100.00"),
            sale_price=Decimal("150.00"),
            unit="UND",
        )
        self.inventory_a = Inventory.objects.create(
            product=self.product_a,
            current_stock=Decimal("20.00"),
            minimum_stock=Decimal("5.00"),
            maximum_stock=Decimal("50.00"),
            is_active=True,
        )

        # 4. Cliente sólo en Empresa A
        self.customer_a = Customer.objects.create(
            company=self.company_a,
            document_type="CC",
            document_number="12345678",
            first_name="Cliente",
            last_name="A",
            is_active=True,
        )

        # 5. Venta sólo en Empresa A
        self.sale_a = Sale.objects.create(
            company=self.company_a,
            user=self.user_a,
            customer=self.customer_a,
            sale_number="VNT-000001",
            status=Sale.SaleStatus.COMPLETED,
            sale_type=Sale.SaleType.ADMIN,
            payment_method="CASH",
            subtotal=Decimal("150.00"),
            total=Decimal("150.00"),
        )

    def test_metrics_isolated_by_company(self):
        """Verifica que las métricas de la Empresa A no se mezclen con las de la Empresa B."""
        widgets = ["users_total", "customers_total", "products_total", "sales_summary"]

        metrics_a = DashboardMetricsService.get_metrics(
            widgets, company_id=self.company_a.id_company
        )
        metrics_b = DashboardMetricsService.get_metrics(
            widgets, company_id=self.company_b.id_company
        )

        dict_a = {m["code"]: m["value"] for m in metrics_a}
        dict_b = {m["code"]: m["value"] for m in metrics_b}

        # Empresa A debe tener 1 usuario, 1 cliente, 1 producto y 1 venta
        self.assertEqual(dict_a["users_total"], 1)
        self.assertEqual(dict_a["customers_total"], 1)
        self.assertEqual(dict_a["products_total"], 1)
        self.assertEqual(dict_a["sales_summary"]["total_month"], 150.0)
        self.assertEqual(dict_a["sales_summary"]["sales_today_count"], 1)

        # Empresa B debe tener 1 usuario (el suyo), 0 clientes, 0 productos y 0 ventas
        self.assertEqual(dict_b["users_total"], 1)
        self.assertEqual(dict_b["customers_total"], 0)
        self.assertEqual(dict_b["products_total"], 0)
        self.assertEqual(dict_b["sales_summary"]["total_month"], 0.0)
        self.assertEqual(dict_b["sales_summary"]["sales_today_count"], 0)

    def test_cache_keys_strictly_isolated_preventing_poisoning(self):
        """Verifica que las claves de caché se aíslen con el company_id."""
        cid_a = self.company_a.id_company
        cid_b = self.company_b.id_company

        # Consultar métricas de Empresa A
        DashboardMetricsService.get_metrics(["products_total"], company_id=cid_a)

        key_a = f"dashboard_metric_products_total_company_{cid_a}"
        key_b = f"dashboard_metric_products_total_company_{cid_b}"

        # Empresa A debe estar en caché con valor 1
        self.assertEqual(django_cache.get(key_a), 1)
        # Empresa B aún no debe tener valor en caché
        self.assertIsNone(django_cache.get(key_b))

        # Consultar métricas de Empresa B
        DashboardMetricsService.get_metrics(["products_total"], company_id=cid_b)

        # Ahora Empresa B está en caché con valor 0 sin alterar Empresa A
        self.assertEqual(django_cache.get(key_b), 0)
        self.assertEqual(django_cache.get(key_a), 1)

    def test_cache_invalidation_affects_only_target_company(self):
        """Verifica que invalidar el caché de la Empresa A no borre el de la Empresa B."""
        cid_a = self.company_a.id_company
        cid_b = self.company_b.id_company

        # Llenar caché para ambas empresas
        DashboardMetricsService.get_metrics(["sales_summary"], company_id=cid_a)
        DashboardMetricsService.get_metrics(["sales_summary"], company_id=cid_b)

        key_a = f"dashboard_metric_sales_summary_company_{cid_a}"
        key_b = f"dashboard_metric_sales_summary_company_{cid_b}"

        self.assertIsNotNone(django_cache.get(key_a))
        self.assertIsNotNone(django_cache.get(key_b))

        # Invalidar ventas de Empresa A
        DashboardMetricsService.invalidate_sales_cache(company_id=cid_a)

        # Clave de Empresa A debe estar borrada
        self.assertIsNone(django_cache.get(key_a))
        # Clave de Empresa B debe permanecer intacta
        self.assertIsNotNone(django_cache.get(key_b))

    def test_security_dashboard_view_tenant_isolation(self):
        """Verifica que el endpoint /api/v1/security/dashboard/ use el company_id del request."""
        view = SecurityDashboardView.as_view()

        # Request autenticado como user_a en company_a
        request_a = self.factory.get("/api/v1/security/dashboard/")
        force_authenticate(request_a, user=self.user_a)
        request_a.company_id = self.company_a.id_company
        response_a = view(request_a)

        self.assertEqual(response_a.status_code, 200)
        data_a = response_a.data.get("data", {})
        widgets_a = {w["code"]: w["value"] for w in data_a.get("widgets", [])}
        self.assertEqual(widgets_a.get("sales_summary", {}).get("total_month"), 150.0)

        # Request autenticado como user_b en company_b
        request_b = self.factory.get("/api/v1/security/dashboard/")
        force_authenticate(request_b, user=self.user_b)
        request_b.company_id = self.company_b.id_company
        response_b = view(request_b)

        self.assertEqual(response_b.status_code, 200)
        data_b = response_b.data.get("data", {})
        widgets_b = {w["code"]: w["value"] for w in data_b.get("widgets", [])}
        self.assertEqual(widgets_b.get("sales_summary", {}).get("total_month"), 0.0)
