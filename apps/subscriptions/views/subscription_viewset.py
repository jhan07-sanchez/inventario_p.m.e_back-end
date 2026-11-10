from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.utils.api_response import ApiResponse
from apps.subscriptions.models import Plan, Subscription
from apps.subscriptions.selectors.subscription_selector import SubscriptionSelector
from apps.subscriptions.serializers.subscription_serializers import (
    PlanSerializer,
    SubscriptionSerializer,
)
from apps.subscriptions.services.subscription_service import SubscriptionService


@extend_schema_view(
    list=extend_schema(summary="Listar planes comerciales activos"),
    retrieve=extend_schema(summary="Consultar detalles de un plan"),
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

    @extend_schema(
        summary="Consultar suscripción y cuotas de consumo de la empresa actual",
        description="Retorna el estado de la suscripción, fecha de corte, días de gracia y consumo actual vs límites.",
    )
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

        return ApiResponse.success(
            data={
                "subscription": sub_data,
                "metrics": metrics,
            },
            message="Información de suscripción obtenida exitosamente.",
        )

    @extend_schema(
        summary="Cambiar o actualizar el plan de suscripción de la empresa",
        request={"application/json": {"type": "object", "properties": {"plan_code": {"type": "string"}}}},
    )
    @action(detail=False, methods=["post"], url_path="change-plan")
    def change_plan(self, request):
        company = getattr(request, "company", None)
        if not company:
            return ApiResponse.error(
                message="No hay una empresa seleccionada en el contexto actual.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Solo el dueño o administrador puede cambiar de plan
        membership = request.user.memberships.filter(company=company, is_active=True).first()
        if not membership or (not membership.is_owner and getattr(membership.role, "role_name", "") != "ADMIN"):
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
