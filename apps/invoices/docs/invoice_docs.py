from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema

from apps.core.docs.api_response_schema import build_api_response_schema
from apps.core.docs.error_schemas import (
    ApiErrorResponseSerializer,
    ValidationErrorResponseSerializer,
)
from apps.invoices.serializers import (
    InvoiceCreateSerializer,  # Asegúrate de importar el de creación si lo usas en request
    InvoiceListSerializer,
    InvoiceRetrieveSerializer,
    InvoiceUpdateSerializer,  # Asegúrate de importar el de actualización si lo usas en request
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
        description="Cantidad de facturas por página.",
        required=False,
    ),
    OpenApiParameter(
        name="document_type",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description="Filtrar por tipo de documento (e.g., PURCHASE_INVOICE).",
        required=False,
    ),
    OpenApiParameter(
        name="status",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description="Filtrar por estado (DRAFT, ISSUED, CANCELLED).",
        required=False,
    ),
    OpenApiParameter(
        name="is_active",
        type=OpenApiTypes.BOOL,
        location=OpenApiParameter.QUERY,
        description="Filtrar por estado activo/inactivo.",
        required=False,
    ),
]


invoice_list_schema = extend_schema(
    tags=["Invoices"],
    summary="Listar facturas",
    description=(
        "Obtiene el listado paginado de todas las facturas en el sistema, con opciones de filtrado."
    ),
    parameters=pagination_parameters,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="InvoiceListResponse",
                data_serializer=InvoiceListSerializer,
                is_list=True,
            ),
            description="Listado de facturas obtenido correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para consultar facturas.",
        ),
    },
)


invoice_retrieve_schema = extend_schema(
    tags=["Invoices"],
    summary="Obtener factura",
    description="Obtiene toda la información detallada de una factura específica por su ID.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la factura.",
            required=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="InvoiceRetrieveResponse",
                data_serializer=InvoiceRetrieveSerializer,
            ),
            description="Factura obtenida correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para consultar facturas.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Factura no encontrada.",
        ),
    },
)


invoice_create_schema = extend_schema(
    tags=["Invoices"],
    summary="Crear factura",
    description=(
        "Crea una nueva factura en estado Borrador (DRAFT) junto con sus ítems."
    ),
    request=InvoiceCreateSerializer,  # Añadido para que la documentación refleje el body de creación
    responses={
        201: OpenApiResponse(
            response=build_api_response_schema(
                name="InvoiceCreateResponse",
                data_serializer=InvoiceRetrieveSerializer,
            ),
            description="Factura creada exitosamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="Error de validación o regla de negocio.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para crear facturas.",
        ),
    },
)


invoice_put_schema = extend_schema(
    tags=["Invoices"],
    summary="Actualizar factura",
    description=(
        "Actualiza completamente la información de la cabecera de la factura. "
        "Solo es posible si la factura está en estado DRAFT."
    ),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la factura a actualizar.",
            required=True,
        ),
    ],
    request=InvoiceUpdateSerializer,  # Añadido para documentar el body de actualización
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="InvoicePutResponse",
                data_serializer=InvoiceRetrieveSerializer,
            ),
            description="Factura actualizada correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="Error de validación o regla de negocio.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para actualizar facturas.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Factura no encontrada.",
        ),
    },
)


invoice_patch_schema = extend_schema(
    tags=["Invoices"],
    summary="Actualizar parcialmente factura",
    description=(
        "Actualiza parcialmente la información de la cabecera de la factura. "
        "Solo es posible si la factura está en estado DRAFT."
    ),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la factura a actualizar.",
            required=True,
        ),
    ],
    request=InvoiceUpdateSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="InvoicePatchResponse",
                data_serializer=InvoiceRetrieveSerializer,
            ),
            description="Factura actualizada correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="Error de validación o regla de negocio.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para actualizar facturas.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Factura no encontrada.",
        ),
    },
)


invoice_issue_schema = extend_schema(
    tags=["Invoices"],
    summary="Emitir factura",
    description=(
        "Cambia el estado de una factura de Borrador (DRAFT) a Emitida (ISSUED)."
    ),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="ID único de la factura a emitir.",
            required=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="InvoiceIssueResponse",
                data_serializer=InvoiceRetrieveSerializer,
            ),
            description="Factura emitida correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="No se pudo emitir la factura.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para emitir facturas.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Factura no encontrada.",
        ),
    },
)


invoice_cancel_schema = extend_schema(
    tags=["Invoices"],
    summary="Anular factura",
    description="Cambia el estado de la factura a Anulada (CANCELLED).",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="ID único de la factura a anular.",
            required=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="InvoiceCancelResponse",
                data_serializer=InvoiceRetrieveSerializer,
            ),
            description="Factura anulada correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="No se pudo anular la factura.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para anular facturas.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Factura no encontrada.",
        ),
    },
)


invoice_delete_schema = extend_schema(
    tags=["Invoices"],
    summary="Desactivar factura",
    description="Realiza un borrado lógico de la factura, desactivándola.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="ID de la factura a desactivar.",
            required=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="InvoiceDeleteResponse",
            ),
            description="Factura desactivada correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="No fue posible desactivar la factura.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para eliminar facturas.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Factura no encontrada.",
        ),
    },
)
