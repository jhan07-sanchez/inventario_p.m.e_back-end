from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema

from apps.core.docs.api_response_schema import build_api_response_schema
from apps.core.docs.error_schemas import ApiErrorResponseSerializer
from apps.configuration.serializers import ConfigurationAuditSerializer

pagination_parameters = [
    OpenApiParameter(
        name="page",
        type=OpenApiTypes.INT,
        location=OpenApiParameter.QUERY,
        description="Número de página.",
        required=False,
    ),
    OpenApiParameter(
        name="page_size",
        type=OpenApiTypes.INT,
        location=OpenApiParameter.QUERY,
        description="Resultados por página.",
        required=False,
    ),
]

configuration_audit_list_schema = extend_schema(
    tags=["Configuration Audits"],
    summary="Listar Auditoría de Configuración",
    description=(
        "Obtiene el historial de cambios realizados en los parámetros globales. "
        "Incluye el valor anterior, el valor nuevo, y el usuario que realizó el cambio."
    ),
    parameters=pagination_parameters,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="ConfigurationAuditListResponse",
                data_serializer=ConfigurationAuditSerializer,
                is_list=True,
            ),
            description="Historial obtenido correctamente.",
        ),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
        403: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

configuration_audit_detail_schema = extend_schema(
    tags=["Configuration Audits"],
    summary="Obtener Registro de Auditoría",
    description="Obtiene el detalle de un registro de auditoría específico.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="ID del registro de auditoría.",
            required=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="ConfigurationAuditDetailResponse",
                data_serializer=ConfigurationAuditSerializer,
            ),
        ),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
        403: OpenApiResponse(response=ApiErrorResponseSerializer),
        404: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)
