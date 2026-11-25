from rest_framework import status
from rest_framework.decorators import action

from apps.core.pagination.custom_pagination import CustomPagination
from apps.core.views.base_viewset import BaseGenericViewSet
from apps.saas_admin.permissions import IsSaaSAdmin
from apps.saas_admin.selectors.saas_subscription_selector import (
    SaaSSubscriptionSelector,
)
from apps.saas_admin.serializers.subscription_serializer import (
    SaaSAssignPlanSerializer,
    SaaSChangePlanSerializer,
    SaaSRenewSubscriptionSerializer,
    SaaSSubscriptionListSerializer,
)
from apps.saas_admin.services.saas_subscription_service import SaaSSubscriptionService
from apps.subscriptions.models import Subscription


class SaaSSubscriptionViewSet(BaseGenericViewSet):
    """
    ViewSet administrativo para la gestión centralizada de suscripciones de todas las empresas.
    Permite listar con paginación server-side, consultar cuotas, asignar, cambiar plan y renovar.
    Protegido por IsSaaSAdmin.
    """

    permission_classes = [IsSaaSAdmin]
    pagination_class = CustomPagination
    serializer_class = SaaSSubscriptionListSerializer

    def list(self, request, *args, **kwargs):
        """Lista todas las suscripciones de la plataforma con filtros y paginación."""
        search = request.query_params.get("search")
        status_param = request.query_params.get("status")
        plan_code = request.query_params.get("plan_code")
        company_id = request.query_params.get("company_id")

        subs_qs = SaaSSubscriptionSelector.get_all_subscriptions(
            search=search,
            status=status_param,
            plan_code=plan_code,
            company_id=int(company_id) if company_id and company_id.isdigit() else None,
        )

        page = self.paginate_queryset(subs_qs)
        if page is not None:
            serializer = SaaSSubscriptionListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = SaaSSubscriptionListSerializer(subs_qs, many=True)
        return self.success_response(
            data=serializer.data,
            code="SAAS_SUBSCRIPTIONS_FETCHED",
            message="Suscripciones obtenidas correctamente.",
        )

    def retrieve(self, request, pk=None, *args, **kwargs):
        """Consulta el detalle de una suscripción específica."""
        try:
            sub = Subscription.objects.select_related("company", "plan").get(
                id_subscription=int(pk)
            )
        except (Subscription.DoesNotExist, ValueError):
            return self.error_response(
                message=f"No se encontró la suscripción con ID {pk}.",
                status_code=status.HTTP_404_NOT_FOUND,
                code="SUBSCRIPTION_NOT_FOUND",
            )

        serializer = SaaSSubscriptionListSerializer(sub)
        return self.success_response(
            data=serializer.data,
            code="SAAS_SUBSCRIPTION_DETAIL_FETCHED",
            message="Detalle de suscripción obtenido correctamente.",
        )

    @action(detail=False, methods=["get"], url_path="kpis")
    def kpis(self, request):
        """Consulta los indicadores clave de rendimiento (KPIs) comerciales."""
        data = SaaSSubscriptionSelector.get_commercial_kpis()
        return self.success_response(
            data=data,
            code="SAAS_COMMERCIAL_KPIS_FETCHED",
            message="KPIs comerciales calculados correctamente.",
        )

    @action(
        detail=False, methods=["get"], url_path=r"company/(?P<company_id>[^/.]+)/quotas"
    )
    def company_quotas(self, request, company_id=None):
        """Consulta el consumo en tiempo real de cuotas (usuarios, productos, facturas) de una empresa."""
        if not company_id or not company_id.isdigit():
            return self.error_response(
                message="Debe especificar un ID de empresa válido.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        metrics = SaaSSubscriptionSelector.get_company_quotas_and_metrics(
            int(company_id)
        )
        if not metrics:
            return self.error_response(
                message=f"No se encontró la empresa con ID {company_id}.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return self.success_response(
            data=metrics,
            code="SAAS_COMPANY_QUOTAS_FETCHED",
            message="Cuotas y métricas de consumo obtenidas correctamente.",
        )

    @action(detail=False, methods=["post"], url_path="assign")
    def assign(self, request):
        """Asigna una nueva suscripción formal a una empresa cliente."""
        serializer = SaaSAssignPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sub = SaaSSubscriptionService.assign_plan(
            company_id=serializer.validated_data["company_id"],
            plan_id=serializer.validated_data["plan_id"],
            duration_days=serializer.validated_data.get("duration_days", 30),
            status=serializer.validated_data.get("status", Subscription.Status.ACTIVE),
            notes=serializer.validated_data.get("notes", ""),
            actor_user=request.user,
        )

        return self.success_response(
            data=SaaSSubscriptionListSerializer(sub).data,
            code="SAAS_SUBSCRIPTION_ASSIGNED",
            message=f"Plan '{sub.plan.name}' asignado exitosamente a la empresa '{sub.company.business_name}'.",
            status_code=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="change-plan")
    def change_plan(self, request, pk=None):
        """
        Cambia el plan comercial de una suscripción activa sin alterar la fecha de vencimiento.
        """
        serializer = SaaSChangePlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sub = SaaSSubscriptionService.change_plan(
            subscription_id=int(pk),
            new_plan_id=serializer.validated_data["new_plan_id"],
            reason=serializer.validated_data["reason"],
            actor_user=request.user,
        )

        return self.success_response(
            data=SaaSSubscriptionListSerializer(sub).data,
            code="SAAS_SUBSCRIPTION_PLAN_CHANGED",
            message=f"Plan de la suscripción #{sub.id_subscription} actualizado a '{sub.plan.name}' exitosamente.",
        )

    @action(detail=True, methods=["post"], url_path="renew")
    def renew(self, request, pk=None):
        """
        Renueva la suscripción extendiendo su vigencia en días a partir del vencimiento actual.
        """
        serializer = SaaSRenewSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sub = SaaSSubscriptionService.renew_subscription(
            subscription_id=int(pk),
            duration_days=serializer.validated_data.get("duration_days"),
            reason=serializer.validated_data.get("reason", ""),
            actor_user=request.user,
        )

        return self.success_response(
            data=SaaSSubscriptionListSerializer(sub).data,
            code="SAAS_SUBSCRIPTION_RENEWED",
            message=f"Suscripción renovada exitosamente hasta el {sub.end_date.strftime('%Y-%m-%d')}.",
        )
