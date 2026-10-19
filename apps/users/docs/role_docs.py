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
from apps.users.serializers.role_serializer import (
    RoleCreateSerializer,
    RoleDetailSerializer,
    RoleListSerializer,
    RoleUpdateSerializer,
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

role_list_schema = extend_schema(
    tags=["Roles"],
    summary="Listar roles",
    description="Obtiene el listado paginado de todos los roles registrados en el sistema.",
    parameters=pagination_parameters,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="RoleListResponse",
                data_serializer=RoleListSerializer,
                is_list=True,
            ),
            description="Listado de roles obtenido correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para consultar roles.",
        ),
    },
)

role_detail_schema = extend_schema(
    tags=["Roles"],
    summary="Obtener rol",
    description="Obtiene la información detallada de un rol específico.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único del rol.",
            required=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="RoleDetailResponse",
                data_serializer=RoleDetailSerializer,
            ),
            description="Información del rol obtenida correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para consultar roles.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer, description="Rol no encontrado."
        ),
    },
)

role_create_schema = extend_schema(
    tags=["Roles"],
    summary="Crear rol",
    description=(
        "Crea un nuevo rol dentro del sistema. "
        "El campo 'permissions' recibe un JSON con los permisos activos del rol basado en el SecurityRegistry."
    ),
    request=RoleCreateSerializer,
    responses={
        201: OpenApiResponse(
            response=build_api_response_schema(
                name="RoleCreateResponse",
                data_serializer=RoleDetailSerializer,
            ),
            description="Rol creado correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="Datos inválidos. Códigos posibles: ROLE_ALREADY_EXISTS, INVALID_ROLE_PERMISSIONS.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para crear roles.",
        ),
    },
    examples=[
        OpenApiExample(
            name="Crear Rol",
            request_only=True,
            value={
                "role_name": "Administrador",
                "role_description": "Control total del sistema",
                "is_active": True,
                "permissions": {
                    "users.view": True,
                    "users.create": True,
                    "customers.view": True,
                },
            },
        )
    ],
)

role_update_schema = extend_schema(
    tags=["Roles"],
    summary="Actualizar rol",
    description="Actualiza completamente un rol.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único del rol a actualizar.",
            required=True,
        )
    ],
    request=RoleUpdateSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="RoleUpdateResponse",
                data_serializer=RoleDetailSerializer,
            ),
            description="Rol actualizado correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="Datos inválidos. Códigos posibles: ROLE_ALREADY_EXISTS, INVALID_ROLE_PERMISSIONS.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para actualizar roles.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer, description="Rol no encontrado."
        ),
    },
)

role_partial_update_schema = extend_schema(
    tags=["Roles"],
    summary="Actualizar parcialmente un rol",
    description="Actualiza uno o varios campos de un rol.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único del rol a actualizar parcialmente.",
            required=True,
        )
    ],
    request=RoleUpdateSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="RolePartialUpdateResponse",
                data_serializer=RoleDetailSerializer,
            ),
            description="Rol actualizado correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="Datos inválidos. Códigos posibles: ROLE_ALREADY_EXISTS, INVALID_ROLE_PERMISSIONS.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para actualizar roles.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer, description="Rol no encontrado."
        ),
    },
)

role_delete_schema = extend_schema(
    tags=["Roles"],
    summary="Desactivar rol",
    description="Realiza el borrado lógico del rol.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único del rol a desactivar.",
            required=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="RoleDeleteResponse",
            ),
            description="Rol desactivado correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="No fue posible desactivar el rol. Códigos posibles: ROLE_INACTIVE.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para eliminar roles.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer, description="Rol no encontrado."
        ),
    },
)

role_restore_schema = extend_schema(
    tags=["Roles"],
    summary="Restaurar rol",
    description="Reactiva un rol previamente desactivado.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único del rol a restaurar.",
            required=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="RoleRestoreResponse",
                data_serializer=RoleDetailSerializer,
            ),
            description="Rol restaurado correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="No fue posible restaurar el rol.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para restaurar roles.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer, description="Rol no encontrado."
        ),
    },
)
