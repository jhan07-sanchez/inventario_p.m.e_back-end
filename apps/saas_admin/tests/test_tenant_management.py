from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from apps.company_info.models import CompanyInfo
from apps.core.exceptions import (
    InvalidTenantActionException,
    SubscriptionNotFoundException,
    TenantNotFoundException,
)
from apps.core.models.audit_log import AuditLog
from apps.saas_admin.dto.tenant_action_dto import TenantActionDto
from apps.saas_admin.services.tenant_management_service import TenantManagementService
from apps.subscriptions.models import Plan, Subscription

User = get_user_model()


class TestTenantManagementService(TestCase):
    """
    Pruebas unitarias para las operaciones administrativas de TenantManagementService.
    Verifica consistencia transaccional, transiciones de estado y registro inmutable en AuditLog.
    """

    def setUp(self):
        cache.clear()
        self.now = timezone.now()

        self.admin_user = User.objects.create_superuser(
            username="super_admin",
            email="super@saas.com",
            password="Password123!",
            document_number="99000020",
        )

        self.company = CompanyInfo.objects.create(
            business_name="Empresa Operativa",
            tax_id="900555666-1",
            status=CompanyInfo.CompanyStatus.ACTIVE,
        )

        self.plan = Plan.objects.create(
            code="PLAN_BASIC",
            name="Plan Básico",
            price=Decimal("50.00"),
            billing_cycle=Plan.BillingCycle.MONTHLY,
            is_active=True,
        )

        self.subscription = Subscription.objects.create(
            company=self.company,
            plan=self.plan,
            status=Subscription.Status.TRIAL,
            start_date=self.now - timedelta(days=10),
            end_date=self.now + timedelta(days=5),
            is_active=True,
        )

    def test_suspend_company_success(self):
        """Suspende exitosamente una empresa activa y registra en auditoría."""
        updated = TenantManagementService.suspend_company(
            company_id=self.company.id_company,
            reason="Mora prolongada",
            actor_user=self.admin_user,
        )

        self.assertEqual(updated.status, CompanyInfo.CompanyStatus.SUSPENDED)
        self.company.refresh_from_db()
        self.assertEqual(self.company.status, CompanyInfo.CompanyStatus.SUSPENDED)

        # Verificar AuditLog
        log = AuditLog.objects.filter(company=self.company).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.payload.get("administrative_action"), "SUSPEND_TENANT")
        self.assertEqual(log.payload.get("reason"), "Mora prolongada")

    def test_suspend_already_suspended_company_fails(self):
        """Intentar suspender una empresa ya suspendida debe lanzar InvalidTenantActionException."""
        self.company.status = CompanyInfo.CompanyStatus.SUSPENDED
        self.company.save(update_fields=["status"])

        with self.assertRaises(InvalidTenantActionException):
            TenantManagementService.suspend_company(
                company_id=self.company.id_company,
                reason="Otra suspensión",
            )

    def test_reactivate_company_success(self):
        """Reactiva una empresa suspendida y registra en auditoría."""
        self.company.status = CompanyInfo.CompanyStatus.SUSPENDED
        self.company.save(update_fields=["status"])

        updated = TenantManagementService.reactivate_company(
            company_id=self.company.id_company,
            reason="Pago regularizado",
            actor_user=self.admin_user,
        )

        self.assertEqual(updated.status, CompanyInfo.CompanyStatus.ACTIVE)
        self.company.refresh_from_db()
        self.assertEqual(self.company.status, CompanyInfo.CompanyStatus.ACTIVE)

        log = AuditLog.objects.filter(company=self.company).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.payload.get("administrative_action"), "REACTIVATE_TENANT")

    def test_reactivate_already_active_company_fails(self):
        """Intentar reactivar una empresa activa debe fallar."""
        with self.assertRaises(InvalidTenantActionException):
            TenantManagementService.reactivate_company(
                company_id=self.company.id_company,
                reason="Reactivar activa",
            )

    def test_extend_trial_success(self):
        """Extiende el período de prueba sumando días a la fecha de fin."""
        original_end = self.subscription.end_date
        sub = TenantManagementService.extend_trial(
            company_id=self.company.id_company,
            extra_days=15,
            reason="Solicitud comercial de extensión",
            actor_user=self.admin_user,
        )

        self.assertEqual(sub.end_date, original_end + timedelta(days=15))
        self.assertIn("Solicitud comercial de extensión", sub.notes)

        log = AuditLog.objects.filter(company=self.company).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.payload.get("administrative_action"), "EXTEND_TRIAL")
        self.assertEqual(log.payload.get("details", {}).get("extra_days"), 15)

    def test_extend_trial_reactivates_expired_subscription_and_suspended_company(self):
        """Extender prueba a una empresa suspendida con suscripción expirada la reactiva automáticamente."""
        self.company.status = CompanyInfo.CompanyStatus.SUSPENDED
        self.company.save(update_fields=["status"])

        self.subscription.status = Subscription.Status.EXPIRED
        self.subscription.end_date = self.now - timedelta(days=2)
        self.subscription.save(update_fields=["status", "end_date"])

        sub = TenantManagementService.extend_trial(
            company_id=self.company.id_company,
            extra_days=10,
            reason="Segunda oportunidad de prueba",
            actor_user=self.admin_user,
        )

        self.assertEqual(sub.status, Subscription.Status.TRIAL)
        self.company.refresh_from_db()
        self.assertEqual(self.company.status, CompanyInfo.CompanyStatus.ACTIVE)

    def test_extend_trial_invalid_days_fails(self):
        """Días menores o iguales a cero deben fallar."""
        with self.assertRaises(InvalidTenantActionException):
            TenantManagementService.extend_trial(
                company_id=self.company.id_company,
                extra_days=0,
            )

    def test_extend_trial_no_subscription_fails(self):
        """Empresa sin suscripción lanza SubscriptionNotFoundException."""
        empty_comp = CompanyInfo.objects.create(
            business_name="Empresa Sin Sub",
            tax_id="900888777-1",
        )
        with self.assertRaises(SubscriptionNotFoundException):
            TenantManagementService.extend_trial(
                company_id=empty_comp.id_company,
                extra_days=10,
            )

    def test_nonexistent_company_fails(self):
        """Acciones sobre empresa inexistente lanzan TenantNotFoundException."""
        with self.assertRaises(TenantNotFoundException):
            TenantManagementService.suspend_company(company_id=999999)

    def test_execute_action_dispatcher(self):
        """Verifica el enrutamiento correcto mediante TenantActionDto."""
        dto_suspend = TenantActionDto(action="suspend", reason="Test suspend")
        result = TenantManagementService.execute_action(
            company_id=self.company.id_company,
            dto=dto_suspend,
            actor_user=self.admin_user,
        )
        self.assertEqual(result.status, CompanyInfo.CompanyStatus.SUSPENDED)

        dto_reactivate = TenantActionDto(action="reactivate", reason="Test reactivate")
        result = TenantManagementService.execute_action(
            company_id=self.company.id_company,
            dto=dto_reactivate,
            actor_user=self.admin_user,
        )
        self.assertEqual(result.status, CompanyInfo.CompanyStatus.ACTIVE)

        dto_extend = TenantActionDto(
            action="extend-trial", reason="Test extend", extra_days=7
        )
        result_sub = TenantManagementService.execute_action(
            company_id=self.company.id_company,
            dto=dto_extend,
            actor_user=self.admin_user,
        )
        self.assertTrue(isinstance(result_sub, Subscription))

        dto_invalid = TenantActionDto(action="delete_everything", reason="")
        with self.assertRaises(InvalidTenantActionException):
            TenantManagementService.execute_action(
                company_id=self.company.id_company,
                dto=dto_invalid,
            )
