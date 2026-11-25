from rest_framework import status
from rest_framework.decorators import action
from rest_framework.views import APIView

from apps.core.utils.api_response import ApiResponse
from apps.core.views.base_viewset import BaseGenericViewSet
from apps.saas_admin.permissions import IsSaaSAdmin
from apps.saas_admin.selectors.saas_subscription_selector import (
    SaaSSubscriptionSelector,
)
from apps.saas_admin.serializers.plan_serializer import (
    SaaSPlanCreateSerializer,
    SaaSPlanSerializer,
    SaaSPlanUpdateSerializer,
)
from apps.saas_admin.services.saas_plan_service import SaaSPlanService
from apps.subscriptions.models import Plan


class SaaSPlanViewSet(BaseGenericViewSet):
    """
    ViewSet administrativo para la gestión integral del catálogo de planes comerciales.
    Permite listar (activos e inactivos), crear, editar, alternar estado y consultar detalles.
    Protegido por IsSaaSAdmin.
    """

    permission_classes = [IsSaaSAdmin]
    serializer_class = SaaSPlanSerializer

    def list(self, request, *args, **kwargs):
        """Lista todos los planes comerciales con soporte de filtros por búsqueda y estado."""
        search = request.query_params.get("search")
        is_active_param = request.query_params.get("is_active")

        is_active = None
        if is_active_param is not None:
            is_active = is_active_param.lower() in ["true", "1", "t", "yes"]

        plans_qs = SaaSSubscriptionSelector.get_all_plans(
            search=search,
            is_active=is_active,
        )

        serializer = SaaSPlanSerializer(plans_qs, many=True)
        return self.success_response(
            data=serializer.data,
            code="SAAS_PLANS_FETCHED",
            message="Planes comerciales obtenidos correctamente.",
        )

    def retrieve(self, request, pk=None, *args, **kwargs):
        """Consulta el detalle de un plan comercial específico."""
        try:
            plan = Plan.objects.get(id_plan=int(pk))
        except (Plan.DoesNotExist, ValueError):
            return self.error_response(
                message=f"No se encontró el plan comercial con ID {pk}.",
                status_code=status.HTTP_404_NOT_FOUND,
                code="PLAN_NOT_FOUND",
            )

        serializer = SaaSPlanSerializer(plan)
        return self.success_response(
            data=serializer.data,
            code="SAAS_PLAN_DETAIL_FETCHED",
            message="Detalle de plan obtenido correctamente.",
        )

    def create(self, request, *args, **kwargs):
        """Crea un nuevo plan comercial con validación de precios, códigos, límites y módulos."""
        serializer = SaaSPlanCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plan = SaaSPlanService.create_plan(
            validated_data=serializer.validated_data,
            actor_user=request.user,
        )

        return self.success_response(
            data=SaaSPlanSerializer(plan).data,
            code="SAAS_PLAN_CREATED",
            message=f"Plan comercial '{plan.name}' creado exitosamente.",
            status_code=status.HTTP_201_CREATED,
        )

    def update(self, request, pk=None, *args, **kwargs):
        """Edita un plan comercial existente."""
        serializer = SaaSPlanUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        plan = SaaSPlanService.update_plan(
            plan_id=int(pk),
            validated_data=serializer.validated_data,
            actor_user=request.user,
        )

        return self.success_response(
            data=SaaSPlanSerializer(plan).data,
            code="SAAS_PLAN_UPDATED",
            message=f"Plan comercial '{plan.name}' actualizado correctamente.",
        )

    def partial_update(self, request, pk=None, *args, **kwargs):
        return self.update(request, pk, *args, **kwargs)

    @action(detail=False, methods=["get"], url_path="available-modules")
    def available_modules(self, request):
        """
        Retorna el catálogo dinámico de módulos y submódulos disponibles en el ERP
        para la configuración y edición de planes comerciales.
        """
        from apps.subscriptions.services.company_entitlement_service import (
            CompanyEntitlementService,
        )

        catalog = CompanyEntitlementService.get_catalog()
        return self.success_response(
            data=catalog,
            code="SAAS_AVAILABLE_MODULES_FETCHED",
            message="Catálogo dinámico de módulos obtenido correctamente.",
        )

    @action(detail=True, methods=["patch"], url_path="toggle-status")
    def toggle_status(self, request, pk=None):
        """Alterna el estado activo/inactivo de un plan comercial."""
        plan = SaaSPlanService.toggle_status(
            plan_id=int(pk),
            actor_user=request.user,
        )
        estado_txt = "activado" if plan.is_active else "desactivado"

        return self.success_response(
            data=SaaSPlanSerializer(plan).data,
            code="SAAS_PLAN_STATUS_TOGGLED",
            message=f"Plan comercial '{plan.name}' {estado_txt} correctamente.",
        )


class SaaSAvailableModulesView(APIView):
    """
    Vista administrativa independiente para consultar el catálogo dinámico
    de módulos y submódulos reales de P.M.E.
    Accesible en GET /api/v1/saas-admin/modules/
    """

    permission_classes = [IsSaaSAdmin]

    def get(self, request, *args, **kwargs):
        from apps.subscriptions.services.company_entitlement_service import (
            CompanyEntitlementService,
        )

        catalog = CompanyEntitlementService.get_catalog()
        return ApiResponse.success(
            message="Catálogo dinámico de módulos obtenido correctamente.",
            code="SAAS_AVAILABLE_MODULES_FETCHED",
            data=catalog,
            status_code=status.HTTP_200_OK,
        )
