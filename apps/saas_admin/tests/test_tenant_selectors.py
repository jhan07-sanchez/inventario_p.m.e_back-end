from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from apps.company_info.models import CompanyInfo
from apps.core.exceptions import TenantNotFoundException
from apps.saas_admin.selectors.saas_admin_selector import SaaSAdminSelector
from apps.subscriptions.models import Plan, Subscription, SubscriptionPayment
from apps.users.models import CompanyMembership, Role

User = get_user_model()


class TestTenantSelectors(TestCase):
    """
    Pruebas unitarias para SaaSAdminSelector:
    consultas optimizadas, filtros, detalle administrativo y cálculo normalizado de métricas/MRR.
    """

    def setUp(self):
        cache.clear()
        self.now = timezone.now()

        # Usuario dueño
        self.owner = User.objects.create_user(
            username="owner1",
            email="owner1@acme.com",
            password="Password123!",
            document_number="99000010",
            first_name="Juan",
            last_name="Perez",
        )

        # Planes
        self.plan_monthly = Plan.objects.create(
            code="MONTHLY_PRO",
            name="Plan Pro Mensual",
            price=Decimal("120.00"),
            billing_cycle=Plan.BillingCycle.MONTHLY,
            is_active=True,
        )
        self.plan_annual = Plan.objects.create(
            code="ANNUAL_CORP",
            name="Plan Corporativo Anual",
            price=Decimal("1200.00"),  # Normalizado: 1200 / 12 = 100.00/mes
            billing_cycle=Plan.BillingCycle.ANNUAL,
            is_active=True,
        )
        self.plan_trial = Plan.objects.create(
            code="TRIAL_FREE",
            name="Plan Prueba",
            price=Decimal("0.00"),
            billing_cycle=Plan.BillingCycle.MONTHLY,
            is_active=True,
        )

        # Empresa 1 (Activa, con suscripción mensual activa)
        self.comp1 = CompanyInfo.objects.create(
            business_name="Acme Corporation",
            trade_name="Acme",
            tax_id="900100100-1",
            email="contact@acme.com",
            status=CompanyInfo.CompanyStatus.ACTIVE,
            owner_user=self.owner,
        )
        self.sub1 = Subscription.objects.create(
            company=self.comp1,
            plan=self.plan_monthly,
            status=Subscription.Status.ACTIVE,
            start_date=self.now - timedelta(days=10),
            end_date=self.now + timedelta(days=20),
            is_active=True,
        )

        # Empresa 2 (Activa, con suscripción anual activa)
        self.comp2 = CompanyInfo.objects.create(
            business_name="Beta Global SAS",
            trade_name="BetaGlobal",
            tax_id="900200200-2",
            email="info@betaglobal.com",
            status=CompanyInfo.CompanyStatus.ACTIVE,
        )
        self.sub2 = Subscription.objects.create(
            company=self.comp2,
            plan=self.plan_annual,
            status=Subscription.Status.ACTIVE,
            start_date=self.now - timedelta(days=30),
            end_date=self.now + timedelta(days=335),
            is_active=True,
        )

        # Empresa 3 (En Trial gratuito)
        self.comp3 = CompanyInfo.objects.create(
            business_name="Gamma Startups",
            trade_name="Gamma",
            tax_id="900300300-3",
            email="hello@gamma.com",
            status=CompanyInfo.CompanyStatus.ACTIVE,
        )
        self.sub3 = Subscription.objects.create(
            company=self.comp3,
            plan=self.plan_trial,
            status=Subscription.Status.TRIAL,
            start_date=self.now - timedelta(days=5),
            end_date=self.now + timedelta(days=10),
            is_active=True,
        )

        # Empresa 4 (Suspendida, con suscripción expirada)
        self.comp4 = CompanyInfo.objects.create(
            business_name="Delta Services",
            trade_name="Delta",
            tax_id="900400400-4",
            email="ops@delta.com",
            status=CompanyInfo.CompanyStatus.SUSPENDED,
        )
        self.sub4 = Subscription.objects.create(
            company=self.comp4,
            plan=self.plan_monthly,
            status=Subscription.Status.EXPIRED,
            start_date=self.now - timedelta(days=60),
            end_date=self.now - timedelta(days=30),
            is_active=True,
        )

        # Pagos registrados
        SubscriptionPayment.objects.create(
            subscription=self.sub1,
            amount=Decimal("120.00"),
            status=SubscriptionPayment.PaymentStatus.APPROVED,
            payment_date=self.now,
        )
        SubscriptionPayment.objects.create(
            subscription=self.sub2,
            amount=Decimal("1200.00"),
            status=SubscriptionPayment.PaymentStatus.APPROVED,
            payment_date=self.now,
        )

    def test_get_all_tenants_unfiltered(self):
        """Retorna todas las empresas activas registradas."""
        qs = SaaSAdminSelector.get_all_tenants()
        self.assertEqual(qs.count(), 4)

    def test_get_all_tenants_search_filter(self):
        """Filtro de búsqueda por razón social, NIT o correo."""
        qs_name = SaaSAdminSelector.get_all_tenants(search="Acme")
        self.assertEqual(qs_name.count(), 1)
        self.assertEqual(qs_name.first().id_company, self.comp1.id_company)

        qs_tax = SaaSAdminSelector.get_all_tenants(search="900200200")
        self.assertEqual(qs_tax.count(), 1)
        self.assertEqual(qs_tax.first().id_company, self.comp2.id_company)

        qs_email = SaaSAdminSelector.get_all_tenants(search="gamma.com")
        self.assertEqual(qs_email.count(), 1)
        self.assertEqual(qs_email.first().id_company, self.comp3.id_company)

    def test_get_all_tenants_status_filter(self):
        """Filtro por estado de empresa (ACTIVE vs SUSPENDED)."""
        qs_active = SaaSAdminSelector.get_all_tenants(status="ACTIVE")
        self.assertEqual(qs_active.count(), 3)

        qs_suspended = SaaSAdminSelector.get_all_tenants(status="SUSPENDED")
        self.assertEqual(qs_suspended.count(), 1)
        self.assertEqual(qs_suspended.first().id_company, self.comp4.id_company)

    def test_get_all_tenants_plan_code_filter(self):
        """Filtro por código de plan contratado."""
        qs_pro = SaaSAdminSelector.get_all_tenants(plan_code="MONTHLY_PRO")
        # comp1 y comp4 tienen MONTHLY_PRO
        self.assertEqual(qs_pro.count(), 2)

    def test_get_all_tenants_subscription_status_filter(self):
        """Filtro por estado de suscripción."""
        qs_trial = SaaSAdminSelector.get_all_tenants(subscription_status="TRIAL")
        self.assertEqual(qs_trial.count(), 1)
        self.assertEqual(qs_trial.first().id_company, self.comp3.id_company)

    def test_get_tenant_detail_success(self):
        """Obtiene el detalle administrativo completo de una empresa."""
        role = Role.objects.create(role_name="Admin", is_active=True)
        CompanyMembership.objects.create(
            user=self.owner,
            company=self.comp1,
            role=role,
            is_active=True,
        )

        detail = SaaSAdminSelector.get_tenant_detail(self.comp1.id_company)

        self.assertEqual(detail["company"].id_company, self.comp1.id_company)
        self.assertIsNotNone(detail["current_subscription"])
        self.assertEqual(
            detail["current_subscription"].id_subscription, self.sub1.id_subscription
        )
        self.assertEqual(len(detail["recent_payments"]), 1)
        self.assertEqual(detail["active_members_count"], 1)

    def test_get_tenant_detail_not_found(self):
        """Lanza TenantNotFoundException si el ID no existe."""
        with self.assertRaises(TenantNotFoundException):
            SaaSAdminSelector.get_tenant_detail(999999)

    def test_get_global_metrics_calculation(self):
        """
        Verifica el cálculo de KPIs globales y normalización de MRR:
        - comp1: 120.00/mes -> 120.00
        - comp2: 1200.00/año -> 100.00/mes
        - comp3: Trial (0.00) -> Excluido de MRR
        - comp4: Expired -> Excluido de MRR
        MRR Esperado: 120.00 + 100.00 = 220.00
        """
        metrics = SaaSAdminSelector.get_global_metrics()

        self.assertEqual(metrics["total_companies"], 4)
        self.assertEqual(metrics["active_companies"], 3)
        self.assertEqual(metrics["suspended_companies"], 1)
        self.assertEqual(metrics["active_trials"], 1)
        self.assertEqual(metrics["active_paid_subscriptions"], 2)
        self.assertEqual(metrics["expired_subscriptions"], 1)

        # MRR normalizado
        self.assertEqual(metrics["mrr"], 220.00)

        # Recaudación
        self.assertEqual(metrics["current_month_revenue"], 1320.00)
        self.assertEqual(metrics["total_historical_revenue"], 1320.00)
