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
from apps.suppliers.serializers.supplier_serializer import (
    SupplierCreateSerializer,
    SupplierDetailSerializer,
    SupplierListSerializer,
    SupplierUpdateSerializer,
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


supplier_list_schema = extend_schema(
    tags=["Suppliers"],
    summary="Listar proveedores",
    description=(
        "Obtiene el listado paginado de proveedores registrados en el sistema."
    ),
    parameters=pagination_parameters,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="SupplierListApiResponse",
                data_serializer=SupplierListSerializer,
                is_list=True,
            ),
            description="Proveedores obtenidos correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para consultar proveedores."),
        ),
    },
)


supplier_detail_schema = extend_schema(
    tags=["Suppliers"],
    summary="Obtener proveedor",
    description=(
        "Obtiene la información detallada de un proveedor mediante su identificador."
    ),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único del proveedor.",
            required=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="SupplierDetailApiResponse",
                data_serializer=SupplierDetailSerializer,
            ),
            description="Proveedor obtenido correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para consultar proveedores."),
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Proveedor no encontrado.",
        ),
    },
)


supplier_create_schema = extend_schema(
    tags=["Suppliers"],
    summary="Crear proveedor",
    description=(
        "Registra un nuevo proveedor en el sistema. "
        "El número de documento debe ser único."
    ),
    request=SupplierCreateSerializer,
    responses={
        201: OpenApiResponse(
            response=build_api_response_schema(
                name="SupplierCreateApiResponse",
                data_serializer=SupplierDetailSerializer,
            ),
            description="Proveedor creado correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description=(
                "Los datos enviados no son válidos. "
                "Código posible: SUPPLIER_ALREADY_EXISTS."
            ),
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para crear proveedores."),
        ),
    },
    examples=[
        OpenApiExample(
            "Crear proveedor",
            request_only=True,
            value={
                "document_type": "NIT",
                "document_number": "900123456-7",
                "first_name": "Carlos",
                "last_name": "Gómez",
                "business_name": "Distribuciones Gómez S.A.S.",
                "email": "contacto@distribucionesgomez.com",
                "phone": "6011234567",
                "mobile": "3001234567",
                "address": "Carrera 10 #20-30",
                "city": "Bogotá",
                "country": "Colombia",
                "notes": "Proveedor principal.",
                "is_active": True,
            },
        ),
    ],
)


supplier_update_schema = extend_schema(
    tags=["Suppliers"],
    summary="Actualizar proveedor",
    description=("Actualiza completamente la información de un proveedor existente."),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description=("Identificador único del proveedor a actualizar."),
            required=True,
        ),
    ],
    request=SupplierUpdateSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="SupplierUpdateApiResponse",
                data_serializer=SupplierDetailSerializer,
            ),
            description="Proveedor actualizado correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description=(
                "Los datos enviados no son válidos. "
                "Código posible: SUPPLIER_ALREADY_EXISTS."
            ),
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para actualizar proveedores."),
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Proveedor no encontrado.",
        ),
    },
)


supplier_partial_update_schema = extend_schema(
    tags=["Suppliers"],
    summary="Actualizar parcialmente proveedor",
    description=("Actualiza parcialmente la información de un proveedor existente."),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description=(
                "Identificador único del proveedor a actualizar parcialmente."
            ),
            required=True,
        ),
    ],
    request=SupplierUpdateSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="SupplierPartialUpdateApiResponse",
                data_serializer=SupplierDetailSerializer,
            ),
            description=("Proveedor actualizado correctamente."),
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description=(
                "Los datos enviados no son válidos. "
                "Código posible: SUPPLIER_ALREADY_EXISTS."
            ),
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para actualizar proveedores."),
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Proveedor no encontrado.",
        ),
    },
)


supplier_delete_schema = extend_schema(
    tags=["Suppliers"],
    summary="Desactivar proveedor",
    description=(
        "Desactiva lógicamente un proveedor. "
        "El registro no se elimina físicamente "
        "de la base de datos."
    ),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description=("Identificador único del proveedor a desactivar."),
            required=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="SupplierDeleteApiResponse",
            ),
            description="Proveedor desactivado correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description=(
                "No fue posible desactivar el proveedor. "
                "Código posible: SUPPLIER_INACTIVE."
            ),
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para eliminar proveedores."),
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Proveedor no encontrado.",
        ),
    },
)


supplier_restore_schema = extend_schema(
    tags=["Suppliers"],
    summary="Restaurar proveedor",
    description=("Reactiva un proveedor previamente desactivado."),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description=("Identificador único del proveedor a restaurar."),
            required=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="SupplierRestoreApiResponse",
                data_serializer=SupplierDetailSerializer,
            ),
            description="Proveedor restaurado correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description=("No fue posible restaurar el proveedor."),
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para restaurar proveedores."),
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Proveedor no encontrado.",
        ),
    },
)
