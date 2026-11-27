from drf_spectacular.utils import extend_schema_view
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action

from apps.core.utils.api_response import ApiResponse
from apps.subscriptions.docs.subscription_docs import (
    plan_detail_schema,
    plan_list_schema,
    subscription_change_plan_schema,
    subscription_current_schema,
)
from apps.subscriptions.models import Plan
from apps.subscriptions.selectors.subscription_selector import SubscriptionSelector
from apps.subscriptions.serializers.subscription_serializers import (
    PlanSerializer,
    SubscriptionSerializer,
    SubscriptionStatusSerializer,
)
from apps.subscriptions.services.subscription_service import SubscriptionService


@extend_schema_view(
    list=plan_list_schema,
    retrieve=plan_detail_schema,
)
class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Endpoint para consultar los planes de suscripción disponibles en P.M.E.
    """

    queryset = Plan.objects.filter(is_active=True).order_by("price")
    serializer_class = PlanSerializer
    permission_classes = [permissions.IsAuthenticated]


class SubscriptionViewSet(viewsets.ViewSet):
    """
    Controlador de la suscripción del inquilino (Empresa) activo.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SubscriptionSerializer

    @subscription_current_schema
    @action(detail=False, methods=["get"], url_path="current")
    def current(self, request):
        company = getattr(request, "company", None)
        if not company:
            return ApiResponse.error(
                message="No hay una empresa seleccionada en el contexto actual.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        metrics = SubscriptionSelector.get_company_usage_metrics(company)
        sub = SubscriptionSelector.get_current_subscription(company)
        sub_data = SubscriptionSerializer(sub).data if sub else None
        status_data = SubscriptionSelector.get_subscription_status(company)
        status_serialized = SubscriptionStatusSerializer(
            status_data, context={"company": company, "request": request}
        ).data

        return ApiResponse.success(
            data={
                "subscription": sub_data,
                "status": status_serialized,
                "metrics": metrics,
            },
            message="Información de suscripción obtenida exitosamente.",
        )

    @action(detail=False, methods=["get"], url_path="current/status")
    def current_status(self, request):
        """
        Retorna el estado operativo de la suscripción de la empresa activa
        (is_valid, is_read_only, can_write, status, grace_period, renew_url).
        """
        company = getattr(request, "company", None)
        if not company:
            return ApiResponse.error(
                message="No hay una empresa seleccionada en el contexto actual.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        status_data = SubscriptionSelector.get_subscription_status(company)
        serializer = SubscriptionStatusSerializer(
            status_data, context={"company": company, "request": request}
        )
        return ApiResponse.success(
            data=serializer.data,
            message="Estado de suscripción obtenido exitosamente.",
        )

    @action(detail=False, methods=["get"], url_path="status")
    def status_alias(self, request):
        """Alias para /api/v1/subscriptions/status/"""
        return self.current_status(request)

    @subscription_change_plan_schema
    @action(detail=False, methods=["post"], url_path="change-plan")
    def change_plan(self, request):
        company = getattr(request, "company", None)
        if not company:
            return ApiResponse.error(
                message="No hay una empresa seleccionada en el contexto actual.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Solo el dueño o administrador puede cambiar de plan
        membership = request.user.memberships.filter(
            company=company, is_active=True
        ).first()
        if not membership or (
            not membership.is_owner
            and getattr(membership.role, "role_name", "") != "ADMIN"
        ):
            return ApiResponse.error(
                message="Solo el propietario o administrador de la empresa puede modificar el plan de suscripción.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        plan_code = request.data.get("plan_code")
        if not plan_code:
            return ApiResponse.error(
                message="Debe especificar el código del plan ('plan_code').",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        plan = SubscriptionSelector.get_plan_by_code(plan_code)
        if not plan:
            return ApiResponse.error(
                message=f"El plan con código '{plan_code}' no existe o está inactivo.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        subscription = SubscriptionService.assign_or_renew_plan(
            company=company,
            plan=plan,
            notes=f"Plan cambiado por usuario {request.user.email}",
        )

        return ApiResponse.success(
            data=SubscriptionSerializer(subscription).data,
            message=f"Plan cambiado exitosamente a {plan.name}.",
            status_code=status.HTTP_200_OK,
        )
