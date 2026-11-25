from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.company_info.models import CompanyInfo
from apps.subscriptions.models import Plan
from apps.subscriptions.services.company_entitlement_service import (
    CompanyEntitlementService,
)
from apps.subscriptions.services.subscription_service import SubscriptionService
from apps.users.models import CompanyMembership, Role

User = get_user_model()


class CompanyEntitlementTestCase(TestCase):
    def setUp(self):
        # 1. Superuser SaaS
        self.superadmin = User.objects.create_superuser(
            username="super@saas.com",
            email="super@saas.com",
            password="SuperPassword123!",
            first_name="Super",
            last_name="Admin",
            document_number="99999999",
        )

        # 2. Regular Company Owner & Tenant
        self.owner = User.objects.create_user(
            username="owner@empresa.com",
            email="owner@empresa.com",
            password="OwnerPassword123!",
            first_name="Owner",
            last_name="Empresa",
            document_number="88888888",
        )
        self.company = CompanyInfo.objects.create(
            business_name="Empresa Comercial S.A.S.",
            trade_name="Comercial PME",
            tax_id="900555666-1",
            owner_user=self.owner,
        )

        # 3. Roles y Permisos completos para el usuario
        self.role_admin = Role.objects.create(
            role_name="ADMIN_EMPRESA",
            role_description="Administrador de Empresa",
            permissions={
                "inventory.view": True,
                "inventory.create": True,
                "products.view": True,
                "products.create": True,
                "sales.view": True,
                "sales.create": True,
                "finance.view": True,
                "finance.create": True,
                "users.view": True,
                "users.create": True,
            },
            is_active=True,
        )

        self.membership = CompanyMembership.objects.create(
            user=self.owner,
            company=self.company,
            role=self.role_admin,
            is_owner=True,
            status=CompanyMembership.MembershipStatus.ACTIVE,
        )

        # 4. Planes: Basic (solo inventario y ventas) y Full (todo)
        self.plan_basic = Plan.objects.create(
            code="BASIC_TEST",
            name="Plan Básico Test",
            price=Decimal("29.99"),
            billing_cycle=Plan.BillingCycle.MONTHLY,
            max_users=2,
            max_products=50,
            max_invoices_per_month=100,
            enabled_modules=["inventory", "sales"],  # Sin 'finance'
            is_active=True,
        )
        self.plan_full = Plan.objects.create(
            code="FULL_TEST",
            name="Plan Full Test",
            price=Decimal("99.99"),
            billing_cycle=Plan.BillingCycle.MONTHLY,
            max_users=10,
            max_products=1000,
            max_invoices_per_month=1000,
            enabled_modules=["inventory", "sales", "finance"],
            is_active=True,
        )

        self.client = APIClient()

    def test_catalog_endpoint_returns_registry_structure(self):
        """Verifica que los endpoints de catálogo retornen el catálogo dinámico con grupos y submódulos."""
        self.client.force_authenticate(user=self.superadmin)

        # Endpoint acción del ViewSet
        resp1 = self.client.get("/api/v1/saas-admin/plans/available-modules/")
        self.assertEqual(resp1.status_code, status.HTTP_200_OK)
        data1 = resp1.json()
        self.assertTrue(data1.get("success"))
        modules_catalog = data1.get("data", [])
        self.assertGreaterEqual(len(modules_catalog), 3)

        group_codes = [g["code"] for g in modules_catalog]
        self.assertIn("inventory", group_codes)
        self.assertIn("operations", group_codes)

        # Endpoint directo
        resp2 = self.client.get("/api/v1/saas-admin/modules/")
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)

    def test_catalog_endpoint_denies_non_saas_admin(self):
        """Verifica que un usuario sin privilegios de staff/superuser reciba 403 en el catálogo."""
        self.client.force_authenticate(user=self.owner)
        resp = self.client.get("/api/v1/saas-admin/plans/available-modules/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_plan_creation_rejects_unknown_module(self):
        """Verifica que la creación de un plan con módulos desconocidos sea rechazada con 400."""
        self.client.force_authenticate(user=self.superadmin)
        payload = {
            "code": "INVALID_PLAN",
            "name": "Plan Inválido",
            "price": 50.00,
            "billing_cycle": "MONTHLY",
            "max_users": 5,
            "max_products": 100,
            "max_invoices_per_month": 50,
            "enabled_modules": ["inventory", "modulo_inventado_xyz"],
            "is_active": True,
        }
        resp = self.client.post(
            "/api/v1/saas-admin/plans/", data=payload, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        data = resp.json()
        self.assertIn("enabled_modules", str(data))

    def test_plan_creation_canonicalizes_aliases_and_deduplicates(self):
        """Verifica que 'clients' se normalice a 'customers' y que se eliminen duplicados."""
        self.client.force_authenticate(user=self.superadmin)
        payload = {
            "code": "CANONICAL_PLAN",
            "name": "Plan Canónico",
            "price": 75.00,
            "billing_cycle": "MONTHLY",
            "max_users": 5,
            "max_products": 100,
            "max_invoices_per_month": 50,
            "enabled_modules": ["clients", "customers", "stock", "inventory"],
            "is_active": True,
        }
        resp = self.client.post(
            "/api/v1/saas-admin/plans/", data=payload, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        created_plan = Plan.objects.get(code="CANONICAL_PLAN")
        self.assertIn("customers", created_plan.enabled_modules)
        self.assertIn("inventory", created_plan.enabled_modules)
        self.assertNotIn("clients", created_plan.enabled_modules)
        self.assertNotIn("stock", created_plan.enabled_modules)
        self.assertEqual(
            len(created_plan.enabled_modules), len(set(created_plan.enabled_modules))
        )

    def test_company_entitlement_service_expands_and_caches(self):
        """Verifica que CompanyEntitlementService expanda grupos y cachee por empresa."""
        # Asignar plan básico
        SubscriptionService.assign_or_renew_plan(
            self.company, self.plan_basic, duration_days=30
        )

        # 1. Resolver módulos habilitados
        enabled = CompanyEntitlementService.get_company_enabled_modules(
            self.company.id_company
        )
        self.assertIn("sales", enabled)
        # El grupo 'inventory' debe haberse expandido a sus submódulos
        self.assertIn("inventory", enabled)
        self.assertIn("products", enabled)
        self.assertIn("categories", enabled)
        # 'finance' no está contratado
        self.assertNotIn("finance", enabled)

        # 2. Comprobar is_module_enabled
        self.assertTrue(
            CompanyEntitlementService.is_module_enabled(
                self.company.id_company, "sales"
            )
        )
        self.assertTrue(
            CompanyEntitlementService.is_module_enabled(
                self.company.id_company, "products"
            )
        )
        self.assertFalse(
            CompanyEntitlementService.is_module_enabled(
                self.company.id_company, "finance"
            )
        )

    def test_permission_service_filters_uncontracted_permissions(self):
        """Verifica que PermissionService filtre permisos de módulos no contratados."""
        SubscriptionService.assign_or_renew_plan(
            self.company, self.plan_basic, duration_days=30
        )

        # Obtener contexto de seguridad con el usuario
        self.client.force_authenticate(user=self.owner)
        self.client.defaults["HTTP_X_COMPANY_ID"] = str(self.company.id_company)

        resp = self.client.get("/api/v1/security/context/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        context_data = resp.json().get("data", {})

        permissions = context_data.get("permissions", {})
        # Permisos de ventas e inventario permitidos (formato anidado)
        self.assertTrue(permissions.get("sales", {}).get("view"))
        self.assertTrue(permissions.get("products", {}).get("view"))
        # Permiso de finanzas debe haber sido filtrado porque el plan Basic no lo incluye
        self.assertFalse(permissions.get("finance", {}).get("view", False))

        # El contexto debe incluir la lista de contracted_modules
        contracted = context_data.get("contracted_modules", [])
        self.assertIn("sales", contracted)
        self.assertIn("inventory", contracted)
        self.assertNotIn("finance", contracted)

    def test_subscription_middleware_blocks_uncontracted_module_request(self):
        """Verifica que una petición HTTP a una ruta de módulo no contratado sea rechazada con 403."""
        SubscriptionService.assign_or_renew_plan(
            self.company, self.plan_basic, duration_days=30
        )

        self.client.force_authenticate(user=self.owner)
        self.client.defaults["HTTP_X_COMPANY_ID"] = str(self.company.id_company)

        # Ruta de Finanzas (no contratada en Basic)
        resp = self.client.get("/api/v1/finance/accounts/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        data = resp.json()
        self.assertEqual(data.get("code"), "MODULE_NOT_IN_PLAN")

    def test_plan_upgrade_invalidates_cache_and_grants_access(self):
        """Verifica que al actualizar el plan a uno con 'finance', se invalide la caché y se conceda acceso."""
        sub = SubscriptionService.assign_or_renew_plan(
            self.company, self.plan_basic, duration_days=30
        )

        self.client.force_authenticate(user=self.owner)
        self.client.defaults["HTTP_X_COMPANY_ID"] = str(self.company.id_company)

        # 1. Bloqueado en Basic
        resp_before = self.client.get("/api/v1/finance/accounts/")
        self.assertEqual(resp_before.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Cambiar plan a Full
        sub.plan = self.plan_full
        sub.save()
        CompanyEntitlementService.invalidate_company(self.company.id_company)

        # 3. Acceso permitido ahora
        resp_after = self.client.get("/api/v1/finance/accounts/")
        self.assertNotEqual(resp_after.status_code, status.HTTP_403_FORBIDDEN)

    def test_subscription_middleware_fail_closed_on_unmapped_api_path(self):
        """Verifica que rutas /api/v1/ no mapeadas ni exentas retornen HTTP 500 (MODULE_MAPPING_ERROR)."""
        self.client.force_authenticate(user=self.owner)
        self.client.defaults["HTTP_X_COMPANY_ID"] = str(self.company.id_company)

        resp = self.client.get("/api/v1/unmapped_commercial_route/test/")
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        data = resp.json()
        self.assertFalse(data.get("success"))
        self.assertEqual(data.get("code"), "MODULE_MAPPING_ERROR")

    def test_subscription_middleware_allows_allowlisted_unmapped_paths(self):
        """Verifica que rutas de la lista blanca (ej. system, health, users) no activen MODULE_MAPPING_ERROR."""
        self.client.force_authenticate(user=self.owner)
        self.client.defaults["HTTP_X_COMPANY_ID"] = str(self.company.id_company)

        # /api/v1/system/ está en ALLOWLISTED_UNMAPPED_PATHS
        resp = self.client.get("/api/v1/system/")
        self.assertNotEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        if resp.status_code == 500:
            self.assertNotEqual(resp.json().get("code"), "MODULE_MAPPING_ERROR")

    @override_settings(TESTING=False)
    def test_entitlement_service_fail_closed_in_production_mode(self):
        """Verifica que en producción (TESTING=False), una empresa sin suscripción solo reciba módulos base."""
        from apps.company_info.models import CompanyInfo

        prod_company = CompanyInfo.objects.create(
            business_name="Empresa Sin Suscripcion Prod S.A.S.",
            trade_name="Sin Sub Prod",
            tax_id="900999888-1",
            phone="3009998888",
            address="Calle 100",
            owner_user=self.owner,
        )

        enabled = CompanyEntitlementService.get_company_enabled_modules(
            prod_company.id_company
        )
        self.assertEqual(enabled, {"dashboard"})
        self.assertFalse(
            CompanyEntitlementService.is_module_enabled(
                prod_company.id_company, "sales"
            )
        )
        self.assertFalse(
            CompanyEntitlementService.is_module_enabled(
                prod_company.id_company, "inventory"
            )
        )

    def test_superuser_bypasses_subscription_middleware_and_entitlements(self):
        """Verifica que un superusuario pueda consultar endpoints comerciales aun sin suscripción en la empresa."""
        self.client.force_authenticate(user=self.superadmin)
        self.client.defaults["HTTP_X_COMPANY_ID"] = str(self.company.id_company)

        # Sin plan asignado a self.company, el superadmin debe poder acceder
        resp = self.client.get("/api/v1/finance/accounts/")
        self.assertNotEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission_resolves_system_manage_releases_to_settings(self):
        """Verifica que system.manage_releases resuelva a 'settings' y no al módulo inexistente 'system'."""
        from apps.core.security.permissions import HasPermission

        # 1. Superusuario siempre tiene permiso, incluso con company_id
        perm = HasPermission("system.manage_releases")()
        request = type(
            "Req",
            (),
            {
                "user": self.superadmin,
                "company": self.company,
                "company_id": self.company.id_company,
            },
        )()
        self.assertTrue(perm.has_permission(request, None))

        # 2. Usuario normal con plan sin 'settings' es rechazado indicando el módulo 'settings'
        SubscriptionService.assign_or_renew_plan(
            self.company, self.plan_basic, duration_days=30
        )
        perm_user = HasPermission("system.manage_releases")()
        req_user = type(
            "Req",
            (),
            {
                "user": self.owner,
                "company": self.company,
                "company_id": self.company.id_company,
            },
        )()
        self.assertFalse(perm_user.has_permission(req_user, None))
        self.assertIn("settings", perm_user.message)
        self.assertNotIn("'system'", perm_user.message)
