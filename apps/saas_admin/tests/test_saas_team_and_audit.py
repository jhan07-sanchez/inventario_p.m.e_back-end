from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.models.audit_log import AuditLog
from apps.saas_admin.services.team_service import SaaSTeamService

User = get_user_model()


class SaaSTeamAndAuditAPITestCase(TestCase):
    """
    Pruebas de endpoints para gestión del equipo interno SaaS y auditoría global.
    """

    def setUp(self):
        cache.clear()
        self.client = APIClient()

        # 1. Superadministrador (Owner)
        self.superadmin = User.objects.create_superuser(
            username="saas_owner",
            email="owner@saas.com",
            password="Password123!",
            document_number="1110001",
        )

        # 2. Miembro de soporte
        self.support_user = User.objects.create_user(
            username="tech_support",
            email="support@saas.com",
            password="Password123!",
            document_number="1110002",
            is_staff=True,
            is_superuser=False,
        )

        # 3. Usuario cliente regular (empresa)
        self.client_user = User.objects.create_user(
            username="client_user",
            email="client@tenant.com",
            password="Password123!",
            document_number="1110003",
            is_staff=False,
            is_superuser=False,
        )

    def test_list_team_as_superadmin(self):
        """El Superadministrador puede listar los miembros del equipo."""
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.get("/api/v1/saas-admin/team/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        resp_data = response.json()
        self.assertTrue(resp_data["success"])
        results = resp_data["data"]["results"]
        # Debe incluir a superadmin y support_user pero NO a client_user
        usernames = [u["username"] for u in results]
        self.assertIn("saas_owner", usernames)
        self.assertIn("tech_support", usernames)
        self.assertNotIn("client_user", usernames)

    def test_list_team_forbidden_for_regular_staff(self):
        """Un usuario staff sin superuser NO puede administrar el equipo."""
        self.client.force_authenticate(user=self.support_user)
        response = self.client.get("/api/v1/saas-admin/team/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_team_member_support(self):
        """Crear un integrante con perfil SUPPORT."""
        self.client.force_authenticate(user=self.superadmin)
        payload = {
            "username": "new_support_agent",
            "email": "agent@saas.com",
            "password": "SecurePassword123!",
            "first_name": "Agente",
            "last_name": "Soporte",
            "document_number": "1110004",
            "phone_number": "3001234567",
            "saas_profile": "SUPPORT",
        }
        response = self.client.post("/api/v1/saas-admin/team/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        resp_data = response.json()
        self.assertTrue(resp_data["success"])
        new_user = User.objects.get(username="new_support_agent")
        self.assertTrue(new_user.is_staff)
        self.assertFalse(new_user.is_superuser)

        # Verificar auditoría generada
        self.assertTrue(
            AuditLog.objects.filter(payload__security_event="SAAS_TEAM_MEMBER_CREATED").exists()
        )

    def test_toggle_team_member_status(self):
        """Activar y desactivar el acceso de un miembro del equipo."""
        self.client.force_authenticate(user=self.superadmin)
        url = f"/api/v1/saas-admin/team/{self.support_user.id_user}/toggle-status/"

        # Desactivar
        res_deact = self.client.post(url, {"is_active": False}, format="json")
        self.assertEqual(res_deact.status_code, status.HTTP_200_OK)
        self.support_user.refresh_from_db()
        self.assertFalse(self.support_user.is_active)

        # Reactivar
        res_act = self.client.post(url, {"is_active": True}, format="json")
        self.assertEqual(res_act.status_code, status.HTTP_200_OK)
        self.support_user.refresh_from_db()
        self.assertTrue(self.support_user.is_active)

    def test_cannot_deactivate_self(self):
        """El superadministrador no puede desactivar su propia cuenta."""
        self.client.force_authenticate(user=self.superadmin)
        url = f"/api/v1/saas-admin/team/{self.superadmin.id_user}/toggle-status/"
        response = self.client.post(url, {"is_active": False}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_roles_catalog(self):
        """Consulta del catálogo de perfiles disponibles."""
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.get("/api/v1/saas-admin/team/roles/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        codes = [r["code"] for r in response.json()["data"]]
        self.assertIn("SUPERADMIN", codes)
        self.assertIn("SUPPORT", codes)
        self.assertIn("SALES", codes)
        self.assertIn("FINANCE", codes)

    def test_global_audit_list(self):
        """Consulta del registro de auditoría global."""
        # Crear un log de auditoría
        AuditLog.objects.create(
            user=self.superadmin,
            method="POST",
            path="/api/v1/saas-admin/test/",
            status_code=200,
            payload={"event": "TEST_AUDIT"},
        )

        self.client.force_authenticate(user=self.superadmin)
        response = self.client.get("/api/v1/saas-admin/audit/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["success"])
        self.assertGreaterEqual(response.json()["data"]["count"], 1)

    def test_end_impersonate_action(self):
        """Finalizar sesión de impersonación."""
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.post("/api/v1/saas-admin/tenants/impersonate/end/", format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["success"])
        self.assertTrue(
            AuditLog.objects.filter(payload__security_event="SUPPORT_IMPERSONATION_ENDED").exists()
        )
