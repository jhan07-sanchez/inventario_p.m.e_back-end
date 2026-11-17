from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.company_info.models import CompanyInfo
from apps.subscriptions.models import Plan, Subscription
from apps.users.models import CompanyMembership, Role

User = get_user_model()


class TestSaaSAdminAPI(TestCase):
    """
    Pruebas integrales de endpoints REST para apps.saas_admin.
    Verifica contratos de respuesta de ApiResponse, paginación, filtros, acciones e impersonación.
    """

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.now = timezone.now()

        # Superadministrador
        self.superadmin = User.objects.create_superuser(
            username="saas_god",
            email="god@saas.com",
            password="Password123!",
            document_number="99000040",
        )
        self.client.force_authenticate(user=self.superadmin)

        # Dueño de empresa y roles
        self.owner = User.objects.create_user(
            username="company_owner",
            email="owner@client.com",
            password="Password123!",
            document_number="99000041",
            first_name="Carlos",
            last_name="Empresario",
        )
        self.role_admin = Role.objects.create(role_name="Admin", is_active=True)

        # Plan
        self.plan = Plan.objects.create(
            code="ENTERPRISE",
            name="Plan Enterprise",
            price=Decimal("199.99"),
            billing_cycle=Plan.BillingCycle.MONTHLY,
            is_active=True,
        )

        # Empresa
        self.company = CompanyInfo.objects.create(
            business_name="Soluciones Informáticas SAS",
            trade_name="SoluInfo",
            tax_id="901234567-8",
            email="contacto@soluinfo.com",
            phone="3001234567",
            status=CompanyInfo.CompanyStatus.ACTIVE,
            owner_user=self.owner,
        )
        self.membership = CompanyMembership.objects.create(
            user=self.owner,
            company=self.company,
            role=self.role_admin,
            is_owner=True,
            status=CompanyMembership.MembershipStatus.ACTIVE,
        )

        # Suscripción
        self.subscription = Subscription.objects.create(
            company=self.company,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
            start_date=self.now - timedelta(days=5),
            end_date=self.now + timedelta(days=25),
            is_active=True,
        )

    def test_list_tenants_endpoint(self):
        """GET /api/v1/saas-admin/tenants/ lista con formato paginado y datos enriquecidos."""
        response = self.client.get("/api/v1/saas-admin/tenants/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        resp_data = response.json()
        self.assertTrue(resp_data.get("success"))
        # Verifica la estructura de datos paginada
        data = resp_data.get("data", {})
        results = data.get("results", [])
        self.assertGreaterEqual(len(results), 1)

        first_tenant = results[0]
        self.assertEqual(first_tenant["id_company"], self.company.id_company)
        self.assertEqual(first_tenant["business_name"], self.company.business_name)
        self.assertEqual(first_tenant["status"], "ACTIVE")
        self.assertIsNotNone(first_tenant["owner"])
        self.assertEqual(first_tenant["owner"]["email"], self.owner.email)
        self.assertEqual(first_tenant["plan_name"], "Plan Enterprise")
        self.assertGreater(first_tenant["days_left"], 0)

    def test_list_tenants_filtering(self):
        """Filtros por search y status en el endpoint de listado."""
        # Búsqueda coincidente
        res_match = self.client.get("/api/v1/saas-admin/tenants/?search=SoluInfo")
        self.assertEqual(res_match.json()["data"]["count"], 1)

        # Búsqueda sin coincidencias
        res_empty = self.client.get(
            "/api/v1/saas-admin/tenants/?search=EmpresaInexistenteXYZ"
        )
        self.assertEqual(res_empty.json()["data"]["count"], 0)

        # Filtro por estado
        res_active = self.client.get("/api/v1/saas-admin/tenants/?status=ACTIVE")
        self.assertEqual(res_active.json()["data"]["count"], 1)

        res_suspended = self.client.get("/api/v1/saas-admin/tenants/?status=SUSPENDED")
        self.assertEqual(res_suspended.json()["data"]["count"], 0)

    def test_retrieve_tenant_detail_endpoint(self):
        """GET /api/v1/saas-admin/tenants/{id}/ retorna el detalle administrativo completo."""
        url = f"/api/v1/saas-admin/tenants/{self.company.id_company}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        resp_data = response.json()
        self.assertTrue(resp_data.get("success"))
        data = resp_data.get("data", {})
        self.assertEqual(data["company"]["id_company"], self.company.id_company)
        self.assertEqual(data["owner"]["email"], self.owner.email)
        self.assertIsNotNone(data["current_subscription"])
        self.assertEqual(data["active_members_count"], 1)

    def test_retrieve_tenant_not_found(self):
        """GET con ID inexistente retorna 404 / error estructurado."""
        response = self.client.get("/api/v1/saas-admin/tenants/999999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.json().get("success"))

    def test_global_metrics_endpoint(self):
        """GET /api/v1/saas-admin/tenants/metrics/ retorna KPIs globales y MRR."""
        response = self.client.get("/api/v1/saas-admin/tenants/metrics/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        resp_data = response.json()
        self.assertTrue(resp_data.get("success"))
        data = resp_data.get("data", {})
        self.assertIn("mrr", data)
        self.assertIn("total_companies", data)
        self.assertIn("active_companies", data)
        self.assertIn("active_trials", data)
        self.assertGreaterEqual(data["total_companies"], 1)

    def test_actions_suspend_and_reactivate(self):
        """POST /api/v1/saas-admin/tenants/{id}/actions/ ejecuta suspensión y reactivación."""
        url = f"/api/v1/saas-admin/tenants/{self.company.id_company}/actions/"

        # 1. Suspender
        res_suspend = self.client.post(
            url,
            {"action": "suspend", "reason": "Falta de pago de mensualidad"},
            format="json",
        )
        self.assertEqual(res_suspend.status_code, status.HTTP_200_OK)
        self.assertEqual(res_suspend.json()["data"]["status"], "SUSPENDED")

        # 2. Reactivar
        res_reactivate = self.client.post(
            url,
            {"action": "reactivate", "reason": "Comprobante de pago remitido"},
            format="json",
        )
        self.assertEqual(res_reactivate.status_code, status.HTTP_200_OK)
        self.assertEqual(res_reactivate.json()["data"]["status"], "ACTIVE")

    def test_actions_extend_trial(self):
        """POST /api/v1/saas-admin/tenants/{id}/actions/ extiende período de prueba."""
        url = f"/api/v1/saas-admin/tenants/{self.company.id_company}/actions/"
        response = self.client.post(
            url,
            {
                "action": "extend-trial",
                "reason": "Campaña de fidelización",
                "extra_days": 10,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("id_subscription", response.json()["data"])

    def test_actions_validation_error(self):
        """POST con acción inválida o falta de motivo retorna 400 Bad Request."""
        url = f"/api/v1/saas-admin/tenants/{self.company.id_company}/actions/"
        response = self.client.post(
            url,
            {"action": "extend-trial", "extra_days": 0, "reason": ""},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.json().get("success"))

    def test_impersonate_endpoint_success(self):
        """POST /api/v1/saas-admin/tenants/{id}/impersonate/ genera JWT temporal de soporte."""
        url = f"/api/v1/saas-admin/tenants/{self.company.id_company}/impersonate/"
        response = self.client.post(
            url,
            {"reason": "Investigación de reporte de soporte ticket #5021"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        resp_data = response.json()
        self.assertTrue(resp_data.get("success"))
        data = resp_data.get("data", {})
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "Bearer")
        self.assertEqual(data["expires_in"], 900)
        self.assertEqual(data["target_user"]["email"], self.owner.email)
        self.assertEqual(data["target_company"]["id_company"], self.company.id_company)

    def test_impersonate_validation_error_missing_reason(self):
        """Impersonación sin motivo explícito es rechazada con 400."""
        url = f"/api/v1/saas-admin/tenants/{self.company.id_company}/impersonate/"
        response = self.client.post(url, {"reason": ""}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
