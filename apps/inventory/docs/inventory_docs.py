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
from apps.inventory.serializers.inventory_serializer import (
    InventoryAdjustmentSerializer,
    InventoryCreateSerializer,
    InventoryDetailSerializer,
    InventoryEntrySerializer,
    InventoryExitSerializer,
    InventoryListSerializer,
    InventoryMovementSerializer,
    InventoryUpdateSerializer,
    InventoryThresholdUpdateSerializer,
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
        description="Cantidad de inventarios por página.",
        required=False,
    ),
]


inventory_list_schema = extend_schema(
    tags=["Inventory"],
    summary="Listar inventarios",
    description=(
        "Obtiene el listado paginado de todos los registros de inventario en el sistema."
    ),
    parameters=pagination_parameters,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="InventoryListResponse",
                data_serializer=InventoryListSerializer,
                is_list=True,
            ),
            description="Listado de inventarios obtenido correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para consultar inventarios."),
        ),
    },
)


inventory_detail_schema = extend_schema(
    tags=["Inventory"],
    summary="Obtener inventario",
    description=(
        "Obtiene toda la información detallada de un registro de inventario específico."
    ),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único del inventario.",
            required=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="InventoryDetailResponse",
                data_serializer=InventoryDetailSerializer,
            ),
            description="Inventario obtenido correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para consultar inventarios."),
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Inventario no encontrado.",
        ),
    },
)


inventory_create_schema = extend_schema(
    tags=["Inventory"],
    summary="Crear inventario",
    description=(
        "Crea un nuevo registro de inventario asociado a un producto. "
        "El producto debe existir, estar activo y no poseer ya un inventario registrado."
    ),
    request=InventoryCreateSerializer,
    responses={
        201: OpenApiResponse(
            response=build_api_response_schema(
                name="InventoryCreateResponse",
                data_serializer=InventoryDetailSerializer,
            ),
            description="Inventario creado correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description=(
                "Datos inválidos. "
                "Códigos posibles: INVENTORY_ALREADY_EXISTS, "
                "PRODUCT_INACTIVE."
            ),
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para crear inventarios."),
        ),
    },
    examples=[
        OpenApiExample(
            "Crear Inventario",
            request_only=True,
            value={
                "product": 1,
                "current_stock": "100.00",
                "minimum_stock": "10.00",
                "maximum_stock": "500.00",
            },
        ),
    ],
)


inventory_update_schema = extend_schema(
    tags=["Inventory"],
    summary="Actualizar inventario",
    description=(
        "Actualiza completamente la información de un registro de inventario existente."
    ),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description=("Identificador único del inventario a actualizar."),
            required=True,
        ),
    ],
    request=InventoryUpdateSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="InventoryUpdateResponse",
                data_serializer=InventoryDetailSerializer,
            ),
            description="Inventario actualizado correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description=(
                "Datos inválidos. Códigos posibles: INVENTORY_ALREADY_EXISTS."
            ),
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para actualizar inventarios."),
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Inventario no encontrado.",
        ),
    },
)


inventory_partial_update_schema = extend_schema(
    tags=["Inventory"],
    summary="Actualizar parcialmente un inventario",
    description=(
        "Actualiza uno o varios campos de un registro de inventario existente."
    ),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description=(
                "Identificador único del inventario a actualizar parcialmente."
            ),
            required=True,
        ),
    ],
    request=InventoryUpdateSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="InventoryPartialUpdateResponse",
                data_serializer=InventoryDetailSerializer,
            ),
            description="Inventario actualizado correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description=(
                "Datos inválidos. Códigos posibles: INVENTORY_ALREADY_EXISTS."
            ),
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para actualizar inventarios."),
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Inventario no encontrado.",
        ),
    },
)


inventory_delete_schema = extend_schema(
    tags=["Inventory"],
    summary="Desactivar inventario",
    description=(
        "Desactiva lógicamente un registro de inventario del sistema."
    ),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description=("Identificador único del inventario a desactivar."),
            required=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="InventoryDeleteResponse",
            ),
            description="Inventario desactivado correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description=("No fue posible desactivar el inventario."),
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para desactivar inventarios."),
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Inventario no encontrado.",
        ),
    },
)


