import threading
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TransactionTestCase
from django.utils import timezone

from apps.company_info.models import CompanyInfo
from apps.saas_admin.services.saas_subscription_service import SaaSSubscriptionService
from apps.subscriptions.models import Plan, Subscription

User = get_user_model()


class SaaSSubscriptionConcurrencyTests(TransactionTestCase):
    """
    Suite de pruebas concurrentes reales para el módulo de Planes y Suscripciones SaaS.
    Utiliza TransactionTestCase para permitir conexiones multihilo reales y barreras de sincronización.
    """

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin_concurrency@saas.com",
            email="admin_concurrency@saas.com",
            password="AdminPassword123!",
            document_number="7770001",
        )

        self.plan_basic = Plan.objects.create(
            code="CONC_BASIC",
            name="Plan Basic Conc",
            price=Decimal("15.00"),
            billing_cycle=Plan.BillingCycle.MONTHLY,
            max_users=2,
            max_products=50,
            max_invoices_per_month=50,
            is_active=True,
        )

        self.plan_pro = Plan.objects.create(
            code="CONC_PRO",
            name="Plan Pro Conc",
            price=Decimal("45.00"),
            billing_cycle=Plan.BillingCycle.MONTHLY,
            max_users=10,
            max_products=500,
            max_invoices_per_month=500,
            is_active=True,
        )

        self.company = CompanyInfo.objects.create(
            business_name="Empresa Concurrencia SAS",
            trade_name="Conc SAS",
            tax_id="901999888-9",
            owner_user=self.admin_user,
            status=CompanyInfo.CompanyStatus.ACTIVE,
        )

    def test_simultaneous_assignments_preserve_single_active_subscription_invariant(self):
        """
        Escenario 1: Dos solicitudes de asignación simultáneas para la misma empresa.
        Verifica que al finalizar el proceso, la empresa NUNCA quede con múltiples suscripciones activas.
        """
        barrier = threading.Barrier(2)
        results = []
        errors = []

        def assign_worker(plan, label):
            try:
                barrier.wait(timeout=5)
                sub = SaaSSubscriptionService.assign_plan(
                    company_id=self.company.pk,
                    plan_id=plan.pk,
                    duration_days=30,
                    notes=f"Asignación concurrente desde {label}",
                    actor_user=self.admin_user,
                )
                results.append((label, sub.pk))
            except Exception as e:
                errors.append((label, type(e).__name__, str(e)))
            finally:
                connection.close()

        t1 = threading.Thread(target=assign_worker, args=(self.plan_basic, "Thread_A"))
        t2 = threading.Thread(target=assign_worker, args=(self.plan_pro, "Thread_B"))

        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        # Verificación de invariante estricto
        active_count = Subscription.objects.filter(
            company=self.company,
            status=Subscription.Status.ACTIVE,
            is_active=True,
        ).count()

        self.assertEqual(
            active_count,
            1,
            f"Fallo de integridad: La empresa tiene {active_count} suscripciones activas simultáneas.",
        )

    def test_simultaneous_assignment_and_renewal_preserve_consistency(self):
        """
        Escenario 2: Asignación y renovación simultáneas.
        """
        sub_initial = SaaSSubscriptionService.assign_plan(
            company_id=self.company.pk,
            plan_id=self.plan_basic.pk,
            duration_days=30,
            actor_user=self.admin_user,
        )

        barrier = threading.Barrier(2)

        def assign_thread():
            try:
                barrier.wait(timeout=5)
                SaaSSubscriptionService.assign_plan(
                    company_id=self.company.pk,
                    plan_id=self.plan_pro.pk,
                    duration_days=60,
                    notes="Assign PRO",
                    actor_user=self.admin_user,
                )
            except Exception:
                pass
            finally:
                connection.close()

        def renew_thread():
            try:
                barrier.wait(timeout=5)
                SaaSSubscriptionService.renew_subscription(
                    subscription_id=sub_initial.pk,
                    duration_days=30,
                    reason="Renew BASIC",
                    actor_user=self.admin_user,
                )
            except Exception:
                pass
            finally:
                connection.close()

        t1 = threading.Thread(target=assign_thread)
        t2 = threading.Thread(target=renew_thread)

        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        active_count = Subscription.objects.filter(
            company=self.company,
            status=Subscription.Status.ACTIVE,
            is_active=True,
        ).count()

        self.assertEqual(active_count, 1)

    def test_simultaneous_renewals_accumulate_or_serialize(self):
        """
        Escenario 3: Dos renovaciones simultáneas sobre la misma suscripción.
        Deben serializarse o bloquearse limpiamente sin corromper fechas.
        """
        sub = SaaSSubscriptionService.assign_plan(
            company_id=self.company.pk,
            plan_id=self.plan_basic.pk,
            duration_days=30,
            actor_user=self.admin_user,
        )
        initial_end = sub.end_date

        barrier = threading.Barrier(2)

        def renew_worker():
            try:
                barrier.wait(timeout=5)
                SaaSSubscriptionService.renew_subscription(
                    subscription_id=sub.pk,
                    duration_days=30,
                    reason="Renovación concurrente",
                    actor_user=self.admin_user,
                )
            except Exception:
                pass
            finally:
                connection.close()

        t1 = threading.Thread(target=renew_worker)
        t2 = threading.Thread(target=renew_worker)

        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        sub.refresh_from_db()
        days_added = (sub.end_date - initial_end).days
        self.assertIn(days_added, [30, 60])
        self.assertEqual(sub.status, Subscription.Status.ACTIVE)

    def test_simultaneous_plan_change_and_renewal(self):
        """
        Escenario 4: Cambio de plan y renovación simultáneos.
        """
        sub = SaaSSubscriptionService.assign_plan(
            company_id=self.company.pk,
            plan_id=self.plan_basic.pk,
            duration_days=30,
            actor_user=self.admin_user,
        )

        barrier = threading.Barrier(2)

        def change_worker():
            try:
                barrier.wait(timeout=5)
                SaaSSubscriptionService.change_plan(
                    subscription_id=sub.pk,
                    new_plan_id=self.plan_pro.pk,
                    reason="Upgrade concurrente",
                    actor_user=self.admin_user,
                )
            except Exception:
                pass
            finally:
                connection.close()

        def renew_worker():
            try:
                barrier.wait(timeout=5)
                SaaSSubscriptionService.renew_subscription(
                    subscription_id=sub.pk,
                    duration_days=30,
                    reason="Renovación concurrente",
                    actor_user=self.admin_user,
                )
            except Exception:
                pass
            finally:
                connection.close()

        t1 = threading.Thread(target=change_worker)
        t2 = threading.Thread(target=renew_worker)

        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        sub.refresh_from_db()
        self.assertEqual(sub.status, Subscription.Status.ACTIVE)
        # La suscripción no se corrompe y mantiene coherencia
        self.assertTrue(sub.plan.code in ["CONC_BASIC", "CONC_PRO"])
