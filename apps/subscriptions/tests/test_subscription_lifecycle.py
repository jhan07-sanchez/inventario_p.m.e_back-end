"""
Pruebas integrales de ciclo de vida de suscripciones, expiración,
período de gracia, modo solo lectura, middleware y comando de expiración.
"""

from datetime import timedelta
from decimal import Decimal
import json

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.models.audit_log import AuditLog
from apps.company_info.models import CompanyInfo
from apps.core.middlewares.subscription_middleware import SubscriptionMiddleware
from apps.subscriptions.models import Plan, Subscription
from apps.subscriptions.selectors.subscription_selector import SubscriptionSelector
from apps.subscriptions.services.plan_limit_validator_service import PlanLimitValidatorService
from apps.subscriptions.services.subscription_contact_service import (
    SubscriptionContactService,
)
from apps.subscriptions.services.subscription_service import SubscriptionService
from apps.users.models import CompanyMembership, Role

User = get_user_model()


class SubscriptionLifecycleTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="test_owner@pme.com",
            email="test_owner@pme.com",
            password="Password123!",
            first_name="Owner",
            last_name="Test",
            document_number="1000000001",
        )
        self.role_admin = Role.objects.create(
            role_name="ADMIN",
            role_description="Administrador",
            is_active=True,
        )
        self.company = CompanyInfo.objects.create(
            business_name="Empresa Ciclo de Vida SAS",
            trade_name="Ciclo de Vida Test",
            tax_id="900999888-1",
            owner_user=self.user,
        )
        self.membership = CompanyMembership.objects.create(
            user=self.user,
            company=self.company,
            role=self.role_admin,
            is_owner=True,
            status=CompanyMembership.MembershipStatus.ACTIVE,
        )
        self.plan = Plan.objects.create(
            code="ENTERPRISE",
            name="Plan Enterprise",
            price=Decimal("199.99"),
            billing_cycle=Plan.BillingCycle.MONTHLY,
            max_users=20,
            max_products=5000,
            max_invoices_per_month=5000,
            enabled_modules=["inventory", "sales", "finance", "cash", "invoices"],
            is_active=True,
        )
        self.client = APIClient()
        self.rf = RequestFactory()

    # -------------------------------------------------------------------------
    # 1. Reglas de negocio del Modelo Subscription
    # -------------------------------------------------------------------------
    def test_trial_active_rules(self):
        """TRIAL activo dentro de fecha: can_write=True, is_in_grace_period=False."""
        now = timezone.now()
        sub = Subscription.objects.create(
            company=self.company,
            plan=self.plan,
            status=Subscription.Status.TRIAL,
            start_date=now - timedelta(days=5),
            end_date=now + timedelta(days=10),
            grace_period_days=0,
            is_active=True,
        )
        self.assertTrue(sub.is_valid)
        self.assertFalse(sub.is_expired)
        self.assertFalse(sub.is_in_grace_period)
        self.assertTrue(sub.can_write)
        self.assertFalse(sub.is_read_only)
        self.assertGreater(sub.days_remaining, 0)
        self.assertEqual(sub.days_overdue, 0)

    def test_trial_expired_has_no_grace_period(self):
        """TRIAL vencido NO tiene período de gracia: can_write=False, is_read_only=True."""
        now = timezone.now()
        sub = Subscription.objects.create(
            company=self.company,
            plan=self.plan,
            status=Subscription.Status.TRIAL,
            start_date=now - timedelta(days=20),
            end_date=now - timedelta(days=2),
            grace_period_days=5,  # Debe ser ignorado por regla de negocio para TRIAL
            is_active=True,
        )
        self.assertFalse(sub.is_valid)
        self.assertTrue(sub.is_expired)
        self.assertFalse(sub.is_in_grace_period)
        self.assertFalse(sub.can_write)
        self.assertTrue(sub.is_read_only)
        self.assertEqual(sub.days_remaining, 0)
        self.assertGreater(sub.days_overdue, 0)

    def test_active_subscription_within_grace_period(self):
        """ACTIVE dentro de días de gracia puede escribir pero is_in_grace_period=True."""
        now = timezone.now()
        sub = Subscription.objects.create(
            company=self.company,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
            start_date=now - timedelta(days=32),
            end_date=now - timedelta(days=2),
            grace_period_days=5,
            is_active=True,
        )
        self.assertTrue(sub.is_valid)
        self.assertFalse(sub.is_expired)
        self.assertTrue(sub.is_in_grace_period)
        self.assertTrue(sub.can_write)
        self.assertFalse(sub.is_read_only)
        self.assertEqual(sub.days_remaining, 0)
        self.assertGreater(sub.days_overdue, 0)

    def test_active_subscription_past_grace_period(self):
        """ACTIVE fuera del período de gracia está expirada y en modo solo lectura."""
        now = timezone.now()
        sub = Subscription.objects.create(
            company=self.company,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
            start_date=now - timedelta(days=40),
            end_date=now - timedelta(days=10),
            grace_period_days=5,
            is_active=True,
        )
        self.assertFalse(sub.is_valid)
        self.assertTrue(sub.is_expired)
        self.assertFalse(sub.is_in_grace_period)
        self.assertFalse(sub.can_write)
        self.assertTrue(sub.is_read_only)

    def test_past_due_within_and_past_grace(self):
        """PAST_DUE opera durante gracia; expira al agotarse."""
        now = timezone.now()
        sub_grace = Subscription.objects.create(
            company=self.company,
            plan=self.plan,
            status=Subscription.Status.PAST_DUE,
            start_date=now - timedelta(days=32),
            end_date=now - timedelta(days=2),
            grace_period_days=5,
            is_active=True,
        )
        self.assertTrue(sub_grace.is_in_grace_period)
        self.assertTrue(sub_grace.can_write)
        self.assertFalse(sub_grace.is_read_only)

        # Ahora vencida más allá de los 5 días de gracia
        sub_grace.end_date = now - timedelta(days=10)
        sub_grace.save()
        self.assertFalse(sub_grace.is_in_grace_period)
        self.assertFalse(sub_grace.can_write)
        self.assertTrue(sub_grace.is_read_only)

    # -------------------------------------------------------------------------
    # 2. SubscriptionMiddleware y Seguridad de Escritura
    # -------------------------------------------------------------------------
    def test_middleware_blocks_writes_when_read_only(self):
        """POST, PUT, PATCH, DELETE se bloquean con 403 y payload exacto."""
        now = timezone.now()
        Subscription.objects.create(
            company=self.company,
            plan=self.plan,
            status=Subscription.Status.TRIAL,
            start_date=now - timedelta(days=20),
            end_date=now - timedelta(days=1),
            grace_period_days=0,
            is_active=True,
        )

        middleware = SubscriptionMiddleware(lambda r: None)

        for http_method in ["post", "put", "patch", "delete"]:
            req_func = getattr(self.rf, http_method)
            req = req_func("/api/v1/categories/")
            req.company = self.company

            res = middleware(req)
            self.assertEqual(res.status_code, 403)

            body = json.loads(res.content.decode())
            self.assertFalse(body["success"])
            self.assertEqual(body["code"], "SUBSCRIPTION_EXPIRED")
            self.assertEqual(body["error_code"], "SUBSCRIPTION_EXPIRED")
            self.assertEqual(body["data"]["is_read_only"], True)
            self.assertEqual(body["data"]["can_write"], False)
            self.assertIn("contact_whatsapp", body["data"])
            self.assertIn("contact_email", body["data"])

    def test_middleware_allows_reads_and_exempt_endpoints(self):
        """GET y rutas de suscripción permitidas en modo solo lectura."""
        now = timezone.now()
        Subscription.objects.create(
            company=self.company,
            plan=self.plan,
            status=Subscription.Status.EXPIRED,
            start_date=now - timedelta(days=40),
            end_date=now - timedelta(days=10),
            grace_period_days=0,
            is_active=True,
        )

        middleware = SubscriptionMiddleware(lambda r: None)

        # GET permitido
        req_get = self.rf.get("/api/v1/categories/")
        req_get.company = self.company
        self.assertIsNone(middleware(req_get))

        # Status endpoint permitido
        req_status = self.rf.get("/api/v1/subscriptions/current/status/")
        req_status.company = self.company
        self.assertIsNone(middleware(req_status))

        # Cambio de plan permitido para permitir renovaciones
        req_change = self.rf.post("/api/v1/subscriptions/change-plan/")
        req_change.company = self.company
        self.assertIsNone(middleware(req_change))

    def test_service_layer_validate_can_write(self):
        """PlanLimitValidatorService.validate_can_write defiende a nivel de servicio."""
        now = timezone.now()
        Subscription.objects.create(
            company=self.company,
            plan=self.plan,
            status=Subscription.Status.EXPIRED,
            start_date=now - timedelta(days=40),
            end_date=now - timedelta(days=10),
            grace_period_days=0,
            is_active=True,
        )

        with self.assertRaises(Exception) as ctx:
            PlanLimitValidatorService.validate_can_write(self.company)
        self.assertIn("SUBSCRIPTION_EXPIRED", str(ctx.exception))

    # -------------------------------------------------------------------------
    # 3. Endpoint de Estado de Suscripción (/current/status/)
    # -------------------------------------------------------------------------
    def test_subscription_status_endpoint(self):
        """GET /api/v1/subscriptions/current/status/ devuelve estructura dinámica."""
        now = timezone.now()
        Subscription.objects.create(
            company=self.company,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
            start_date=now - timedelta(days=10),
            end_date=now + timedelta(days=20),
            grace_period_days=5,
            is_active=True,
        )

        self.client.force_authenticate(user=self.user)
        res = self.client.get(
            "/api/v1/subscriptions/current/status/",
            HTTP_X_COMPANY_ID=str(self.company.pk),
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()["data"]

        self.assertTrue(data["is_valid"])
        self.assertFalse(data["is_read_only"])
        self.assertTrue(data["can_write"])
        self.assertEqual(data["status"], "ACTIVE")
        self.assertEqual(data["plan_name"], self.plan.name)
        self.assertGreater(data["days_remaining"], 0)
        self.assertEqual(data["days_overdue"], 0)
        self.assertIn("contact_whatsapp", data)
        self.assertIn("contact_email", data)

    # -------------------------------------------------------------------------
    # 4. Management Command expire_subscriptions
    # -------------------------------------------------------------------------
    def test_expire_subscriptions_command(self):
        """El comando de expiración realiza transiciones atómicas, idempotentes y registra auditoría."""
        now = timezone.now()

        # Suscripción 1: TRIAL vencida -> debe pasar a EXPIRED
        sub_trial = Subscription.objects.create(
            company=self.company,
            plan=self.plan,
            status=Subscription.Status.TRIAL,
            start_date=now - timedelta(days=20),
            end_date=now - timedelta(days=2),
            grace_period_days=0,
            is_active=True,
        )

        # Crear segunda empresa para probar ACTIVE en gracia y ACTIVE vencida
        company_2 = CompanyInfo.objects.create(
            business_name="Empresa Dos SAS",
            trade_name="Dos Test",
            tax_id="900888777-2",
            owner_user=self.user,
        )
        # Suscripción 2: ACTIVE vencida fuera de gracia -> pasa a EXPIRED
        sub_active_expired = Subscription.objects.create(
            company=company_2,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
            start_date=now - timedelta(days=40),
            end_date=now - timedelta(days=10),
            grace_period_days=5,
            is_active=True,
        )

        # Crear tercera empresa para ACTIVE dentro de gracia
        company_3 = CompanyInfo.objects.create(
            business_name="Empresa Tres SAS",
            trade_name="Tres Test",
            tax_id="900777666-3",
            owner_user=self.user,
        )
        # Suscripción 3: ACTIVE vencida dentro de gracia -> pasa a PAST_DUE
        sub_active_grace = Subscription.objects.create(
            company=company_3,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
            start_date=now - timedelta(days=32),
            end_date=now - timedelta(days=2),
            grace_period_days=5,
            is_active=True,
        )

        # Ejecutar comando
        call_command("expire_subscriptions")

        sub_trial.refresh_from_db()
        sub_active_expired.refresh_from_db()
        sub_active_grace.refresh_from_db()

        self.assertEqual(sub_trial.status, Subscription.Status.EXPIRED)
        self.assertEqual(sub_active_expired.status, Subscription.Status.EXPIRED)
        self.assertEqual(sub_active_grace.status, Subscription.Status.PAST_DUE)

        # Verificar auditoría
        audit_logs = AuditLog.objects.filter(
            path="management/expire_subscriptions",
        )
        self.assertGreaterEqual(audit_logs.count(), 3)

        # Idempotencia: volver a ejecutar no debe fallar ni causar transiciones extra
        call_command("expire_subscriptions")
        sub_trial.refresh_from_db()
        self.assertEqual(sub_trial.status, Subscription.Status.EXPIRED)

    def test_expire_subscriptions_command_dry_run_leaves_db_untouched(self):
        """El flag --dry-run analiza y reporta sin modificar estados en BD ni registrar auditoría."""
        now = timezone.now()
        sub = Subscription.objects.create(
            company=self.company,
            plan=self.plan,
            status=Subscription.Status.TRIAL,
            start_date=now - timedelta(days=20),
            end_date=now - timedelta(days=3),
            grace_period_days=0,
            is_active=True,
        )

        initial_audit_count = AuditLog.objects.filter(
            path="management/expire_subscriptions"
        ).count()

        call_command("expire_subscriptions", dry_run=True)

        sub.refresh_from_db()
        self.assertEqual(sub.status, Subscription.Status.TRIAL)

        final_audit_count = AuditLog.objects.filter(
            path="management/expire_subscriptions"
        ).count()
        self.assertEqual(final_audit_count, initial_audit_count)

    # -------------------------------------------------------------------------
    # 5. Pruebas de Endurecimiento: SUBSCRIPTION_REQUIRED, Fail-Closed y Aislamiento
    # -------------------------------------------------------------------------
    def test_middleware_blocks_writes_when_subscription_does_not_exist(self):
        """Si la empresa no tiene suscripción alguna, el middleware bloquea con HTTP 403 y SUBSCRIPTION_REQUIRED."""
        Subscription.objects.filter(company=self.company).delete()

        middleware = SubscriptionMiddleware(lambda r: None)
        req = self.rf.post("/api/v1/categories/")
        req.company = self.company
        req.user = self.user

        res = middleware(req)
        self.assertEqual(res.status_code, 403)
        body = json.loads(res.content.decode())
        self.assertFalse(body["success"])
        self.assertEqual(body["code"], "SUBSCRIPTION_REQUIRED")
        self.assertEqual(body["error_code"], "SUBSCRIPTION_REQUIRED")
        self.assertEqual(body["data"]["status"], "NO_SUBSCRIPTION")
        self.assertTrue(body["data"]["is_read_only"])
        self.assertFalse(body["data"]["can_write"])

    def test_middleware_blocks_commercial_writes_when_company_context_is_missing(self):
        """Si falta el contexto de empresa (request.company is None) en una ruta comercial de escritura, aplica Fail-Closed 403 COMPANY_CONTEXT_REQUIRED."""
        middleware = SubscriptionMiddleware(lambda r: None)
        req = self.rf.post("/api/v1/categories/")
        req.company = None
        req.user = self.user

        res = middleware(req)
        self.assertEqual(res.status_code, 403)
        body = json.loads(res.content.decode())
        self.assertFalse(body["success"])
        self.assertEqual(body["code"], "COMPANY_CONTEXT_REQUIRED")
        self.assertEqual(body["error_code"], "COMPANY_CONTEXT_REQUIRED")
        self.assertEqual(body["data"]["status"], "NO_COMPANY")

    def test_saas_admin_staff_exemptions_and_restrictions(self):
        """Staff tiene acceso a rutas /api/v1/saas-admin/ pero NO puede evadir reglas comerciales del tenant."""
        staff_user = User.objects.create_user(
            username="staff_member@pme.com",
            email="staff_member@pme.com",
            password="Password123!",
            document_number="1000000002",
            is_staff=True,
            is_superuser=False,
        )

        middleware = SubscriptionMiddleware(lambda r: None)

        # 1. Ruta /api/v1/saas-admin/ está en EXEMPT_PREFIXES: pasa de inmediato
        req_saas = self.rf.post("/api/v1/saas-admin/tenants/")
        req_saas.user = staff_user
        req_saas.company = None
        self.assertIsNone(middleware(req_saas))

        # 2. Ruta comercial sin contexto de empresa: staff es bloqueado con COMPANY_CONTEXT_REQUIRED
        req_comm_no_comp = self.rf.post("/api/v1/categories/")
        req_comm_no_comp.user = staff_user
        req_comm_no_comp.company = None
        res_no_comp = middleware(req_comm_no_comp)
        self.assertEqual(res_no_comp.status_code, 403)
        self.assertEqual(
            json.loads(res_no_comp.content.decode())["code"],
            "COMPANY_CONTEXT_REQUIRED",
        )

        # 3. Ruta comercial con empresa cuya suscripción venció: staff también es bloqueado con SUBSCRIPTION_EXPIRED
        now = timezone.now()
        Subscription.objects.create(
            company=self.company,
            plan=self.plan,
            status=Subscription.Status.EXPIRED,
            start_date=now - timedelta(days=30),
            end_date=now - timedelta(days=5),
            grace_period_days=0,
            is_active=True,
        )
        req_comm_expired = self.rf.post("/api/v1/categories/")
        req_comm_expired.user = staff_user
        req_comm_expired.company = self.company
        res_expired = middleware(req_comm_expired)
        self.assertEqual(res_expired.status_code, 403)
        self.assertEqual(
            json.loads(res_expired.content.decode())["code"],
            "SUBSCRIPTION_EXPIRED",
        )

    def test_multi_company_switch_isolation(self):
        """Mismo usuario alternando entre Empresa A (vencida) y Empresa B (activa) mantiene estricto aislamiento."""
        now = timezone.now()
        company_b = CompanyInfo.objects.create(
            business_name="Empresa B Activa SAS",
            trade_name="Empresa B",
            tax_id="900555444-9",
            owner_user=self.user,
        )
        CompanyMembership.objects.create(
            user=self.user,
            company=company_b,
            role=self.role_admin,
            is_owner=True,
            status=CompanyMembership.MembershipStatus.ACTIVE,
        )

        # Empresa A: Vencida
        Subscription.objects.create(
            company=self.company,
            plan=self.plan,
            status=Subscription.Status.EXPIRED,
            start_date=now - timedelta(days=30),
            end_date=now - timedelta(days=5),
            grace_period_days=0,
            is_active=True,
        )
        # Empresa B: Activa
        Subscription.objects.create(
            company=company_b,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
            start_date=now - timedelta(days=5),
            end_date=now + timedelta(days=25),
            grace_period_days=5,
            is_active=True,
        )

        middleware = SubscriptionMiddleware(lambda r: None)

        # Petición para Empresa A (vencida) -> bloqueada
        req_a = self.rf.post("/api/v1/categories/")
        req_a.company = self.company
        req_a.user = self.user
        res_a = middleware(req_a)
        self.assertEqual(res_a.status_code, 403)
        self.assertEqual(
            json.loads(res_a.content.decode())["code"], "SUBSCRIPTION_EXPIRED"
        )

        # Petición para Empresa B (activa) -> permitida
        req_b = self.rf.post("/api/v1/categories/")
        req_b.company = company_b
        req_b.user = self.user
        res_b = middleware(req_b)
        self.assertIsNone(res_b)

    def test_cache_invalidation_via_signals(self):
        """post_save y post_delete en Subscription invalidan la caché de la empresa correspondiente."""
        now = timezone.now()
        sub = Subscription.objects.create(
            company=self.company,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
            start_date=now - timedelta(days=5),
            end_date=now + timedelta(days=25),
            grace_period_days=5,
            is_active=True,
        )

        # Primer acceso: llena la caché
        cached_sub_1 = SubscriptionSelector.get_current_subscription(self.company)
        self.assertEqual(cached_sub_1.status, Subscription.Status.ACTIVE)

        # Modificación directa con emisión y ejecución de on_commit
        with self.captureOnCommitCallbacks(execute=True):
            sub.status = Subscription.Status.CANCELLED
            sub.save()

        # Al invalidarse la caché, la siguiente consulta trae el nuevo estado CANCELLED
        cached_sub_2 = SubscriptionSelector.get_current_subscription(self.company)
        self.assertEqual(cached_sub_2.status, Subscription.Status.CANCELLED)

        # Eliminación con emisión y ejecución de on_commit
        with self.captureOnCommitCallbacks(execute=True):
            sub.delete()

        cached_sub_3 = SubscriptionSelector.get_current_subscription(self.company)
        self.assertIsNone(cached_sub_3)

    def test_middleware_blocks_cancelled_subscription(self):
        """Una suscripción CANCELLED no permite operaciones de escritura pero sí lecturas."""
        now = timezone.now()
        Subscription.objects.create(
            company=self.company,
            plan=self.plan,
            status=Subscription.Status.CANCELLED,
            start_date=now - timedelta(days=20),
            end_date=now + timedelta(days=10),
            grace_period_days=0,
            is_active=False,
        )

        middleware = SubscriptionMiddleware(lambda r: None)

        # Escritura bloqueada
        req_post = self.rf.post("/api/v1/categories/")
        req_post.company = self.company
        req_post.user = self.user
        res_post = middleware(req_post)
        self.assertEqual(res_post.status_code, 403)
        self.assertEqual(
            json.loads(res_post.content.decode())["code"], "SUBSCRIPTION_EXPIRED"
        )

        # Lectura permitida
        req_get = self.rf.get("/api/v1/categories/")
        req_get.company = self.company
        req_get.user = self.user
        self.assertIsNone(middleware(req_get))

    def test_contact_channels_generation_with_and_without_settings(self):
        """Verifica que contact_whatsapp y contact_email se generen correctamente según settings."""
        # 1. Con variables de configuración activas
        with self.settings(
            SUPPORT_WHATSAPP="573001234567",
            SUPPORT_EMAIL="ventas@inventariopme.com",
        ):
            wa, em = SubscriptionContactService.get_channels(self.company)
            self.assertIsNotNone(wa)
            self.assertIsNotNone(em)
            self.assertTrue(wa.startswith("https://wa.me/573001234567?text="))
            self.assertTrue(em.startswith("mailto:ventas@inventariopme.com?subject="))

            status_data = SubscriptionSelector.get_subscription_status(self.company)
            self.assertTrue(status_data["contact_whatsapp"].startswith("https://wa.me/573001234567?text="))
            self.assertTrue(status_data["contact_email"].startswith("mailto:ventas@inventariopme.com?subject="))

        # 2. Con variables vacías / ausentes -> deben retornar None
        with self.settings(
            SUPPORT_WHATSAPP="",
            SUPPORT_EMAIL="",
        ):
            wa_empty, em_empty = SubscriptionContactService.get_channels(self.company)
            self.assertIsNone(wa_empty)
            self.assertIsNone(em_empty)

    def test_status_endpoint_includes_contact_channels(self):
        """Valida que el endpoint /current/status/ incluya contact_whatsapp y contact_email según settings."""
        now = timezone.now()
        Subscription.objects.create(
            company=self.company,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
            start_date=now - timedelta(days=5),
            end_date=now + timedelta(days=25),
            grace_period_days=5,
            is_active=True,
        )

        self.client.force_authenticate(user=self.user)

        # 1. Con canales de contacto configurados (override_settings)
        with self.settings(
            SUPPORT_WHATSAPP="573001234567",
            SUPPORT_EMAIL="ventas@inventariopme.com",
        ):
            res = self.client.get(
                "/api/v1/subscriptions/current/status/",
                HTTP_X_COMPANY_ID=str(self.company.pk),
            )
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            print("\n--- [JSON RESPONSE GET /api/v1/subscriptions/current/status/]: ---")
            print(json.dumps(res.json(), indent=2, ensure_ascii=False))
            print("------------------------------------------------------------------\n")
            data = res.json()["data"]
            self.assertIsNotNone(data["contact_whatsapp"])
            self.assertIsNotNone(data["contact_email"])
            self.assertTrue(data["contact_whatsapp"].startswith("https://wa.me/"))
            self.assertTrue(data["contact_email"].startswith("mailto:"))

        # 2. Con canales vacíos -> deben ser None en el JSON
        with self.settings(
            SUPPORT_WHATSAPP="",
            SUPPORT_EMAIL="",
        ):
            res_empty = self.client.get(
                "/api/v1/subscriptions/current/status/",
                HTTP_X_COMPANY_ID=str(self.company.pk),
            )
            self.assertEqual(res_empty.status_code, status.HTTP_200_OK)
            data_empty = res_empty.json()["data"]
            self.assertIsNone(data_empty["contact_whatsapp"])
            self.assertIsNone(data_empty["contact_email"])
