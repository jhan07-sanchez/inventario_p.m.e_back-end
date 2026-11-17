from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)

from apps.core.docs.api_response_schema import build_api_response_schema
from apps.core.docs.error_schemas import (
    ApiErrorResponseSerializer,
    ValidationErrorResponseSerializer,
)
from apps.subscriptions.serializers.subscription_serializers import (
    ChangePlanRequestSerializer,
    PlanSerializer,
    SubscriptionSerializer,
)

plan_list_schema = extend_schema(
    tags=["Subscriptions"],
    summary="Listar Planes Comerciales",
    description=(
        "Obtiene el catálogo de planes comerciales activos ofrecidos por la plataforma SaaS. "
        "Detalla precios, ciclos de cobro (mensual/anual), límites de cuotas de recursos "
        "(usuarios, productos, facturas) y módulos del ERP permitidos."
    ),
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="PlanListApiResponse",
                data_serializer=PlanSerializer,
                is_list=True,
            ),
            description="Listado de planes comerciales obtenido correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Usuario no autenticado o token expirado.",
        ),
    },
)

plan_detail_schema = extend_schema(
    tags=["Subscriptions"],
    summary="Detalle de Plan Comercial",
    description="Consulta la información detallada de un plan de suscripción específico a través de su identificador único.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador numérico único del plan (id_plan).",
            required=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="PlanDetailApiResponse",
                data_serializer=PlanSerializer,
            ),
            description="Detalles del plan comercial obtenidos exitosamente.",
        ),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Plan no encontrado o inactivo.",
        ),
    },
)

subscription_current_schema = extend_schema(
    tags=["Subscriptions"],
    summary="Consultar Suscripción y Cuotas de Uso de la Empresa",
    description=(
        "Retorna la información completa de la suscripción de la empresa activa: "
        "plan contratado, estado operativo, vigencia, días de gracia, días restantes de servicio "
        "y métricas en tiempo real de consumo de recursos vs límites permitidos."
    ),
    parameters=[
        OpenApiParameter(
            name="X-Company-ID",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.HEADER,
            description="ID de la empresa activa sobre la que se consulta la suscripción.",
            required=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="CurrentSubscriptionApiResponse",
                description="Información de suscripción y métricas de consumo de cuotas.",
            ),
            description="Suscripción y métricas de consumo obtenidas correctamente.",
            examples=[
                OpenApiExample(
                    "Ejemplo Suscripción Actual",
                    value={
                        "success": True,
                        "code": "SUBSCRIPTION_FETCHED",
                        "message": "Información de suscripción obtenida exitosamente.",
                        "data": {
                            "subscription": {
                                "id_subscription": 12,
                                "company": 5,
                                "plan": {
                                    "id_plan": 2,
                                    "code": "PRO",
                                    "name": "Plan Pro Mensual",
                                    "price": "79.99",
                                    "billing_cycle": "MONTHLY",
                                    "billing_cycle_display": "Mensual",
                                    "max_users": 5,
                                    "max_products": 500,
                                    "max_invoices_per_month": 300,
                                    "enabled_modules": [
                                        "inventory",
                                        "sales",
                                        "invoices",
                                        "purchases",
                                        "finance",
                                    ],
                                    "is_active": True,
                                },
                                "status": "ACTIVE",
                                "status_display": "Activa",
                                "start_date": "2026-01-01T00:00:00Z",
                                "end_date": "2026-02-01T00:00:00Z",
                                "grace_period_days": 5,
                                "auto_renew": True,
                                "is_valid": True,
                                "is_in_grace_period": False,
                                "days_remaining": 16,
                                "notes": "",
                            },
                            "metrics": {
                                "users_count": 3,
                                "users_limit": 5,
                                "products_count": 142,
                                "products_limit": 500,
                                "invoices_this_month": 48,
                                "invoices_limit": 300,
                            },
                        },
                        "errors": None,
                    },
                )
            ],
        ),
        400: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="No hay una empresa seleccionada en el contexto de la petición.",
        ),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

subscription_change_plan_schema = extend_schema(
    tags=["Subscriptions"],
    summary="Cambiar o Renovar Plan de Suscripción",
    description=(
        "Permite cambiar el plan comercial contratado o renovar el servicio de la empresa activa. "
        "Esta operación está reservada exclusivamente para el Propietario o Administrador de la empresa. "
        "Ajusta automáticamente las cuotas de usuarios, productos y módulos disponibles."
    ),
    parameters=[
        OpenApiParameter(
            name="X-Company-ID",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.HEADER,
            description="ID de la empresa activa para la actualización del plan.",
            required=True,
        )
    ],
    request=ChangePlanRequestSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="SubscriptionChangePlanApiResponse",
                data_serializer=SubscriptionSerializer,
            ),
            description="Plan comercial cambiado y aplicado exitosamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="Código de plan ausente o sin contexto de empresa.",
        ),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Acceso denegado: solo el dueño o administrador puede cambiar de plan.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El plan comercial especificado no existe o se encuentra inactivo.",
        ),
    },
)
