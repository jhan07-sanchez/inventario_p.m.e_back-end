from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.test import RequestFactory, TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.company_info.models import CompanyInfo
from apps.saas_admin.permissions import IsSaaSAdmin
from apps.users.models import CompanyMembership, Role

User = get_user_model()


class TestIsSaaSAdminPermission(TestCase):
    """
    Pruebas de seguridad para el permiso IsSaaSAdmin.
    Verifica que única y exclusivamente los superusuarios de la plataforma tengan acceso.
    """

    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()
        self.permission = IsSaaSAdmin()

        # 1. Superusuario global
        self.superuser = User.objects.create_superuser(
            username="superadmin",
            email="superadmin@saas.com",
            password="Password123!",
            document_number="99000001",
        )

        # 2. Usuario regular sin empresas
        self.regular_user = User.objects.create_user(
            username="regular_user",
            email="regular@test.com",
            password="Password123!",
            document_number="99000002",
        )

        # 3. Propietario / Administrador de empresa (no superusuario)
        self.tenant_owner = User.objects.create_user(
            username="tenant_owner",
            email="owner@tenant.com",
            password="Password123!",
            document_number="99000003",
        )
        self.role_admin = Role.objects.create(
            role_name="Admin",
            role_description="Administrador de Empresa",
            is_active=True,
        )
        self.company = CompanyInfo.objects.create(
            business_name="Empresa Cliente SAS",
            tax_id="900999888-1",
            owner_user=self.tenant_owner,
        )
        self.membership = CompanyMembership.objects.create(
            user=self.tenant_owner,
            company=self.company,
            role=self.role_admin,
            is_owner=True,
            status=CompanyMembership.MembershipStatus.ACTIVE,
        )

    def test_anonymous_user_is_denied(self):
        """Usuario no autenticado debe ser rechazado."""
        request = self.factory.get("/api/v1/saas-admin/tenants/")
        request.user = AnonymousUser()
        self.assertFalse(self.permission.has_permission(request, None))

    def test_regular_user_is_denied(self):
        """Usuario autenticado común sin superuser debe ser rechazado."""
        request = self.factory.get("/api/v1/saas-admin/tenants/")
        request.user = self.regular_user
        self.assertFalse(self.permission.has_permission(request, None))

    def test_tenant_owner_is_denied(self):
        """El propietario o administrador de un tenant NO debe tener acceso administrativo global."""
        request = self.factory.get("/api/v1/saas-admin/tenants/")
        request.user = self.tenant_owner
        self.assertFalse(self.permission.has_permission(request, None))

    def test_superuser_is_granted(self):
        """El superusuario global del SaaS debe tener acceso concedido."""
        request = self.factory.get("/api/v1/saas-admin/tenants/")
        request.user = self.superuser
        self.assertTrue(self.permission.has_permission(request, None))

    def test_api_endpoint_enforces_permission(self):
        """Verifica la respuesta HTTP real ante diferentes identidades."""
        client = APIClient()

        # Anónimo -> 401 Unauthorized
        response_anon = client.get("/api/v1/saas-admin/tenants/")
        self.assertIn(
            response_anon.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

        # Propietario de tenant -> 403 Forbidden
        client.force_authenticate(user=self.tenant_owner)
        response_owner = client.get("/api/v1/saas-admin/tenants/")
        self.assertEqual(response_owner.status_code, status.HTTP_403_FORBIDDEN)

        # Superadministrador -> 200 OK
        client.force_authenticate(user=self.superuser)
        response_super = client.get("/api/v1/saas-admin/tenants/")
        self.assertEqual(response_super.status_code, status.HTTP_200_OK)
