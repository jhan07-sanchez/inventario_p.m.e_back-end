from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)

from apps.core.docs.api_response_schema import build_api_response_schema
from apps.core.docs.error_schemas import (
    ApiErrorResponseSerializer,
)
from apps.inventory.serializers.inventory_serializer import (
    InventoryMovementDetailSerializer,
    InventoryMovementListSerializer,
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
    OpenApiParameter(
        name="search",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description=(
            "Término de búsqueda. Filtra por código de producto, "
            "nombre de producto, código de barras o referencia del movimiento."
        ),
        required=False,
    ),
]

movement_list_schema = extend_schema(
    tags=["Inventory"],
    summary="Listar movimientos de inventario",
    description=(
        "Obtiene el listado paginado de todos los movimientos de inventario "
        "registrados en el sistema (entradas, salidas y ajustes). "
        "Permite búsqueda por código, nombre o barcode del producto y por referencia."
    ),
    parameters=pagination_parameters,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="MovementListApiResponse",
                data_serializer=InventoryMovementListSerializer,
                is_list=True,
            ),
            description="Movimientos obtenidos correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para consultar movimientos.",
        ),
    },
)

movement_detail_schema = extend_schema(
    tags=["Inventory"],
    summary="Obtener movimiento de inventario",
    description=(
        "Obtiene la información detallada de un movimiento de inventario específico."
    ),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único del movimiento.",
            required=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="MovementDetailApiResponse",
                data_serializer=InventoryMovementDetailSerializer,
            ),
            description="Movimiento obtenido correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para consultar movimientos.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Movimiento no encontrado.",
        ),
    },
)
