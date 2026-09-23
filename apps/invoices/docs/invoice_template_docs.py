from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema

from apps.core.docs.api_response_schema import build_api_response_schema
from apps.core.docs.error_schemas import (
    ApiErrorResponseSerializer,
    ValidationErrorResponseSerializer,
)
from apps.invoices.serializers import (
    InvoiceTemplateCreateSerializer,  # Asegúrate de importarlo o ajustarlo según tus serializers de plantillas
    InvoiceTemplateListSerializer,
    InvoiceTemplateRetrieveSerializer,
    InvoiceTemplateUpdateSerializer,  # Asegúrate de importarlo o ajustarlo según tus serializers de plantillas
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
        description="Cantidad de plantillas por página.",
        required=False,
    ),
    OpenApiParameter(
        name="document_type",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description=(
            "Filtrar por tipo de documento: PURCHASE_INVOICE, "
            "SALE_INVOICE o POS_TICKET."
        ),
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


invoice_template_list_schema = extend_schema(
    tags=["Invoice Templates"],
    summary="Listar plantillas de factura",
    description=(
        "Obtiene el listado paginado de todas las plantillas documentales "
        "configuradas para facturas de compra, facturas de venta y tickets POS."
    ),
    parameters=pagination_parameters,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="InvoiceTemplateListResponse",
                data_serializer=InvoiceTemplateListSerializer,
                is_list=True,
            ),
            description="Listado de plantillas obtenido correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para consultar plantillas de factura.",
        ),
    },
)


invoice_template_retrieve_schema = extend_schema(
    tags=["Invoice Templates"],
    summary="Obtener plantilla de factura",
    description="Obtiene toda la información detallada de una plantilla específica por su ID.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la plantilla.",
            required=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="InvoiceTemplateRetrieveResponse",
                data_serializer=InvoiceTemplateRetrieveSerializer,
            ),
            description="Plantilla obtenida correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para consultar plantillas de factura.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Plantilla no encontrada.",
        ),
    },
)


invoice_template_create_schema = extend_schema(
    tags=["Invoice Templates"],
    summary="Crear plantilla de factura",
    description=(
        "Crea una nueva plantilla documental para facturas de compra, "
        "facturas de venta o tickets POS. POS_TICKET solo configura la "
        "presentación futura del comprobante POS."
    ),
    request=InvoiceTemplateCreateSerializer,
    responses={
        201: OpenApiResponse(
            response=build_api_response_schema(
                name="InvoiceTemplateCreateResponse",
                data_serializer=InvoiceTemplateRetrieveSerializer,
            ),
            description="Plantilla creada exitosamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="Errores de validación en los datos enviados.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para crear plantillas de factura.",
        ),
    },
)


invoice_template_put_schema = extend_schema(
    tags=["Invoice Templates"],
    summary="Actualizar plantilla de factura",
    description="Actualiza completamente la información de una plantilla documental existente.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la plantilla a actualizar.",
            required=True,
        ),
    ],
    request=InvoiceTemplateUpdateSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="InvoiceTemplatePutResponse",
                data_serializer=InvoiceTemplateRetrieveSerializer,
            ),
            description="Plantilla actualizada correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="Errores de validación en los datos enviados.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para actualizar plantillas de factura.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Plantilla no encontrada.",
        ),
    },
)


invoice_template_patch_schema = extend_schema(
    tags=["Invoice Templates"],
    summary="Actualizar parcialmente plantilla de factura",
    description="Actualiza parcialmente la información de una plantilla documental existente.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la plantilla a actualizar.",
            required=True,
        ),
    ],
    request=InvoiceTemplateUpdateSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="InvoiceTemplatePatchResponse",
                data_serializer=InvoiceTemplateRetrieveSerializer,
            ),
            description="Plantilla actualizada correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="Errores de validación en los datos enviados.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para actualizar plantillas de factura.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Plantilla no encontrada.",
        ),
    },
)


invoice_template_delete_schema = extend_schema(
    tags=["Invoice Templates"],
    summary="Desactivar plantilla de factura",
    description="Realiza un borrado lógico de la plantilla. El registro no se elimina físicamente.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la plantilla a desactivar.",
            required=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="InvoiceTemplateDeleteResponse",
            ),
            description="Plantilla desactivada correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="No fue posible desactivar la plantilla.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para eliminar plantillas de factura.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Plantilla no encontrada.",
        ),
    },
)

invoice_template_restore_schema = extend_schema(
    tags=["Invoice Templates"],
    summary="Restaurar Plantilla",
    description="Restaura una plantilla de factura desactivada lógicamente.",
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
                name="InvoiceTemplateRestoreApiResponse",
            ),
            description="Plantilla restaurada correctamente.",
        ),
        400: OpenApiResponse(response=ValidationErrorResponseSerializer),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
        403: OpenApiResponse(response=ApiErrorResponseSerializer),
        404: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)
