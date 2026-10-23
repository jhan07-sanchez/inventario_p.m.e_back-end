from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)

from apps.configuration.serializers import (
    GlobalParameterCreateSerializer,
    GlobalParameterSerializer,
    GlobalParameterUpdateSerializer,
)
from apps.core.docs.api_response_schema import build_api_response_schema
from apps.core.docs.error_schemas import (
    ApiErrorResponseSerializer,
    ValidationErrorResponseSerializer,
)

pagination_parameters = [
    OpenApiParameter(
        name="page",
        type=OpenApiTypes.INT,
        location=OpenApiParameter.QUERY,
        description="Número de página para la paginación.",
        required=False,
    ),
    OpenApiParameter(
        name="page_size",
        type=OpenApiTypes.INT,
        location=OpenApiParameter.QUERY,
        description="Cantidad de resultados por página.",
        required=False,
    ),
]

global_parameter_list_schema = extend_schema(
    tags=["Configuration"],
    summary="Listar Parámetros Globales",
    description="Obtiene una lista paginada de todos los parámetros configurables del sistema.",
    parameters=pagination_parameters,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="GlobalParameterListApiResponse",
                data_serializer=GlobalParameterSerializer,
                is_list=True,
            ),
            description="Parámetros obtenidos correctamente.",
        ),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
        403: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

global_parameter_detail_schema = extend_schema(
    tags=["Configuration"],
    summary="Obtener Parámetro Global",
    description="Obtiene los detalles de un parámetro por su ID.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único del parámetro.",
            required=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="GlobalParameterDetailApiResponse",
                data_serializer=GlobalParameterSerializer,
            ),
        ),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
        403: OpenApiResponse(response=ApiErrorResponseSerializer),
        404: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

global_parameter_create_schema = extend_schema(
    tags=["Configuration"],
    summary="Crear Parámetro Global",
    description="Registra un nuevo parámetro en el sistema.",
    request=GlobalParameterCreateSerializer,
    responses={
        201: OpenApiResponse(
            response=build_api_response_schema(
                name="GlobalParameterCreateApiResponse",
                data_serializer=GlobalParameterSerializer,
            ),
        ),
        400: OpenApiResponse(response=ValidationErrorResponseSerializer),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
        403: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
    examples=[
        OpenApiExample(
            "Crear Parámetro (IVA)",
            request_only=True,
            value={
                "key": "DEFAULT_TAX_RATE",
                "value": "0.19",
                "data_type": "DECIMAL",
                "description": "Porcentaje de IVA por defecto.",
            },
        )
    ],
)

global_parameter_update_schema = extend_schema(
    tags=["Configuration"],
    summary="Actualizar Parámetro Global",
    description="Actualiza completamente un parámetro existente.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            required=True,
        )
    ],
    request=GlobalParameterUpdateSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="GlobalParameterUpdateApiResponse",
                data_serializer=GlobalParameterSerializer,
            ),
        ),
        400: OpenApiResponse(response=ValidationErrorResponseSerializer),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
        403: OpenApiResponse(response=ApiErrorResponseSerializer),
        404: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

global_parameter_partial_update_schema = extend_schema(
    tags=["Configuration"],
    summary="Actualizar Parcialmente Parámetro",
    description="Actualiza de forma parcial un parámetro existente.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            required=True,
        )
    ],
    request=GlobalParameterUpdateSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="GlobalParameterPartialUpdateApiResponse",
                data_serializer=GlobalParameterSerializer,
            ),
        ),
        400: OpenApiResponse(response=ValidationErrorResponseSerializer),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
        403: OpenApiResponse(response=ApiErrorResponseSerializer),
        404: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

global_parameter_delete_schema = extend_schema(
    tags=["Configuration"],
    summary="Desactivar Parámetro Global",
    description="Realiza un borrado lógico del parámetro.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            required=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(name="GlobalParameterDeleteApiResponse"),
        ),
        400: OpenApiResponse(response=ValidationErrorResponseSerializer),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
        403: OpenApiResponse(response=ApiErrorResponseSerializer),
        404: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

global_parameter_restore_schema = extend_schema(
    tags=["Configuration"],
    summary="Restaurar Parámetro Global",
    description="Restaura un parámetro previamente desactivado.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            required=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="GlobalParameterRestoreApiResponse"
            ),
        ),
        400: OpenApiResponse(response=ValidationErrorResponseSerializer),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
        403: OpenApiResponse(response=ApiErrorResponseSerializer),
        404: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)
