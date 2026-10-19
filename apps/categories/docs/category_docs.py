from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)

from apps.categories.serializers.category_serializer import (
    CategoryCreateSerializer,
    CategoryDetailSerializer,
    CategoryListSerializer,
    CategoryUpdateSerializer,
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


category_list_schema = extend_schema(
    tags=["Categories"],
    summary="Listar categorías",
    description=(
        "Obtiene el listado paginado de las categorías registradas en el sistema."
    ),
    parameters=pagination_parameters,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="CategoryListApiResponse",
                data_serializer=CategoryListSerializer,
                is_list=True,
            ),
            description="Categorías obtenidas correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para consultar categorías."),
        ),
    },
)


category_detail_schema = extend_schema(
    tags=["Categories"],
    summary="Obtener categoría",
    description=(
        "Obtiene la información detallada de una categoría mediante su identificador."
    ),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la categoría.",
            required=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="CategoryDetailApiResponse",
                data_serializer=CategoryDetailSerializer,
            ),
            description="Categoría obtenida correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para consultar categorías."),
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Categoría no encontrada.",
        ),
    },
)


category_create_schema = extend_schema(
    tags=["Categories"],
    summary="Crear categoría",
    description=(
        "Registra una nueva categoría en el sistema. "
        "El nombre de la categoría debe cumplir las reglas "
        "de validación definidas por el sistema."
    ),
    request=CategoryCreateSerializer,
    responses={
        201: OpenApiResponse(
            response=build_api_response_schema(
                name="CategoryCreateApiResponse",
                data_serializer=CategoryDetailSerializer,
            ),
            description="Categoría creada correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description=("Los datos enviados no son válidos."),
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para crear categorías."),
        ),
    },
    examples=[
        OpenApiExample(
            "Crear categoría",
            request_only=True,
            value={
                "name": "Herramientas",
                "description": ("Categoría para herramientas manuales y eléctricas."),
                "is_active": True,
            },
        ),
    ],
)


category_update_schema = extend_schema(
    tags=["Categories"],
    summary="Actualizar categoría",
    description=("Actualiza completamente la información de una categoría existente."),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description=("Identificador único de la categoría a actualizar."),
            required=True,
        ),
    ],
    request=CategoryUpdateSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="CategoryUpdateApiResponse",
                data_serializer=CategoryDetailSerializer,
            ),
            description="Categoría actualizada correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description=("Los datos enviados no son válidos."),
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para actualizar categorías."),
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Categoría no encontrada.",
        ),
    },
)


category_partial_update_schema = extend_schema(
    tags=["Categories"],
    summary="Actualizar parcialmente categoría",
    description=("Actualiza parcialmente la información de una categoría existente."),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description=(
                "Identificador único de la categoría a actualizar parcialmente."
            ),
            required=True,
        ),
    ],
    request=CategoryUpdateSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="CategoryPartialUpdateApiResponse",
                data_serializer=CategoryDetailSerializer,
            ),
            description=("Categoría actualizada parcialmente."),
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description=("Los datos enviados no son válidos."),
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para actualizar categorías."),
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Categoría no encontrada.",
        ),
    },
)


category_delete_schema = extend_schema(
    tags=["Categories"],
    summary="Desactivar categoría",
    description=(
        "Desactiva lógicamente una categoría. "
        "El registro no se elimina físicamente "
        "de la base de datos."
    ),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description=("Identificador único de la categoría a desactivar."),
            required=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="CategoryDeleteApiResponse",
            ),
            description=("Categoría desactivada correctamente."),
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description=("No fue posible desactivar la categoría."),
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para eliminar categorías."),
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Categoría no encontrada.",
        ),
    },
)


category_restore_schema = extend_schema(
    tags=["Categories"],
    summary="Restaurar categoría",
    description=("Reactiva una categoría previamente desactivada."),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description=("Identificador único de la categoría a restaurar."),
            required=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="CategoryRestoreApiResponse",
                data_serializer=CategoryDetailSerializer,
            ),
            description="Categoría restaurada correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description=("No fue posible restaurar la categoría."),
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("Token inválido, expirado o usuario no autenticado."),
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description=("El usuario no tiene permiso para restaurar categorías."),
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Categoría no encontrada.",
        ),
    },
)
