from datetime import timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.company_info.models import CompanyInfo
from apps.core.models.audit_log import AuditLog
from apps.subscriptions.models import Plan, Subscription
from apps.saas_admin.services.saas_plan_service import SaaSPlanService
from apps.saas_admin.services.saas_subscription_service import SaaSSubscriptionService

User = get_user_model()


class SaaSPlansAndSubscriptionsTests(TestCase):
    def setUp(self):
        # 1. Superadministrador del SaaS
        self.superadmin = User.objects.create_superuser(
            username="super@saas.com",
            email="super@saas.com",
            password="AdminPassword123!",
            first_name="Super",
            last_name="Admin",
            document_number="9990001",
        )

        # 2. Usuario regular sin privilegios
        self.regular_user = User.objects.create_user(
            username="regular@client.com",
            email="regular@client.com",
            password="UserPassword123!",
            document_number="9990002",
        )

        # 3. Empresa cliente
        self.company = CompanyInfo.objects.create(
            business_name="Empresa Test SAS",
            trade_name="Test SAS",
            tax_id="900999888-1",
            owner_user=self.regular_user,
            status=CompanyInfo.CompanyStatus.ACTIVE,
        )

        # 4. Planes iniciales
        self.plan_basic = Plan.objects.create(
            code="BASIC_TEST",
            name="Plan Básico Test",
            price=Decimal("49.99"),
            billing_cycle=Plan.BillingCycle.MONTHLY,
            max_users=2,
            max_products=50,
            max_invoices_per_month=100,
            enabled_modules=["inventory", "sales"],
            is_active=True,
        )

        self.plan_pro = Plan.objects.create(
            code="PRO_TEST",
            name="Plan Pro Test",
            price=Decimal("129.99"),
            billing_cycle=Plan.BillingCycle.MONTHLY,
            max_users=10,
            max_products=500,
            max_invoices_per_month=1000,
            enabled_modules=["inventory", "sales", "finance", "cash", "invoices"],
            is_active=True,
        )

        self.plan_inactive = Plan.objects.create(
            code="OLD_PLAN",
            name="Plan Antiguo Inactivo",
            price=Decimal("19.99"),
            billing_cycle=Plan.BillingCycle.MONTHLY,
            max_users=1,
            max_products=10,
            max_invoices_per_month=20,
            is_active=False,
        )

        self.client = APIClient()

    # ─────────────────────────────────────────────────────────────
    # Tests de Planes (SaaSPlanViewSet)
    # ─────────────────────────────────────────────────────────────

    def test_list_plans_as_saas_admin(self):
        """El SaaS Admin puede ver todos los planes, incluyendo los inactivos."""
        self.client.force_authenticate(user=self.superadmin)
        res = self.client.get("/api/v1/saas-admin/plans/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()["data"]
        codes = [p["code"] for p in data]
        self.assertIn("BASIC_TEST", codes)
        self.assertIn("PRO_TEST", codes)
        self.assertIn("OLD_PLAN", codes)  # El inactivo debe estar presente

    def test_non_admin_cannot_access_plans_api(self):
        """Un usuario sin privilegios es bloqueado con 403 Forbidden."""
        self.client.force_authenticate(user=self.regular_user)
        res = self.client.get("/api/v1/saas-admin/plans/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_plan_success(self):
        """El SaaS Admin puede crear un nuevo plan con límites y módulos."""
        self.client.force_authenticate(user=self.superadmin)
        payload = {
            "code": "ENTERPRISE_TEST",
            "name": "Plan Enterprise Test",
            "description": "Plan corporativo ilimitado",
            "price": "299.99",
            "billing_cycle": "ANNUAL",
            "max_users": 50,
            "max_products": 10000,
            "max_invoices_per_month": 5000,
            "enabled_modules": ["inventory", "sales", "finance", "cash", "invoices", "reports"],
            "is_active": True,
        }
        res = self.client.post("/api/v1/saas-admin/plans/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.json()["data"]
        self.assertEqual(data["code"], "ENTERPRISE_TEST")
        self.assertEqual(data["max_users"], 50)

        # Verificar auditoría
        audit = AuditLog.objects.filter(payload__security_event="CREATE_PLAN").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.payload["code"], "ENTERPRISE_TEST")

    def test_create_plan_duplicate_code_fails(self):
        """No se permite crear planes con código repetido."""
        self.client.force_authenticate(user=self.superadmin)
        payload = {
            "code": "BASIC_TEST",  # Ya existe
            "name": "Plan Duplicado",
            "price": "50.00",
        }
        res = self.client.post("/api/v1/saas-admin/plans/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_plan(self):
        """El SaaS Admin puede actualizar un plan comercial."""
        self.client.force_authenticate(user=self.superadmin)
        payload = {
            "name": "Plan Básico Mejorado",
            "price": "59.99",
            "max_products": 100,
        }
        res = self.client.patch(f"/api/v1/saas-admin/plans/{self.plan_basic.pk}/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.plan_basic.refresh_from_db()
        self.assertEqual(self.plan_basic.name, "Plan Básico Mejorado")
        self.assertEqual(self.plan_basic.price, Decimal("59.99"))
        self.assertEqual(self.plan_basic.max_products, 100)

    def test_toggle_plan_status(self):
        """El SaaS Admin puede alternar el estado activo/inactivo de un plan."""
        self.client.force_authenticate(user=self.superadmin)
        self.assertTrue(self.plan_basic.is_active)

        # Desactivar
        res = self.client.patch(f"/api/v1/saas-admin/plans/{self.plan_basic.pk}/toggle-status/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.plan_basic.refresh_from_db()
        self.assertFalse(self.plan_basic.is_active)

        # Reactivar
        res2 = self.client.patch(f"/api/v1/saas-admin/plans/{self.plan_basic.pk}/toggle-status/")
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.plan_basic.refresh_from_db()
        self.assertTrue(self.plan_basic.is_active)

    # ─────────────────────────────────────────────────────────────
    # Tests de Suscripciones (SaaSSubscriptionViewSet)
    # ─────────────────────────────────────────────────────────────

    def test_assign_subscription_to_company(self):
        """Asignación de una nueva suscripción a una empresa cliente."""
        self.client.force_authenticate(user=self.superadmin)
        payload = {
            "company_id": self.company.pk,
            "plan_id": self.plan_basic.pk,
            "duration_days": 60,
            "notes": "Asignación semestral de prueba acordada",
        }
        res = self.client.post("/api/v1/saas-admin/subscriptions/assign/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        sub_data = res.json()["data"]
        self.assertEqual(sub_data["company_id"], self.company.pk)
        self.assertEqual(sub_data["plan"]["code"], "BASIC_TEST")

        # Verificar auditoría
        audit = AuditLog.objects.filter(payload__security_event="ASSIGN_SUBSCRIPTION_PLAN").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.company, self.company)

    def test_change_plan_preserves_end_date(self):
        """Regla Crítica: El cambio de plan NO extiende la vigencia; preserva end_date."""
        # 1. Crear suscripción activa con 20 días de vigencia
        now = timezone.now()
        expected_end_date = now + timedelta(days=20)
        sub = Subscription.objects.create(
            company=self.company,
            plan=self.plan_basic,
            status=Subscription.Status.ACTIVE,
            start_date=now,
            end_date=expected_end_date,
        )

        self.client.force_authenticate(user=self.superadmin)
        payload = {
            "new_plan_id": self.plan_pro.pk,
            "reason": "Upgrade a Plan Pro por crecimiento de la empresa",
        }
        res = self.client.post(f"/api/v1/saas-admin/subscriptions/{sub.pk}/change-plan/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        sub.refresh_from_db()
        self.assertEqual(sub.plan.code, "PRO_TEST")
        # La fecha de fin se conserva idéntica (al segundo)
        self.assertEqual(sub.end_date.strftime("%Y-%m-%d %H:%M"), expected_end_date.strftime("%Y-%m-%d %H:%M"))

        # Verificar auditoría con detalle de plan anterior y nuevo
        audit = AuditLog.objects.filter(payload__security_event="CHANGE_SUBSCRIPTION_PLAN").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.payload["old_plan_code"], "BASIC_TEST")
        self.assertEqual(audit.payload["new_plan_code"], "PRO_TEST")

    def test_renew_subscription_extends_end_date(self):
        """Renovación de suscripción acumula los días sobre el vencimiento actual."""
        now = timezone.now()
        initial_end = now + timedelta(days=5)
        sub = Subscription.objects.create(
            company=self.company,
            plan=self.plan_basic,
            status=Subscription.Status.ACTIVE,
            start_date=now,
            end_date=initial_end,
        )

        self.client.force_authenticate(user=self.superadmin)
        payload = {
            "duration_days": 30,
            "reason": "Pago recibido por transferencia bancaria",
        }
        res = self.client.post(f"/api/v1/saas-admin/subscriptions/{sub.pk}/renew/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        sub.refresh_from_db()
        expected_new_end = initial_end + timedelta(days=30)
        self.assertEqual(sub.end_date.strftime("%Y-%m-%d %H:%M"), expected_new_end.strftime("%Y-%m-%d %H:%M"))

    def test_commercial_kpis(self):
        """Verifica el cálculo de KPIs comerciales."""
        self.client.force_authenticate(user=self.superadmin)
        res = self.client.get("/api/v1/saas-admin/subscriptions/kpis/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        kpis = res.json()["data"]
        self.assertIn("total_plans", kpis)
        self.assertIn("active_plans", kpis)
        self.assertIn("active_subscriptions", kpis)
        self.assertIn("expiring_soon", kpis)

    def test_company_quotas_endpoint(self):
        """Verifica la consulta en tiempo real de consumo y cuotas de una empresa."""
        Subscription.objects.create(
            company=self.company,
            plan=self.plan_basic,
            status=Subscription.Status.ACTIVE,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
        )

        self.client.force_authenticate(user=self.superadmin)
        res = self.client.get(f"/api/v1/saas-admin/subscriptions/company/{self.company.pk}/quotas/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()["data"]
        self.assertTrue(data["has_subscription"])
        self.assertIn("usage", data)
        self.assertIn("users", data["usage"])
        self.assertIn("products", data["usage"])
        self.assertIn("invoices", data["usage"])

    # ─────────────────────────────────────────────────────────────
    # Tests de Seguridad y Casos Límite (Auditoría Técnica)
    # ─────────────────────────────────────────────────────────────

    def test_unauthenticated_request_rejected_with_401(self):
        """Peticiones anónimas sin token JWT son rechazadas con 401."""
        self.client.logout()
        res_plans = self.client.get("/api/v1/saas-admin/plans/")
        self.assertEqual(res_plans.status_code, status.HTTP_401_UNAUTHORIZED)

        res_subs = self.client.get("/api/v1/saas-admin/subscriptions/")
        self.assertEqual(res_subs.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_tenant_user_blocked_with_403_on_all_saas_admin_endpoints(self):
        """Un usuario de empresa no puede acceder ni alterar suscripciones ni planes."""
        self.client.force_authenticate(user=self.regular_user)

        res_plans = self.client.get("/api/v1/saas-admin/plans/")
        self.assertEqual(res_plans.status_code, status.HTTP_403_FORBIDDEN)

        res_subs = self.client.get("/api/v1/saas-admin/subscriptions/")
        self.assertEqual(res_subs.status_code, status.HTTP_403_FORBIDDEN)

        res_quotas = self.client.get(f"/api/v1/saas-admin/subscriptions/company/{self.company.pk}/quotas/")
        self.assertEqual(res_quotas.status_code, status.HTTP_403_FORBIDDEN)

        res_assign = self.client.post("/api/v1/saas-admin/subscriptions/assign/", {}, format="json")
        self.assertEqual(res_assign.status_code, status.HTTP_403_FORBIDDEN)

    def test_assign_plan_cancels_previous_active_subscription(self):
        """
        Regla de negocio crítica: Si la empresa ya tiene una suscripción activa previa,
        la asignación de un nuevo plan cancela la anterior para evitar suscripciones activas concurrentes.
        """
        now = timezone.now()
        sub_old = Subscription.objects.create(
            company=self.company,
            plan=self.plan_basic,
            status=Subscription.Status.ACTIVE,
            start_date=now - timedelta(days=10),
            end_date=now + timedelta(days=20),
            notes="Suscripción previa",
        )

        self.client.force_authenticate(user=self.superadmin)
        payload = {
            "company_id": self.company.pk,
            "plan_id": self.plan_pro.pk,
            "duration_days": 30,
            "notes": "Nueva asignación que supera la anterior",
        }
        res = self.client.post("/api/v1/saas-admin/subscriptions/assign/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        sub_old.refresh_from_db()
        self.assertEqual(sub_old.status, Subscription.Status.CANCELLED)
        self.assertIn("Cancelada automáticamente", sub_old.notes)

        # La nueva suscripción debe estar activa
        new_sub_id = res.json()["data"]["id_subscription"]
        new_sub = Subscription.objects.get(id_subscription=new_sub_id)
        self.assertEqual(new_sub.status, Subscription.Status.ACTIVE)
        self.assertEqual(new_sub.plan, self.plan_pro)

        # La consulta de suscripciones activas de la empresa debe tener solo 1
        active_count = Subscription.objects.filter(
            company=self.company,
            status=Subscription.Status.ACTIVE,
            is_active=True,
        ).count()
        self.assertEqual(active_count, 1)

    def test_cannot_assign_inactive_plan(self):
        """No se puede asignar un plan inactivo a una empresa."""
        self.client.force_authenticate(user=self.superadmin)
        payload = {
            "company_id": self.company.pk,
            "plan_id": self.plan_inactive.pk,
            "duration_days": 30,
        }
        res = self.client.post("/api/v1/saas-admin/subscriptions/assign/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("desactivado", str(res.json()))

    def test_cannot_change_plan_to_inactive_plan(self):
        """No se puede cambiar el plan de una suscripción activa a un plan inactivo."""
        sub = Subscription.objects.create(
            company=self.company,
            plan=self.plan_basic,
            status=Subscription.Status.ACTIVE,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
        )

        self.client.force_authenticate(user=self.superadmin)
        payload = {
            "new_plan_id": self.plan_inactive.pk,
            "reason": "Intento de asignación de plan inactivo",
        }
        res = self.client.post(f"/api/v1/saas-admin/subscriptions/{sub.pk}/change-plan/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("inactivo", str(res.json()))

    def test_cannot_change_plan_on_expired_subscription(self):
        """No se puede cambiar el plan de una suscripción vencida sin antes renovarla."""
        now = timezone.now()
        sub_expired = Subscription.objects.create(
            company=self.company,
            plan=self.plan_basic,
            status=Subscription.Status.EXPIRED,
            start_date=now - timedelta(days=40),
            end_date=now - timedelta(days=10),
        )

        self.client.force_authenticate(user=self.superadmin)
        payload = {
            "new_plan_id": self.plan_pro.pk,
            "reason": "Intento de cambio en suscripción expirada",
        }
        res = self.client.post(f"/api/v1/saas-admin/subscriptions/{sub_expired.pk}/change-plan/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("vencida", str(res.json()).lower())

    def test_cannot_change_plan_on_cancelled_subscription(self):
        """No se puede cambiar el plan de una suscripción cancelada."""
        sub_cancelled = Subscription.objects.create(
            company=self.company,
            plan=self.plan_basic,
            status=Subscription.Status.CANCELLED,
            start_date=timezone.now() - timedelta(days=20),
            end_date=timezone.now() + timedelta(days=10),
        )

        self.client.force_authenticate(user=self.superadmin)
        payload = {
            "new_plan_id": self.plan_pro.pk,
            "reason": "Intento de cambio en suscripción cancelada",
        }
        res = self.client.post(f"/api/v1/saas-admin/subscriptions/{sub_cancelled.pk}/change-plan/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cancelada", str(res.json()).lower())

    def test_cannot_renew_cancelled_subscription(self):
        """No se puede renovar una suscripción cancelada; requiere nueva asignación."""
        sub_cancelled = Subscription.objects.create(
            company=self.company,
            plan=self.plan_basic,
            status=Subscription.Status.CANCELLED,
            start_date=timezone.now() - timedelta(days=20),
            end_date=timezone.now() + timedelta(days=10),
        )

        self.client.force_authenticate(user=self.superadmin)
        payload = {
            "duration_days": 30,
            "reason": "Intento de renovación de suscripción cancelada",
        }
        res = self.client.post(f"/api/v1/saas-admin/subscriptions/{sub_cancelled.pk}/renew/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cancelada", str(res.json()).lower())

    def test_renew_expired_subscription_extends_from_now(self):
        """
        Si la suscripción ya estaba vencida, la renovación suma los días a partir de 'hoy',
        no a partir de la fecha vieja vencida.
        """
        now = timezone.now()
        sub_expired = Subscription.objects.create(
            company=self.company,
            plan=self.plan_basic,
            status=Subscription.Status.EXPIRED,
            start_date=now - timedelta(days=60),
            end_date=now - timedelta(days=30),  # Venció hace 30 días
        )

        self.client.force_authenticate(user=self.superadmin)
        payload = {
            "duration_days": 30,
            "reason": "Reactivación y pago recibido tras vencimiento",
        }
        res = self.client.post(f"/api/v1/saas-admin/subscriptions/{sub_expired.pk}/renew/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        sub_expired.refresh_from_db()
        self.assertEqual(sub_expired.status, Subscription.Status.ACTIVE)
        # La nueva fecha debe ser aproximadamente now + 30 días (mayor que now + 29 días)
        self.assertGreater(sub_expired.end_date, now + timedelta(days=29))

    def test_renew_past_due_reactivates_suspended_company(self):
        """Si la empresa estaba suspendida por mora, la renovación de la suscripción la reactiva."""
        self.company.status = CompanyInfo.CompanyStatus.SUSPENDED
        self.company.save(update_fields=["status"])

        now = timezone.now()
        sub = Subscription.objects.create(
            company=self.company,
            plan=self.plan_basic,
            status=Subscription.Status.PAST_DUE,
            start_date=now - timedelta(days=35),
            end_date=now - timedelta(days=2),
        )

        self.client.force_authenticate(user=self.superadmin)
        payload = {
            "duration_days": 30,
            "reason": "Pago recibido y deuda saneada",
        }
        res = self.client.post(f"/api/v1/saas-admin/subscriptions/{sub.pk}/renew/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.company.refresh_from_db()
        self.assertEqual(self.company.status, CompanyInfo.CompanyStatus.ACTIVE)
        sub.refresh_from_db()
        self.assertEqual(sub.status, Subscription.Status.ACTIVE)
