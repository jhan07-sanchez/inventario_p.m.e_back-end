from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema

from apps.core.docs.api_response_schema import build_api_response_schema
from apps.core.docs.error_schemas import ApiErrorResponseSerializer
from apps.core.serializers.history_serializer import GenericHistorySerializer

history_list_schema = extend_schema(
    tags=["System History"],
    summary="Listar Historial del Sistema",
    description=(
        "Obtiene el historial de cambios de un modelo específico. "
        "Puede filtrar por un objeto en particular usando `object_id`."
    ),
    parameters=[
        OpenApiParameter(
            name="model",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Nombre del modelo (user, role, userrole, etc).",
            required=True,
        ),
        OpenApiParameter(
            name="object_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="ID del objeto para filtrar su historial específico.",
            required=False,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="SystemHistoryResponse",
                data_serializer=GenericHistorySerializer,
                is_list=True,
            ),
            description="Historial obtenido correctamente.",
        ),
        400: OpenApiResponse(response=ApiErrorResponseSerializer),
        404: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)
