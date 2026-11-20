from decimal import Decimal
from typing import Any, Optional

from django.db.models import Prefetch, Q, QuerySet, Sum
from django.utils import timezone

from apps.company_info.models import CompanyInfo
from apps.core.exceptions import TenantNotFoundException
from apps.subscriptions.models import Plan, Subscription, SubscriptionPayment
from apps.users.models import User


class SaaSAdminSelector:
    """
    Selector centralizado para consultas de administración global de la plataforma SaaS.
    Optimiza lecturas de solo lectura con select_related y prefetch_related, previniendo N+1.
    """

    @classmethod
    def get_all_tenants(
        cls,
        search: Optional[str] = None,
        status: Optional[str] = None,
        plan_code: Optional[str] = None,
        subscription_status: Optional[str] = None,
    ) -> QuerySet[CompanyInfo]:
        """
        Retorna el QuerySet optimizado de todas las empresas para la vista administrativa global.
        Permite filtrado por texto (búsqueda), estado de empresa, código de plan y estado de suscripción.
        """
        latest_subs_qs = (
            Subscription.objects.filter(is_active=True)
            .select_related("plan")
            .order_by("-start_date")
        )

        qs = (
            CompanyInfo.objects.filter(is_active=True)
            .select_related("owner_user")
            .prefetch_related(
                Prefetch(
                    "subscriptions",
                    queryset=latest_subs_qs,
                    to_attr="prefetched_subscriptions",
                )
            )
            .order_by("-created_at")
        )

        if search:
            search_term = search.strip()
            qs = qs.filter(
                Q(business_name__icontains=search_term)
                | Q(trade_name__icontains=search_term)
                | Q(tax_id__icontains=search_term)
                | Q(email__icontains=search_term)
            )

        if status:
            qs = qs.filter(status=status.upper())

        if plan_code:
            qs = qs.filter(
                subscriptions__plan__code=plan_code.upper(),
                subscriptions__is_active=True,
            ).distinct()

        if subscription_status:
            qs = qs.filter(
                subscriptions__status=subscription_status.upper(),
                subscriptions__is_active=True,
            ).distinct()

        return qs

    @classmethod
    def get_tenant_detail(cls, company_id: int) -> dict[str, Any]:
        """
        Retorna el detalle administrativo completo de una empresa, incluyendo propietario,
        suscripción activa, histórico de planes, límites de uso y pagos registrados.
        """
        latest_subs_qs = (
            Subscription.objects.filter(is_active=True)
            .select_related("plan")
            .order_by("-start_date")
        )

        try:
            company = (
                CompanyInfo.objects.filter(id_company=company_id)
                .select_related("owner_user")
                .prefetch_related(
                    Prefetch(
                        "subscriptions",
                        queryset=latest_subs_qs,
                        to_attr="prefetched_subscriptions",
                    ),
                    "memberships__user",
                    "memberships__role",
                )
                .get()
            )
        except CompanyInfo.DoesNotExist:
            raise TenantNotFoundException()

        # Determinar suscripción actual
        subs = getattr(company, "prefetched_subscriptions", [])
        current_sub = subs[0] if subs else None

        # Historial de pagos de suscripción
        payments_qs = (
            SubscriptionPayment.objects.filter(
                subscription__company=company,
                is_active=True,
            )
            .select_related("subscription__plan")
            .order_by("-payment_date")[:10]
        )

        active_members_count = company.memberships.filter(is_active=True).count()

        return {
            "company": company,
            "current_subscription": current_sub,
            "all_subscriptions": subs,
            "recent_payments": list(payments_qs),
            "active_members_count": active_members_count,
        }

    @classmethod
    def get_global_metrics(cls) -> dict[str, Any]:
        """
        Calcula las métricas e indicadores clave de rendimiento (KPIs) globales de la plataforma SaaS.

        Fórmulas y criterios de negocio:
        - MRR (Monthly Recurring Revenue): Normalización exacta según ciclo de facturación de planes activos pagados.
          * Mensual: precio directo.
          * Anual: precio dividido entre 12 meses.
          * Excluye pruebas gratuitas (TRIAL), suscripciones canceladas o expiradas.
        - Pruebas activas: Suscripciones en estado TRIAL cuya fecha de fin es mayor o igual a la fecha actual.
        - Suscripciones activas pagadas: Suscripciones en estado ACTIVE vigentes.
        - Recaudación del mes: Suma de pagos aprobados (APPROVED) efectuados durante el mes en curso.
        """
        now = timezone.now()

        # Empresas
        total_companies = CompanyInfo.objects.filter(is_active=True).count()
        active_companies = CompanyInfo.objects.filter(
            is_active=True, status=CompanyInfo.CompanyStatus.ACTIVE
        ).count()
        suspended_companies = CompanyInfo.objects.filter(
            is_active=True, status=CompanyInfo.CompanyStatus.SUSPENDED
        ).count()

        # Suscripciones
        active_trials = Subscription.objects.filter(
            is_active=True,
            status=Subscription.Status.TRIAL,
            end_date__gte=now,
        ).count()

        active_paid_subs = Subscription.objects.filter(
            is_active=True,
            status=Subscription.Status.ACTIVE,
            end_date__gte=now,
        ).select_related("plan")
        active_paid_count = active_paid_subs.count()

        past_due_subs = Subscription.objects.filter(
            is_active=True,
            status=Subscription.Status.PAST_DUE,
        ).count()

        expired_subs = Subscription.objects.filter(
            is_active=True,
            status=Subscription.Status.EXPIRED,
        ).count()

        # Cálculo normalizado de MRR
        mrr = Decimal("0.00")
        for sub in active_paid_subs:
            plan = sub.plan
            if plan and plan.price > Decimal("0.00"):
                if plan.billing_cycle == Plan.BillingCycle.ANNUAL:
                    mrr += plan.price / Decimal("12.00")
                else:
                    mrr += plan.price

        mrr_rounded = mrr.quantize(Decimal("0.01"))

        # Recaudación de pagos
        current_month_revenue = SubscriptionPayment.objects.filter(
            status=SubscriptionPayment.PaymentStatus.APPROVED,
            payment_date__year=now.year,
            payment_date__month=now.month,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        total_historical_revenue = SubscriptionPayment.objects.filter(
            status=SubscriptionPayment.PaymentStatus.APPROVED,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        #CONTAR SOLO USUARIOS DE EMPRESAS CLIENTES (TENANTS)
        # Filtramos a los usuarios que tienen una membresía activa en alguna empresa.
        # Usamos .distinct() por si un usuario pertenece a varias empresas, para no contarlo doble.
        total_users = (
            User.objects.filter(
                is_active=True,
                is_staff=False,  # Excluye al equipo de soporte/ventas
                is_superuser=False,  # # Excluye al dueño del SaaS
                memberships__is_active=True,
                memberships__status="ACTIVE",
            )
            .distinct()
            .count()
        )

        recent_payments = (
            SubscriptionPayment.objects.filter(is_active=True)
            .select_related("subscription__company", "subscription__plan")
            .order_by("-payment_date")[:5]
        )
        recent_payments_data = [
            {
                "id_payment": p.id_payment,
                "amount": float(p.amount),
                "payment_date": p.payment_date.isoformat() if p.payment_date else None,
                "company_name": p.subscription.company.business_name if p.subscription and p.subscription.company else "N/A",
                "plan_name": p.subscription.plan.name if p.subscription and p.subscription.plan else "N/A",
                "status": p.status,
            }
            for p in recent_payments
        ]

        return {
            "total_companies": total_companies,
            "active_companies": active_companies,
            "suspended_companies": suspended_companies,
            "total_users": total_users,
            "active_trials": active_trials,
            "active_paid_subscriptions": active_paid_count,
            "past_due_subscriptions": past_due_subs,
            "expired_subscriptions": expired_subs,
            "mrr": float(mrr_rounded),
            "current_month_revenue": float(current_month_revenue),
            "total_historical_revenue": float(total_historical_revenue),
            "recent_payments": recent_payments_data,
        }


# Alias de compatibilidad hacia atrás
SaaSDashboardSelector = SaaSAdminSelector
