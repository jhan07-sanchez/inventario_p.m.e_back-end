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
from apps.purchases.serializers.purchase_serializer import (
    PurchaseCreateSerializer,
    PurchaseListSerializer,
    PurchaseRetrieveSerializer,
    PurchaseUpdateSerializer,
)

# Parámetros de paginación reutilizables
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

# Esquemas individuales para cada acción del ViewSet

purchase_list_schema = extend_schema(
    tags=["Purchases"],
    summary="Listar Compras",
    description="Obtiene una lista paginada de todas las compras registradas en el sistema.",
    parameters=pagination_parameters,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="PurchaseListApiResponse",
                data_serializer=PurchaseListSerializer,
                is_list=True,
            ),
            description="Compras obtenidas correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para consultar compras.",
        ),
    },
)

purchase_detail_schema = extend_schema(
    tags=["Purchases"],
    summary="Obtener Compra",
    description="Obtiene los detalles completos de una compra por su ID, incluyendo sus líneas de detalle.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la compra.",
            required=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="PurchaseDetailApiResponse",
                data_serializer=PurchaseRetrieveSerializer,
            ),
            description="Compra obtenida correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para consultar compras.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Compra no encontrada.",
        ),
    },
)

purchase_create_schema = extend_schema(
    tags=["Purchases"],
    summary="Crear Compra",
    description=(
        "Crea una nueva compra en estado DRAFT junto con sus detalles. "
        "Los montos se calculan automáticamente."
    ),
    request=PurchaseCreateSerializer,
    responses={
        201: OpenApiResponse(
            response=build_api_response_schema(
                name="PurchaseCreateApiResponse",
                data_serializer=PurchaseRetrieveSerializer,
            ),
            description="Compra creada correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="Los datos enviados no son válidos.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para crear compras.",
        ),
    },
    examples=[
        OpenApiExample(
            "Crear Compra",
            request_only=True,
            value={
                "supplier_id": 1,
                "issue_date": "2026-06-01",
                "observations": "Compra inicial de inventario.",
                "items": [
                    {
                        "product_id": 10,
                        "quantity": 50,
                        "unit_price": 12500.00,
                    }
                ],
            },
        )
    ],
)

purchase_update_schema = extend_schema(
    tags=["Purchases"],
    summary="Actualizar Compra",
    description="Permite actualizar completamente una compra que se encuentre en estado DRAFT.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la compra a actualizar.",
            required=True,
        )
    ],
    request=PurchaseUpdateSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="PurchaseUpdateApiResponse",
                data_serializer=PurchaseRetrieveSerializer,
            ),
            description="Compra actualizada correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="Los datos enviados no son válidos o la compra no está en estado DRAFT.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para actualizar compras.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Compra no encontrada.",
        ),
    },
)

purchase_partial_update_schema = extend_schema(
    tags=["Purchases"],
    summary="Actualizar parcialmente compra",
    description="Permite actualizar de forma parcial los campos de una compra en estado DRAFT.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la compra a actualizar parcialmente.",
            required=True,
        )
    ],
    request=PurchaseUpdateSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="PurchasePartialUpdateApiResponse",
                data_serializer=PurchaseRetrieveSerializer,
            ),
            description="Compra actualizada correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="Datos no válidos.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para actualizar compras.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Compra no encontrada.",
        ),
    },
)

purchase_delete_schema = extend_schema(
    tags=["Purchases"],
    summary="Desactivar Compra",
    description="Realiza un borrado lógico de la compra, desactivándola.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la compra a desactivar.",
            required=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="PurchaseDeleteApiResponse",
            ),
            description="Compra desactivada correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="No fue posible desactivar la compra.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para desactivar compras.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Compra no encontrada.",
        ),
    },
)

purchase_restore_schema = extend_schema(
    tags=["Purchases"],
    summary="Restaurar Compra",
    description="Restaura una compra desactivada lógicamente.",
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
                name="PurchaseRestoreApiResponse",
            ),
            description="Compra restaurada correctamente.",
        ),
        400: OpenApiResponse(response=ValidationErrorResponseSerializer),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
        403: OpenApiResponse(response=ApiErrorResponseSerializer),
        404: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

purchase_confirm_schema = extend_schema(
    tags=["Purchases"],
    summary="Confirmar Compra",
    description="Transita la compra de estado DRAFT a PENDING.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la compra a confirmar.",
            required=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="PurchaseConfirmApiResponse",
            ),
            description="Compra confirmada con éxito.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="La compra no puede ser confirmada en su estado actual.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para confirmar compras.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Compra no encontrada.",
        ),
    },
)

purchase_receive_schema = extend_schema(
    tags=["Purchases"],
    summary="Recibir Compra",
    description="Transita de PENDING a RECEIVED. Incrementa el inventario de los productos.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la compra a recibir.",
            required=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="PurchaseReceiveApiResponse",
            ),
            description="Compra recibida y stock actualizado con éxito.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="La compra no puede ser recibida en su estado actual.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para recibir compras.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Compra no encontrada.",
        ),
    },
)

purchase_complete_schema = extend_schema(
    tags=["Purchases"],
    summary="Completar Compra",
    description="Transita de RECEIVED a COMPLETED.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la compra a completar.",
            required=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="PurchaseCompleteApiResponse",
            ),
            description="Compra completada con éxito.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="La compra no puede ser completada en su estado actual.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para completar compras.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Compra no encontrada.",
        ),
    },
)

purchase_cancel_schema = extend_schema(
    tags=["Purchases"],
    summary="Cancelar Compra",
    description="Cancela una compra siempre y cuando no haya sido recibida en inventario.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la compra a cancelar.",
            required=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="PurchaseCancelApiResponse",
            ),
            description="Compra cancelada con éxito.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="La compra no se puede cancelar.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para cancelar compras.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Compra no encontrada.",
        ),
    },
)
