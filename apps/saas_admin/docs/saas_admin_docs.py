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
from apps.saas_admin.serializers.tenant_serializer import (
    GlobalMetricsSerializer,
    ImpersonateRequestSerializer,
    TenantActionSerializer,
    TenantDetailSerializer,
    TenantListSerializer,
)

saas_tenant_list_schema = extend_schema(
    tags=["SaaS Admin"],
    summary="Listar Empresas de la Plataforma",
    description=(
        "Obtiene el catálogo global de empresas (Tenants) registradas en el SaaS con soporte "
        "de búsqueda textual (razón social, nombre comercial, NIT o correo), filtros por "
        "estado empresarial, plan contratado y estado de suscripción. "
        "Paginado uniformemente mediante CustomPagination con metadatos completos."
    ),
    parameters=[
        OpenApiParameter(
            name="search",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Búsqueda por coincidencia en razón social, nombre comercial, NIT o email.",
            required=False,
        ),
        OpenApiParameter(
            name="status",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Filtro por estado de la empresa.",
            enum=["ACTIVE", "SUSPENDED", "PENDING_VERIFICATION", "CANCELLED"],
            required=False,
        ),
        OpenApiParameter(
            name="plan_code",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Filtro por código del plan activo contratado (ej. BASIC, PRO, ENTERPRISE).",
            required=False,
        ),
        OpenApiParameter(
            name="subscription_status",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Filtro por estado de la suscripción actual.",
            enum=["TRIAL", "ACTIVE", "PAST_DUE", "CANCELLED", "EXPIRED"],
            required=False,
        ),
        OpenApiParameter(
            name="page",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Número de página solicitada (por defecto 1).",
            required=False,
        ),
        OpenApiParameter(
            name="page_size",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Cantidad de registros por página (por defecto 10, máximo 100).",
            required=False,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="SaaSTenantListApiResponse",
                data_serializer=TenantListSerializer,
                is_list=True,
            ),
            description="Listado de empresas obtenido correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Acceso denegado: se requieren privilegios de Superadministrador global.",
        ),
    },
)

saas_tenant_detail_schema = extend_schema(
    tags=["SaaS Admin"],
    summary="Detalle Administrativo de Empresa",
    description=(
        "Obtiene la radiografía administrativa, técnica y financiera completa de una empresa: "
        "información legal y fiscal, datos del propietario, estado de la suscripción vigente, "
        "histórico de suscripciones, pagos registrados en pasarelas y total de miembros activos."
    ),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador numérico único de la empresa (id_company).",
            required=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="SaaSTenantDetailApiResponse",
                data_serializer=TenantDetailSerializer,
            ),
            description="Ficha técnica de la empresa obtenida exitosamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token no provisto o expirado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Acceso denegado: reservado exclusivamente para Superadministradores.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="La empresa especificada no existe en la plataforma.",
        ),
    },
)

saas_global_metrics_schema = extend_schema(
    tags=["SaaS Admin"],
    summary="Métricas Globales y KPIs del SaaS",
    description=(
        "Calcula en tiempo real los indicadores estratégicos de la plataforma: "
        "Monthly Recurring Revenue (MRR) normalizado según ciclo mensual y anual (anual / 12), "
        "conteo de empresas activas y suspendidas, pruebas gratuitas vigentes (trials), "
        "suscripciones en mora/expiradas y recaudación aprobada del mes e histórica."
    ),
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="SaaSGlobalMetricsApiResponse",
                data_serializer=GlobalMetricsSerializer,
            ),
            description="Métricas consolidadas obtenidas correctamente.",
            examples=[
                OpenApiExample(
                    "Ejemplo KPIs SaaS",
                    value={
                        "success": True,
                        "code": "SAAS_METRICS_FETCHED",
                        "message": "Métricas globales del SaaS obtenidas correctamente.",
                        "data": {
                            "total_companies": 142,
                            "active_companies": 130,
                            "suspended_companies": 12,
                            "active_trials": 28,
                            "active_paid_subscriptions": 95,
                            "past_due_subscriptions": 4,
                            "expired_subscriptions": 15,
                            "mrr": 4750.50,
                            "current_month_revenue": 5200.00,
                            "total_historical_revenue": 68400.00,
                        },
                        "errors": None,
                    },
                )
            ],
        ),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
        403: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

