from dataclasses import asdict

from rest_framework.decorators import action

from apps.company_info.models import CompanyInfo
from apps.core.pagination.custom_pagination import CustomPagination
from apps.core.views.base_viewset import BaseGenericViewSet
from apps.saas_admin.docs.saas_admin_docs import (
    saas_global_metrics_schema,
    saas_tenant_action_schema,
    saas_tenant_detail_schema,
    saas_tenant_impersonate_schema,
    saas_tenant_list_schema,
)
from apps.saas_admin.permissions import IsSaaSAdmin
from apps.saas_admin.selectors.saas_admin_selector import SaaSAdminSelector
from apps.saas_admin.serializers.tenant_serializer import (
    GlobalMetricsSerializer,
    ImpersonateRequestSerializer,
    TenantActionSerializer,
    TenantDetailSerializer,
    TenantListSerializer,
)
from apps.saas_admin.services.impersonation_service import ImpersonationService
from apps.saas_admin.services.tenant_management_service import TenantManagementService


class SaaSAdminViewSet(BaseGenericViewSet):
    """
    ViewSet administrativo global para el propietario del SaaS.
    Gestiona todas las empresas de la plataforma, métricas globales,
    acciones administrativas y sesiones de soporte técnico por impersonación.

    Protegido estrictamente por el permiso IsSaaSAdmin (superuser=True).
    """

    permission_classes = [IsSaaSAdmin]
    pagination_class = CustomPagination
    serializer_class = TenantListSerializer

    def get_throttles(self):
        """Aplica alcances de limitación (throttling) específicos para acciones críticas."""
        if self.action == "impersonate":
            self.throttle_scope = "saas_impersonate"
        elif self.action == "execute_action":
            self.throttle_scope = "saas_action"
        return super().get_throttles()

    @saas_tenant_list_schema
    def list(self, request, *args, **kwargs):
        """
        Lista todas las empresas registradas en la plataforma con soporte para búsqueda,
        filtrado avanzado por estado de empresa, código de plan y estado de suscripción,
        además de paginación uniforme con CustomPagination.
        """
        search = request.query_params.get("search")
        status_filter = request.query_params.get("status")
        plan_code = request.query_params.get("plan_code")
        subscription_status = request.query_params.get("subscription_status")

        tenants_qs = SaaSAdminSelector.get_all_tenants(
            search=search,
            status=status_filter,
            plan_code=plan_code,
            subscription_status=subscription_status,
        )

        page = self.paginate_queryset(tenants_qs)
        if page is not None:
            serializer = TenantListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = TenantListSerializer(tenants_qs, many=True)
        return self.success_response(
            data=serializer.data,
            code="SAAS_TENANTS_FETCHED",
            message="Empresas obtenidas correctamente.",
        )

    @saas_tenant_detail_schema
    def retrieve(self, request, pk=None, *args, **kwargs):
        """
        Obtiene el detalle administrativo completo de una empresa:
        datos de la empresa, propietario, suscripción activa, historial de suscripciones,
        pagos registrados y total de miembros de equipo.
        """
        detail_data = SaaSAdminSelector.get_tenant_detail(company_id=int(pk))
        serializer = TenantDetailSerializer(detail_data)

        return self.success_response(
            data=serializer.data,
            code="SAAS_TENANT_DETAIL_FETCHED",
            message="Detalle de empresa obtenido correctamente.",
        )

    @saas_global_metrics_schema
    @action(detail=False, methods=["get"], url_path="metrics")
    def metrics(self, request):
        """
        Consulta las métricas globales del SaaS:
        MRR normalizado, empresas activas/suspendidas, trials vigentes,
        suscripciones vencidas y recaudación del mes/histórica.
        """
        metrics_data = SaaSAdminSelector.get_global_metrics()
        serializer = GlobalMetricsSerializer(metrics_data)

        return self.success_response(
            data=serializer.data,
            code="SAAS_METRICS_FETCHED",
            message="Métricas globales del SaaS obtenidas correctamente.",
        )

    @saas_tenant_action_schema
    @action(detail=True, methods=["post"], url_path="actions")
    def execute_action(self, request, pk=None):
        """
        Ejecuta acciones administrativas sobre una empresa:
        - suspender ('suspend')
        - reactivar ('reactivate')
        - extender período de prueba ('extend-trial')
        """
        serializer = TenantActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dto = serializer.to_dto()
        result = TenantManagementService.execute_action(
            company_id=int(pk),
            dto=dto,
            actor_user=request.user,
        )

        if isinstance(result, CompanyInfo):
            resp_data = {
                "id_company": result.id_company,
                "status": result.status,
            }
        else:
            resp_data = {
                "id_subscription": result.id_subscription,
                "status": result.status,
                "end_date": result.end_date,
            }

        return self.success_response(
            data=resp_data,
            code="SAAS_ACTION_EXECUTED",
            message="Acción administrativa ejecutada correctamente.",
        )

    @saas_tenant_impersonate_schema
    @action(detail=True, methods=["post"], url_path="impersonate")
    def impersonate(self, request, pk=None):
        """
        Inicia una sesión de soporte técnico temporal por impersonación.
        Genera un JWT de corta duración (15 min) confinado a la empresa seleccionada,
        registrando una traza auditable inmutable.
        """
        serializer = ImpersonateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dto = serializer.to_dto(company_id=int(pk))

        # Detección de impersonación encadenada
        is_already_impersonated = False
        if hasattr(request, "auth") and request.auth and hasattr(request.auth, "get"):
            is_already_impersonated = bool(request.auth.get("is_impersonated", False))

        result_dto = ImpersonationService.start_impersonation(
            admin_user=request.user,
            dto=dto,
            is_already_impersonated=is_already_impersonated,
        )

        return self.success_response(
            data=asdict(result_dto),
            code="SAAS_IMPERSONATION_STARTED",
            message="Sesión de soporte iniciada correctamente.",
        )

    @action(detail=False, methods=["post"], url_path="impersonate/end")
    def end_impersonate(self, request):
        """
        Finaliza una sesión de soporte técnico por impersonación y registra la traza de salida.
        """
        auth_payload = {}
        if hasattr(request, "auth") and request.auth and hasattr(request.auth, "get"):
            auth_payload = {
                "impersonator_id": request.auth.get("impersonator_id"),
                "impersonated_company": request.auth.get("impersonated_company"),
            }

        result = ImpersonationService.end_impersonation(
            actor_user=request.user,
            auth_payload=auth_payload,
        )

        return self.success_response(
            data=result,
            code="SAAS_IMPERSONATION_ENDED",
            message="Sesión de soporte finalizada.",
        )
