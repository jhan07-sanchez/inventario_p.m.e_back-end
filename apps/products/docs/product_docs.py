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
from apps.products.serializers.product_serializer import (
    ProductCreateSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    ProductUpdateSerializer,
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
        description="Cantidad de productos por página.",
        required=False,
    ),
]


product_list_schema = extend_schema(
    tags=["Products"],
    summary="Listar productos",
    description=(
        "Obtiene el listado paginado de todos los productos registrados en el sistema."
    ),
    parameters=pagination_parameters,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="ProductListResponse",
                data_serializer=ProductListSerializer,
                is_list=True,
            ),
            description="Listado de productos obtenido correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para consultar productos."),
        ),
    },
)


product_detail_schema = extend_schema(
    tags=["Products"],
    summary="Obtener producto",
    description=("Obtiene toda la información detallada de un producto específico."),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único del producto.",
            required=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="ProductDetailResponse",
                data_serializer=ProductDetailSerializer,
            ),
            description="Producto obtenido correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para consultar productos."),
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Producto no encontrado.",
        ),
    },
)


product_create_schema = extend_schema(
    tags=["Products"],
    summary="Crear producto",
    description=(
        "Crea un nuevo producto dentro del sistema. "
        "El código y el código de barras deben ser únicos. "
        "La categoría debe existir y encontrarse activa."
    ),
    request=ProductCreateSerializer,
    responses={
        201: OpenApiResponse(
            response=build_api_response_schema(
                name="ProductCreateResponse",
                data_serializer=ProductDetailSerializer,
            ),
            description="Producto creado correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description=(
                "Datos inválidos. "
                "Códigos posibles: PRODUCT_ALREADY_EXISTS, "
                "CATEGORY_INACTIVE."
            ),
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para crear productos."),
        ),
    },
    examples=[
        OpenApiExample(
            "Crear Producto",
            request_only=True,
            value={
                "code": "FER-001",
                "barcode": "7701234567890",
                "name": "Martillo de acero",
                "description": ("Martillo de acero con mango reforzado."),
                "category": 1,
                "purchase_price": "25000.00",
                "sale_price": "35000.00",
                "unit": "UNIT",
                "is_active": True,
            },
        ),
    ],
)


product_update_schema = extend_schema(
    tags=["Products"],
    summary="Actualizar producto",
    description=(
        "Actualiza completamente la información de un producto "
        "existente. El stock no se modifica mediante esta operación; "
        "debe ser gestionado mediante el módulo de inventario."
    ),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description=("Identificador único del producto a actualizar."),
            required=True,
        ),
    ],
    request=ProductUpdateSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="ProductUpdateResponse",
                data_serializer=ProductDetailSerializer,
            ),
            description="Producto actualizado correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description=(
                "Datos inválidos. "
                "Códigos posibles: PRODUCT_ALREADY_EXISTS, "
                "CATEGORY_INACTIVE."
            ),
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para actualizar productos."),
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Producto no encontrado.",
        ),
    },
)


product_partial_update_schema = extend_schema(
    tags=["Products"],
    summary="Actualizar parcialmente un producto",
    description=(
        "Actualiza uno o varios campos de un producto existente. "
        "El stock no se modifica mediante esta operación."
    ),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description=("Identificador único del producto a actualizar parcialmente."),
            required=True,
        ),
    ],
    request=ProductUpdateSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="ProductPartialUpdateResponse",
                data_serializer=ProductDetailSerializer,
            ),
            description="Producto actualizado correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description=(
                "Datos inválidos. "
                "Códigos posibles: PRODUCT_ALREADY_EXISTS, "
                "CATEGORY_INACTIVE."
            ),
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para actualizar productos."),
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Producto no encontrado.",
        ),
    },
)


product_delete_schema = extend_schema(
    tags=["Products"],
    summary="Desactivar producto",
    description=(
        "Realiza el borrado lógico del producto. "
        "El registro no se elimina físicamente de la base de datos."
    ),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description=("Identificador único del producto a desactivar."),
            required=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="ProductDeleteResponse",
            ),
            description="Producto desactivado correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description=(
                "No fue posible desactivar el producto. "
                "Código posible: PRODUCT_INACTIVE."
            ),
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para eliminar productos."),
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Producto no encontrado.",
        ),
    },
)


product_restore_schema = extend_schema(
    tags=["Products"],
    summary="Restaurar producto",
    description=(
        "Reactiva un producto previamente desactivado mediante borrado lógico."
    ),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description=("Identificador único del producto a restaurar."),
            required=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="ProductRestoreResponse",
                data_serializer=ProductDetailSerializer,
            ),
            description="Producto restaurado correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description=("No fue posible restaurar el producto."),
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para restaurar productos."),
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Producto no encontrado.",
        ),
    },
)
