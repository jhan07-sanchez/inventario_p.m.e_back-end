from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.categories.models import Category
from apps.company_info.models import CompanyInfo
from apps.core.middlewares.subscription_middleware import SubscriptionMiddleware
from apps.products.models import Product
from apps.subscriptions.models import Plan, Subscription, SubscriptionPayment
from apps.subscriptions.selectors.subscription_selector import SubscriptionSelector
from apps.subscriptions.services.plan_limit_validator_service import (
    PlanLimitValidatorService,
)
from apps.subscriptions.services.subscription_service import SubscriptionService
from apps.users.models import CompanyMembership, Role

User = get_user_model()


class SubscriptionTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin@saas.com",
            email="admin@saas.com",
            password="Password123!",
            first_name="Admin",
            last_name="SaaS",
        )
        self.role_admin = Role.objects.create(
            role_name="ADMIN", role_description="Administrador", is_active=True
        )
        self.company = CompanyInfo.objects.create(
            business_name="Empresa SaaS 1",
            trade_name="SaaS 1",
            tax_id="900111222-1",
            owner_user=self.user,
        )
        self.membership = CompanyMembership.objects.create(
            user=self.user,
            company=self.company,
            role=self.role_admin,
            is_owner=True,
            status=CompanyMembership.MembershipStatus.ACTIVE,
        )
        self.plan_basic = Plan.objects.create(
            code="BASIC",
            name="Plan Básico",
            price=Decimal("49.99"),
            billing_cycle=Plan.BillingCycle.MONTHLY,
            max_users=2,
            max_products=5,
            max_invoices_per_month=10,
            enabled_modules=["inventory", "sales"],
            is_active=True,
        )
        self.plan_pro = Plan.objects.create(
            code="PRO",
            name="Plan Pro",
            price=Decimal("149.99"),
            billing_cycle=Plan.BillingCycle.MONTHLY,
            max_users=10,
            max_products=1000,
            max_invoices_per_month=1000,
            enabled_modules=["inventory", "sales", "finance", "cash", "invoices"],
            is_active=True,
        )
        self.client = APIClient()

    def test_assign_plan_and_selector(self):
        sub = SubscriptionService.assign_or_renew_plan(
            company=self.company,
            plan=self.plan_basic,
            duration_days=30,
        )
        self.assertIsNotNone(sub)
        self.assertTrue(sub.is_valid)
        self.assertEqual(sub.plan, self.plan_basic)

        fetched_sub = SubscriptionSelector.get_current_subscription(self.company)
        self.assertEqual(fetched_sub.pk, sub.pk)

    def test_record_payment_renews_subscription(self):
        sub = SubscriptionService.assign_or_renew_plan(
            company=self.company,
            plan=self.plan_basic,
            duration_days=10,
        )
        initial_end = sub.end_date

        payment = SubscriptionService.record_payment(
            subscription=sub,
            amount=Decimal("49.99"),
            payment_method="STRIPE",
            transaction_reference="ch_123456",
        )
        self.assertEqual(payment.status, SubscriptionPayment.PaymentStatus.APPROVED)
        sub.refresh_from_db()
        self.assertGreater(sub.end_date, initial_end)

    def test_product_limit_validator(self):
        SubscriptionService.assign_or_renew_plan(
            company=self.company,
            plan=self.plan_basic,  # max_products = 5
        )

        category = Category.objects.create(name="General", company=self.company)
        for i in range(5):
            Product.objects.create(
                company=self.company,
                category=category,
                code=f"PRD-{i}",
                name=f"Producto {i}",
                purchase_price=Decimal("5.00"),
                sale_price=Decimal("10.00"),
            )

        # 5 products exist; adding 6th should be rejected by validator
        with self.assertRaises(ValidationError) as ctx:
            PlanLimitValidatorService.validate_can_add_product(self.company)
        self.assertIn("PLAN_PRODUCT_LIMIT_EXCEEDED", str(ctx.exception))

    def test_module_access_validator(self):
        SubscriptionService.assign_or_renew_plan(
            company=self.company,
            plan=self.plan_basic,  # only inventory, sales
        )

        # Inventory is allowed
        PlanLimitValidatorService.validate_module_access(self.company, "inventory")

        # Finance is NOT in basic plan
        with self.assertRaises(PermissionDenied) as ctx:
            PlanLimitValidatorService.validate_module_access(self.company, "finance")
        self.assertIn("MODULE_NOT_IN_PLAN", str(ctx.exception))

    def test_subscription_middleware_blocks_writes_when_expired(self):
        # Expired subscription past grace period
        now = timezone.now()
        Subscription.objects.create(
            company=self.company,
            plan=self.plan_basic,
            status=Subscription.Status.EXPIRED,
            start_date=now - timedelta(days=40),
            end_date=now - timedelta(days=10),
            grace_period_days=5,
            is_active=True,
        )

        rf = RequestFactory()
        # GET is safe: must pass through
        req_get = rf.get("/api/v1/products/")
        req_get.company = self.company
        middleware = SubscriptionMiddleware(lambda r: None)
        res_get = middleware(req_get)
        self.assertIsNone(res_get)  # Passed through to inner handler

        # POST is mutation: must be blocked with 403
        req_post = rf.post("/api/v1/products/", {})
        req_post.company = self.company
        res_post = middleware(req_post)
        self.assertEqual(res_post.status_code, 403)
        self.assertIn("SUBSCRIPTION_EXPIRED_OR_SUSPENDED", res_post.content.decode())

    def test_current_subscription_endpoint(self):
        SubscriptionService.assign_or_renew_plan(
            company=self.company,
            plan=self.plan_basic,
        )
        self.client.force_authenticate(user=self.user)
        res = self.client.get(
            "/api/v1/subscriptions/current/",
            HTTP_X_COMPANY_ID=str(self.company.pk),
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()["data"]
        self.assertIn("subscription", data)
        self.assertIn("metrics", data)
        self.assertEqual(data["metrics"]["plan"]["code"], "BASIC")

    def test_change_plan_endpoint(self):
        SubscriptionService.assign_or_renew_plan(
            company=self.company,
            plan=self.plan_basic,
        )
        self.client.force_authenticate(user=self.user)
        res = self.client.post(
            "/api/v1/subscriptions/change-plan/",
            {"plan_code": "PRO"},
            format="json",
            HTTP_X_COMPANY_ID=str(self.company.pk),
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        sub = SubscriptionSelector.get_current_subscription(self.company)
        self.assertEqual(sub.plan.code, "PRO")