inventory_thresholds_schema = extend_schema(
    tags=["Inventory"],
    summary="Actualizar umbrales",
    description=(
        "Actualiza de manera específica los umbrales de stock mínimo y máximo del inventario."
    ),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description=("Identificador único del inventario."),
            required=True,
        ),
    ],
    request=InventoryThresholdUpdateSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="InventoryThresholdsResponse",
                data_serializer=InventoryDetailSerializer,
            ),
            description="Umbrales actualizados correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="Datos de umbrales inválidos.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para actualizar inventarios."),
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Inventario no encontrado.",
        ),
    },
    examples=[
        OpenApiExample(
            "Actualizar Umbrales",
            request_only=True,
            value={
                "minimum_stock": "5.00",
                "maximum_stock": "200.00",
            },
        ),
    ],
)


inventory_entry_schema = extend_schema(
    tags=["Inventory"],
    summary="Registrar entrada",
    description=(
        "Registra una entrada de stock al inventario, incrementando la cantidad actual."
    ),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description=("Identificador único del inventario."),
            required=True,
        ),
    ],
    request=InventoryEntrySerializer,
    responses={
        201: OpenApiResponse(
            response=build_api_response_schema(
                name="InventoryEntryResponse",
                data_serializer=InventoryMovementSerializer,
            ),
            description="Entrada registrada correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="No fue posible registrar la entrada (cantidad inválida).",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para registrar movimientos."),
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Inventario no encontrado.",
        ),
    },
    examples=[
        OpenApiExample(
            "Registrar Entrada",
            request_only=True,
            value={
                "quantity": "50.00",
                "reference": "FAC-00123",
                "notes": "Compra a proveedor principal",
            },
        ),
    ],
)


inventory_exit_schema = extend_schema(
    tags=["Inventory"],
    summary="Registrar salida",
    description=(
        "Registra una salida de stock del inventario, disminuyendo la cantidad actual."
    ),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description=("Identificador único del inventario."),
            required=True,
        ),
    ],
    request=InventoryExitSerializer,
    responses={
        201: OpenApiResponse(
            response=build_api_response_schema(
                name="InventoryExitResponse",
                data_serializer=InventoryMovementSerializer,
            ),
            description="Salida registrada correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="No fue posible registrar la salida (stock insuficiente o cantidad inválida).",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para registrar movimientos."),
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Inventario no encontrado.",
        ),
    },
    examples=[
        OpenApiExample(
            "Registrar Salida",
            request_only=True,
            value={
                "quantity": "5.00",
                "reference": "VEN-00456",
                "notes": "Venta en mostrador",
            },
        ),
    ],
)


inventory_adjustment_schema = extend_schema(
    tags=["Inventory"],
    summary="Registrar ajuste",
    description=(
        "Realiza un ajuste manual del stock actual del inventario a un valor específico."
    ),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description=("Identificador único del inventario."),
            required=True,
        ),
    ],
    request=InventoryAdjustmentSerializer,
    responses={
        201: OpenApiResponse(
            response=build_api_response_schema(
                name="InventoryAdjustmentResponse",
                data_serializer=InventoryMovementSerializer,
            ),
            description="Ajuste registrado correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="No fue posible registrar el ajuste.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para registrar movimientos."),
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Inventario no encontrado.",
        ),
    },
    examples=[
        OpenApiExample(
            "Registrar Ajuste",
            request_only=True,
            value={
                "new_stock": "85.00",
                "notes": "Conteo físico de inventario de fin de mes",
            },
        ),
    ],
)


inventory_movements_schema = extend_schema(
    tags=["Inventory"],
    summary="Historial de movimientos",
    description=(
        "Obtiene el listado paginado del historial de movimientos (entradas, salidas y ajustes) de un inventario."
    ),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description=("Identificador único del inventario."),
            required=True,
        ),
    ]
    + pagination_parameters,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="InventoryMovementsResponse",
                data_serializer=InventoryMovementSerializer,
                is_list=True,
            ),
            description="Historial de movimientos obtenido correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para consultar inventarios."),
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Inventario no encontrado.",
        ),
    },
)
