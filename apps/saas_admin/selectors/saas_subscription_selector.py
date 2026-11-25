from typing import Any, Dict, Optional

from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from apps.company_info.models import CompanyInfo
from apps.subscriptions.models import Plan, Subscription
from apps.subscriptions.selectors.subscription_selector import SubscriptionSelector


class SaaSSubscriptionSelector:
    """
    Selector especializado para consultas administrativas globales sobre planes y suscripciones.
    """

    @classmethod
    def get_all_plans(
        cls,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> QuerySet[Plan]:
        """
        Retorna el QuerySet de todos los planes comerciales (activos e inactivos),
        anotando el conteo de suscripciones activas vinculadas.
        """
        qs = Plan.objects.annotate(
            active_subs_count=Count(
                "subscriptions",
                filter=Q(
                    subscriptions__is_active=True,
                    subscriptions__status=Subscription.Status.ACTIVE,
                ),
            )
        ).order_by("-is_active", "price")

        if search:
            term = search.strip()
            qs = qs.filter(
                Q(name__icontains=term)
                | Q(code__icontains=term)
                | Q(description__icontains=term)
            )

        if is_active is not None:
            qs = qs.filter(is_active=is_active)

        return qs

    @classmethod
    def get_all_subscriptions(
        cls,
        search: Optional[str] = None,
        status: Optional[str] = None,
        plan_code: Optional[str] = None,
        company_id: Optional[int] = None,
    ) -> QuerySet[Subscription]:
        """
        Retorna todas las suscripciones de todas las empresas con select_related para evitar N+1.
        """
        qs = (
            Subscription.objects.filter(is_active=True)
            .select_related("company", "plan")
            .order_by("-start_date")
        )

        if search:
            term = search.strip()
            qs = qs.filter(
                Q(company__business_name__icontains=term)
                | Q(company__trade_name__icontains=term)
                | Q(company__tax_id__icontains=term)
                | Q(plan__name__icontains=term)
                | Q(plan__code__icontains=term)
            )

        if status:
            qs = qs.filter(status=status.upper())

        if plan_code:
            qs = qs.filter(plan__code__iexact=plan_code)

        if company_id:
            qs = qs.filter(company_id=company_id)

        return qs

    @classmethod
    def get_commercial_kpis(cls) -> Dict[str, Any]:
        """
        Calcula los KPIs comerciales consolidados de la plataforma.
        """
        now = timezone.now()

        total_plans = Plan.objects.count()
        active_plans = Plan.objects.filter(is_active=True).count()

        total_subs = Subscription.objects.filter(is_active=True).count()
        active_subs = Subscription.objects.filter(
            is_active=True,
            status=Subscription.Status.ACTIVE,
            end_date__gte=now,
        ).count()
        trials = Subscription.objects.filter(
            is_active=True,
            status=Subscription.Status.TRIAL,
            end_date__gte=now,
        ).count()
        past_due = Subscription.objects.filter(
            is_active=True,
            status=Subscription.Status.PAST_DUE,
        ).count()
        expired = Subscription.objects.filter(
            is_active=True,
            status=Subscription.Status.EXPIRED,
        ).count()

        # Próximas a vencer (en los siguientes 7 días)
        seven_days_later = now + timezone.timedelta(days=7)
        expiring_soon = Subscription.objects.filter(
            is_active=True,
            status__in=[Subscription.Status.ACTIVE, Subscription.Status.TRIAL],
            end_date__gte=now,
            end_date__lte=seven_days_later,
        ).count()

        return {
            "total_plans": total_plans,
            "active_plans": active_plans,
            "inactive_plans": total_plans - active_plans,
            "total_subscriptions": total_subs,
            "active_subscriptions": active_subs,
            "active_trials": trials,
            "past_due_subscriptions": past_due,
            "expired_subscriptions": expired,
            "expiring_soon": expiring_soon,
        }

    @classmethod
    def get_company_quotas_and_metrics(cls, company_id: int) -> Dict[str, Any]:
        """
        Retorna las cuotas y consumo de recursos de una empresa específica.
        """
        try:
            company = CompanyInfo.objects.get(id_company=company_id)
        except CompanyInfo.DoesNotExist:
            return None
        return SubscriptionSelector.get_company_usage_metrics(company)
