from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.company_info.models import CompanyInfo
from apps.core.security.services import PermissionService
from apps.users.models import CompanyMembership, Role, User


class MultiTenantMembershipTests(TestCase):
    """
    Pruebas unitarias y de integración para membresías multiempresa,
    resolución de permisos por tenant y Middleware de contexto.
    """

    def setUp(self):
        cache.clear()
        self.client = APIClient()

        # Usuario multiempresa
        self.user = User.objects.create_user(
            username="multi_user",
            email="multi@example.com",
            password="Password123!",
            document_number="11223344",
        )

        # Empresa A y Empresa B
        self.company_a = CompanyInfo.objects.create(
            business_name="Empresa Alfa S.A.S.",
            trade_name="Alfa",
            tax_id="900111222-1",
            is_active=True,
        )

        self.company_b = CompanyInfo.objects.create(
            business_name="Empresa Beta Ltda.",
            trade_name="Beta",
            tax_id="900333444-2",
            is_active=True,
        )

        # Empresa C (a la que el usuario NO pertenece)
        self.company_c = CompanyInfo.objects.create(
            business_name="Empresa Gamma S.A.",
            trade_name="Gamma",
            tax_id="900555666-3",
            is_active=True,
        )

        # Rol de Administrador en Alfa
        self.role_admin = Role.objects.create(
            role_name="Admin_Alfa",
            permissions={
                "users.view": True,
                "users.create": True,
                "sales.view": True,
                "sales.create": True,
            },
            is_active=True,
        )

        # Rol de Cajero en Beta
        self.role_cashier = Role.objects.create(
            role_name="Cajero_Beta",
            permissions={
                "sales.view": True,
                "sales.create": True,
                "cash.view": True,
            },
            is_active=True,
        )

        # Membresía en Alfa (Admin y Propietario)
        self.membership_a = CompanyMembership.objects.create(
            user=self.user,
            company=self.company_a,
            role=self.role_admin,
            is_owner=True,
            status=CompanyMembership.MembershipStatus.ACTIVE,
            is_active=True,
        )

        # Membresía en Beta (Solo Cajero, No Propietario)
        self.membership_b = CompanyMembership.objects.create(
            user=self.user,
            company=self.company_b,
            role=self.role_cashier,
            is_owner=False,
            status=CompanyMembership.MembershipStatus.ACTIVE,
            is_active=True,
        )

        # Obtener token JWT
        login_res = self.client.post(
            reverse("auth-login"),
            {"username": "multi_user", "password": "Password123!"},
        )
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        self.token = login_res.data["data"]["access_token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def tearDown(self):
        cache.clear()

    def test_user_has_different_roles_and_permissions_per_company(self):
        # En Empresa Alfa: el usuario tiene users.view
        self.assertTrue(
            PermissionService.user_has_permission(
                user=self.user,
                permission_code="users.view",
                company_id=self.company_a.id_company,
            )
        )
        self.assertTrue(
            PermissionService.user_has_permission(
                user=self.user,
                permission_code="users.create",
                company_id=self.company_a.id_company,
            )
        )

        # En Empresa Beta: el usuario NO tiene users.view ni users.create
        self.assertFalse(
            PermissionService.user_has_permission(
                user=self.user,
                permission_code="users.view",
                company_id=self.company_b.id_company,
            )
        )
        self.assertFalse(
            PermissionService.user_has_permission(
                user=self.user,
                permission_code="users.create",
                company_id=self.company_b.id_company,
            )
        )

        # En ambas empresas tiene sales.create
        self.assertTrue(
            PermissionService.user_has_permission(
                user=self.user,
                permission_code="sales.create",
                company_id=self.company_a.id_company,
            )
        )
        self.assertTrue(
            PermissionService.user_has_permission(
                user=self.user,
                permission_code="sales.create",
                company_id=self.company_b.id_company,
            )
        )

    def test_permission_caches_are_strictly_isolated_by_tenant(self):
        # Cargar permisos en Alfa y en Beta
        perms_a = PermissionService.get_effective_permissions(
            self.user, company_id=self.company_a.id_company
        )
        perms_b = PermissionService.get_effective_permissions(
            self.user, company_id=self.company_b.id_company
        )

        key_a = f"user_permissions_{self.user.pk}_{self.company_a.id_company}"
        key_b = f"user_permissions_{self.user.pk}_{self.company_b.id_company}"

        self.assertIsNotNone(cache.get(key_a))
        self.assertIsNotNone(cache.get(key_b))

        self.assertTrue(cache.get(key_a)["users.view"])
        self.assertFalse(cache.get(key_b)["users.view"])

    def test_security_context_returns_active_company_and_all_user_companies(self):
        # Con encabezado X-Company-ID: company_a
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
            HTTP_X_COMPANY_ID=str(self.company_a.id_company),
        )

        res = self.client.get(reverse("security-context"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data["data"]

        # Validamos que se retorne la lista de empresas del usuario
        companies = data.get("companies", [])
        self.assertEqual(len(companies), 2)
        company_ids = [c["id_company"] for c in companies]
        self.assertIn(self.company_a.id_company, company_ids)
        self.assertIn(self.company_b.id_company, company_ids)
        self.assertNotIn(self.company_c.id_company, company_ids)

        # Validamos que la empresa activa sea Alfa
        active_company = data.get("active_company")
        self.assertIsNotNone(active_company)
        self.assertEqual(active_company["id_company"], self.company_a.id_company)

        # Validamos que en Alfa tenga rol Admin
        self.assertIn("Admin_Alfa", data["roles"])

    def test_switching_company_header_switches_security_context_and_roles(self):
        # Conmutar encabezado X-Company-ID: company_b
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
            HTTP_X_COMPANY_ID=str(self.company_b.id_company),
        )

        res = self.client.get(reverse("security-context"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data["data"]

        # Validamos que la empresa activa sea Beta
        active_company = data.get("active_company")
        self.assertIsNotNone(active_company)
        self.assertEqual(active_company["id_company"], self.company_b.id_company)

        # En Beta el rol es Cajero
        self.assertIn("Cajero_Beta", data["roles"])
        self.assertNotIn("Admin_Alfa", data["roles"])

    def test_tenant_middleware_blocks_access_to_unauthorized_company(self):
        # Intentar acceder a Empresa Gamma (a la cual NO pertenece)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
            HTTP_X_COMPANY_ID=str(self.company_c.id_company),
        )

        res = self.client.get(reverse("security-context"))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        res_data = res.json() if hasattr(res, "json") else res.data
        self.assertEqual(res_data.get("code"), "TENANT_ACCESS_DENIED")

    def test_superuser_can_access_any_company_context(self):
        superuser = User.objects.create_superuser(
            username="super_admin",
            email="super@example.com",
            password="SuperPassword123!",
            document_number="99001122",
        )
        login_res = self.client.post(
            reverse("auth-login"),
            {"username": "super_admin", "password": "SuperPassword123!"},
        )
        super_token = login_res.data["data"]["access_token"]

        # El superadmin puede seleccionar la Empresa Gamma sin pertenecer explícitamente a ella
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {super_token}",
            HTTP_X_COMPANY_ID=str(self.company_c.id_company),
        )

        res = self.client.get(reverse("security-context"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["data"]["active_company"]["id_company"], self.company_c.id_company)
