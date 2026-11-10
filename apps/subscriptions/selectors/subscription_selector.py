from typing import Any, Dict, Optional

from django.db.models import QuerySet
from django.utils import timezone

from apps.categories.models import Category
from apps.invoices.models import Invoice
from apps.products.models import Product
from apps.subscriptions.models import Plan, Subscription
from apps.users.models import CompanyMembership


class SubscriptionSelector:
    """
    Selector para consultas optimizadas de planes, suscripciones y métricas de consumo.
    """

    @staticmethod
    def get_available_plans() -> QuerySet[Plan]:
        """Retorna todos los planes comerciales activos disponibles para suscripción."""
        return Plan.objects.filter(is_active=True).order_by("price")

    @staticmethod
    def get_plan_by_code(code: str) -> Optional[Plan]:
        """Obtiene un plan específico por su código único."""
        return Plan.objects.filter(code__iexact=code, is_active=True).first()

    @staticmethod
    def get_current_subscription(company) -> Optional[Subscription]:
        """
        Obtiene la suscripción más reciente y aplicable para una empresa.
        Prioriza suscripciones válidas y activas.
        """
        if not company:
            return None

        # Primero busca activa o trial
        sub = (
            Subscription.objects.filter(
                company=company,
                is_active=True,
                status__in=[
                    Subscription.Status.ACTIVE,
                    Subscription.Status.TRIAL,
                    Subscription.Status.PAST_DUE,
                ],
            )
            .select_related("plan")
            .order_by("-end_date")
            .first()
        )
        if sub:
            return sub

        # Si no hay activa, retorna la última registrada
        return (
            Subscription.objects.filter(company=company, is_active=True)
            .select_related("plan")
            .order_by("-end_date")
            .first()
        )

    @staticmethod
    def get_company_usage_metrics(company) -> Dict[str, Any]:
        """
        Calcula las métricas de consumo de la empresa frente a los límites de su plan.
        """
        if not company:
            return {
                "has_subscription": False,
                "plan": None,
                "users": {"current": 0, "max": 0, "percentage": 0},
                "products": {"current": 0, "max": 0, "percentage": 0},
                "invoices": {"current": 0, "max": 0, "percentage": 0},
            }

        sub = SubscriptionSelector.get_current_subscription(company)
        plan = sub.plan if sub else None

        active_users_count = CompanyMembership.objects.filter(
            company=company,
            is_active=True,
            status=CompanyMembership.MembershipStatus.ACTIVE,
        ).count()

        products_count = Product.objects.filter(
            company=company,
            is_active=True,
        ).count()

        # Facturas del mes calendario en curso
        now = timezone.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_invoices_count = Invoice.objects.filter(
            company=company,
            created_at__gte=start_of_month,
        ).count()

        max_users = plan.max_users if plan else 1
        max_products = plan.max_products if plan else 100
        max_invoices = plan.max_invoices_per_month if plan else 100

        user_pct = round((active_users_count / max_users * 100), 1) if max_users else 0
        prod_pct = round((products_count / max_products * 100), 1) if max_products else 0
        inv_pct = round((monthly_invoices_count / max_invoices * 100), 1) if max_invoices else 0

        return {
            "has_subscription": sub is not None,
            "subscription_id": sub.pk if sub else None,
            "status": sub.status if sub else "NO_SUBSCRIPTION",
            "is_valid": sub.is_valid if sub else False,
            "days_remaining": sub.days_remaining if sub else 0,
            "plan": {
                "code": plan.code if plan else "NONE",
                "name": plan.name if plan else "Sin Plan Asignado",
                "price": str(plan.price) if plan else "0.00",
                "billing_cycle": plan.billing_cycle if plan else "MONTHLY",
                "enabled_modules": plan.enabled_modules if plan else [],
            }
            if plan
            else None,
            "usage": {
                "users": {
                    "current": active_users_count,
                    "max": max_users,
                    "percentage": min(user_pct, 100),
                    "is_exceeded": active_users_count > max_users,
                },
                "products": {
                    "current": products_count,
                    "max": max_products,
                    "percentage": min(prod_pct, 100),
                    "is_exceeded": products_count > max_products,
                },
                "invoices": {
                    "current": monthly_invoices_count,
                    "max": max_invoices,
                    "percentage": min(inv_pct, 100),
                    "is_exceeded": monthly_invoices_count > max_invoices,
                },
            },
        }

