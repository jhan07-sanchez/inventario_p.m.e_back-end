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
from apps.sales.serializers.sale_serializer import (
    SaleCreateSerializer,
    SaleListSerializer,
    SaleRetrieveSerializer,
    SaleUpdateSerializer,
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
        name="customer_id",
        type=OpenApiTypes.INT,
        location=OpenApiParameter.QUERY,
        description="Filtrar por identificador del cliente.",
        required=False,
    ),
    OpenApiParameter(
        name="status",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description="Filtrar por estado de la venta (PENDING, COMPLETED, CANCELLED).",
        required=False,
    ),
    OpenApiParameter(
        name="invoice_number",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description="Filtrar por número de factura asociada.",
        required=False,
    ),
    OpenApiParameter(
        name="invoice_status",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description="Filtrar por estado de la factura asociada.",
        required=False,
    ),
    OpenApiParameter(
        name="is_active",
        type=OpenApiTypes.BOOL,
        location=OpenApiParameter.QUERY,
        description="Filtrar por ventas activas o inactivas.",
        required=False,
    ),
]

sale_list_schema = extend_schema(
    tags=["Sales"],
    summary="Listar Ventas",
    description=(
        "Obtiene una lista paginada de ventas registradas en el sistema. "
        "Cada venta incluye el resumen de sus facturas asociadas."
    ),
    parameters=pagination_parameters,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="SaleListApiResponse",
                data_serializer=SaleListSerializer,
                is_list=True,
            ),
            description="Ventas obtenidas correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para consultar ventas.",
        ),
    },
)

sale_detail_schema = extend_schema(
    tags=["Sales"],
    summary="Obtener Venta",
    description=(
        "Obtiene los detalles completos de una venta por su ID, incluyendo "
        "sus líneas de detalle y el resumen de sus facturas asociadas."
    ),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la venta.",
            required=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="SaleDetailApiResponse",
                data_serializer=SaleRetrieveSerializer,
            ),
            description="Venta obtenida correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para consultar ventas.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Venta no encontrada.",
        ),
    },
)

sale_create_schema = extend_schema(
    tags=["Sales"],
    summary="Crear Venta",
    description=(
        "Crea una nueva venta en estado PENDING junto con sus detalles. "
        "Los montos se calculan automáticamente."
    ),
    request=SaleCreateSerializer,
    responses={
        201: OpenApiResponse(
            response=build_api_response_schema(
                name="SaleCreateApiResponse",
                data_serializer=SaleRetrieveSerializer,
            ),
            description="Venta creada correctamente.",
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
            description="El usuario no tiene permiso para crear ventas.",
        ),
    },
    examples=[
        OpenApiExample(
            "Crear Venta",
            request_only=True,
            value={
                "customer_id": 1,
                "payment_method": "CASH",
                "discount": "0.00",
                "tax": "0.00",
                "notes": "Venta inicial.",
                "details": [
                    {
                        "product_id": 10,
                        "quantity": "2.00",
                        "unit_price": "12500.00",
                        "discount": "0.00",
                    }
                ],
            },
        )
    ],
)

sale_update_schema = extend_schema(
    tags=["Sales"],
    summary="Actualizar Venta",
    description="Permite actualizar completamente una venta que se encuentre en estado PENDING.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la venta a actualizar.",
            required=True,
        )
    ],
    request=SaleUpdateSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="SaleUpdateApiResponse",
                data_serializer=SaleRetrieveSerializer,
            ),
            description="Venta actualizada correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="Los datos enviados no son válidos o la venta no está en estado PENDING.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para actualizar ventas.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Venta no encontrada.",
        ),
    },
)

sale_partial_update_schema = extend_schema(
    tags=["Sales"],
    summary="Actualizar parcialmente venta",
    description="Permite actualizar de forma parcial los campos de una venta en estado PENDING.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la venta a actualizar parcialmente.",
            required=True,
        )
    ],
    request=SaleUpdateSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="SalePartialUpdateApiResponse",
                data_serializer=SaleRetrieveSerializer,
            ),
            description="Venta actualizada correctamente.",
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
            description="El usuario no tiene permiso para actualizar ventas.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Venta no encontrada.",
        ),
    },
)

sale_delete_schema = extend_schema(
    tags=["Sales"],
    summary="Desactivar Venta",
    description="Realiza un borrado lógico de la venta, desactivándola.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la venta a desactivar.",
            required=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(name="SaleDeleteApiResponse"),
            description="Venta desactivada correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="No fue posible desactivar la venta.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para desactivar ventas.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Venta no encontrada.",
        ),
    },
)

sale_restore_schema = extend_schema(
    tags=["Sales"],
    summary="Restaurar Venta",
    description="Restaura una venta desactivada lógicamente.",
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
                name="SaleRestoreApiResponse",
            ),
            description="Venta restaurada correctamente.",
        ),
        400: OpenApiResponse(response=ValidationErrorResponseSerializer),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
        403: OpenApiResponse(response=ApiErrorResponseSerializer),
        404: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

sale_complete_schema = extend_schema(
    tags=["Sales"],
    summary="Completar Venta",
    description="Transita una venta de PENDING a COMPLETED y descuenta los productos del inventario.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la venta a completar.",
            required=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(name="SaleCompleteApiResponse"),
            description="Venta completada y stock actualizado con éxito.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="La venta no puede ser completada en su estado actual.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para completar ventas.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Venta no encontrada.",
        ),
    },
)

sale_cancel_schema = extend_schema(
    tags=["Sales"],
    summary="Cancelar Venta",
    description="Cancela una venta y revierte las salidas de inventario cuando corresponde.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la venta a cancelar.",
            required=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(name="SaleCancelApiResponse"),
            description="Venta cancelada con éxito.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="La venta no se puede cancelar.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para cancelar ventas.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Venta no encontrada.",
        ),
    },
)