saas_tenant_action_schema = extend_schema(
    tags=["SaaS Admin"],
    summary="Ejecutar Acción Administrativa sobre Empresa",
    description=(
        "Ejecuta una acción administrativa sobre una empresa específica:\n\n"
        "- **`suspend`**: Suspende preventivamente la operatividad de la organización.\n"
        "- **`reactivate`**: Restablece el estado activo de una empresa previamente suspendida.\n"
        "- **`extend-trial`**: Adiciona días a la prueba gratuita de la empresa y reactiva el acceso si estaba vencido.\n\n"
        "Todas las acciones se ejecutan en transacciones atómicas y generan un registro auditable inmutable en AuditLog."
    ),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la empresa destino.",
            required=True,
        )
    ],
    request=TenantActionSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="SaaSTenantActionExecutedApiResponse",
            ),
            description="Acción administrativa ejecutada correctamente.",
            examples=[
                OpenApiExample(
                    "Ejemplo Suspensión",
                    value={
                        "success": True,
                        "code": "SAAS_ACTION_EXECUTED",
                        "message": "Acción administrativa ejecutada correctamente.",
                        "data": {
                            "id_company": 14,
                            "status": "SUSPENDED",
                        },
                        "errors": None,
                    },
                )
            ],
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="Parámetros inválidos, acción no soportada o transición de estado ilegal.",
        ),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
        403: OpenApiResponse(response=ApiErrorResponseSerializer),
        404: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

saas_tenant_impersonate_schema = extend_schema(
    tags=["SaaS Admin"],
    summary="Iniciar Sesión de Soporte Técnico (Impersonación)",
    description=(
        "Inicia una sesión de soporte técnico temporal y controlada mediante un JWT efímero (15 minutos) "
        "confinado estrictamente a la empresa objetivo.\n\n"
        "**Reglas de seguridad innegociables:**\n"
        "1. Exclusivo para Superadministradores autenticados.\n"
        "2. Prohíbe terminantemente la impersonación de otros Superadministradores.\n"
        "3. Prohíbe impersonaciones encadenadas (no es posible impersonar desde una sesión ya impersonada).\n"
        "4. El usuario objetivo debe pertenecer activamente a la empresa destino.\n"
        "5. El token emitido incluye claims criptográficos (`is_impersonated: True`, `impersonator_id`, etc.) "
        "y NO incluye Refresh Token para prevenir extensiones silenciosas.\n"
        "6. Todo inicio de sesión de soporte queda registrado en el AuditLog del sistema."
    ),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la empresa donde se prestará el soporte.",
            required=True,
        )
    ],
    request=ImpersonateRequestSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="SaaSImpersonationStartedApiResponse",
            ),
            description="Sesión temporal de soporte generada exitosamente.",
            examples=[
                OpenApiExample(
                    "Ejemplo JWT Impersonación",
                    value={
                        "success": True,
                        "code": "SAAS_IMPERSONATION_STARTED",
                        "message": "Sesión de soporte iniciada correctamente.",
                        "data": {
                            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "token_type": "Bearer",
                            "expires_in": 900,
                            "target_user": {
                                "id_user": 25,
                                "username": "carlos_empresa",
                                "email": "carlos@tenant.com",
                                "full_name": "Carlos Gomez",
                            },
                            "target_company": {
                                "id_company": 14,
                                "business_name": "Distribuidora del Norte SAS",
                                "tax_id": "900555444-1",
                            },
                            "impersonated_by": {
                                "id_user": 1,
                                "email": "superadmin@saas.com",
                                "reason": "Soporte técnico por incidencia #1042 en conciliación bancaria",
                            },
                        },
                        "errors": None,
                    },
                )
            ],
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="Motivo no suministrado, usuario fuera de la empresa o intento de impersonar superadministrador.",
        ),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
        403: OpenApiResponse(response=ApiErrorResponseSerializer),
        404: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)
