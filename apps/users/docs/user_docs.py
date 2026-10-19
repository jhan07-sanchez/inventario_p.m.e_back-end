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
from apps.users.serializers.user_serializer import (
    UserCreateSerializer,
    UserDetailSerializer,
    UserListSerializer,
    UserUpdateSerializer,
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

user_list_schema = extend_schema(
    tags=["Users"],
    summary="Listar usuarios",
    description="Obtiene el listado paginado de todos los usuarios registrados en el sistema.",
    parameters=pagination_parameters,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="UserListResponse",
                data_serializer=UserListSerializer,
                is_list=True,
            ),
            description="Listado de usuarios obtenido correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para consultar usuarios.",
        ),
    },
)

user_detail_schema = extend_schema(
    tags=["Users"],
    summary="Obtener usuario",
    description="Obtiene toda la información detallada de un usuario específico.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único del usuario.",
            required=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="UserDetailResponse",
                data_serializer=UserDetailSerializer,
            ),
            description="Información del usuario obtenida correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para consultar usuarios.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer, description="Usuario no encontrado."
        ),
    },
)

user_create_schema = extend_schema(
    tags=["Users"],
    summary="Crear usuario",
    description=(
        "Crea un nuevo usuario dentro del sistema. "
        "El nombre de usuario, correo electrónico y número de documento deben ser únicos."
    ),
    request=UserCreateSerializer,
    responses={
        201: OpenApiResponse(
            response=build_api_response_schema(
                name="UserCreateResponse",
                data_serializer=UserDetailSerializer,
            ),
            description="Usuario creado correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="Datos inválidos. Códigos posibles: USER_ALREADY_EXISTS, EMAIL_ALREADY_EXISTS, DOCUMENT_ALREADY_EXISTS.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para crear usuarios.",
        ),
    },
    examples=[
        OpenApiExample(
            "Crear Usuario",
            request_only=True,
            value={
                "username": "juanperez",
                "password": "Admin123*",
                "first_name": "Juan",
                "last_name": "Pérez",
                "email": "juan@gmail.com",
                "document_number": "123456789",
                "phone_number": "3001234567",
            },
        )
    ],
)

user_update_schema = extend_schema(
    tags=["Users"],
    summary="Actualizar usuario",
    description="Actualiza completamente un usuario existente.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único del usuario a actualizar.",
            required=True,
        )
    ],
    request=UserUpdateSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="UserUpdateResponse",
                data_serializer=UserDetailSerializer,
            ),
            description="Usuario actualizado correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="Datos inválidos. Códigos posibles: USER_ALREADY_EXISTS, EMAIL_ALREADY_EXISTS, DOCUMENT_ALREADY_EXISTS.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para actualizar usuarios.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer, description="Usuario no encontrado."
        ),
    },
)

user_partial_update_schema = extend_schema(
    tags=["Users"],
    summary="Actualizar parcialmente un usuario",
    description="Actualiza uno o varios campos de un usuario existente.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único del usuario a actualizar parcialmente.",
            required=True,
        )
    ],
    request=UserUpdateSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="UserPartialUpdateResponse",
                data_serializer=UserDetailSerializer,
            ),
            description="Usuario actualizado correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="Datos inválidos. Códigos posibles: USER_ALREADY_EXISTS, EMAIL_ALREADY_EXISTS, DOCUMENT_ALREADY_EXISTS.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para actualizar usuarios.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer, description="Usuario no encontrado."
        ),
    },
)

user_delete_schema = extend_schema(
    tags=["Users"],
    summary="Desactivar usuario",
    description=(
        "Realiza el borrado lógico del usuario. No elimina físicamente el registro."
    ),
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único del usuario a desactivar.",
            required=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="UserDeleteResponse",
            ),
            description="Usuario desactivado correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="No fue posible desactivar el usuario. Códigos posibles: USER_INACTIVE.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para eliminar usuarios.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer, description="Usuario no encontrado."
        ),
    },
)

user_restore_schema = extend_schema(
    tags=["Users"],
    summary="Restaurar usuario",
    description="Reactiva un usuario previamente desactivado.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único del usuario a restaurar.",
            required=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="UserRestoreResponse",
                data_serializer=UserDetailSerializer,
            ),
            description="Usuario restaurado correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="No fue posible restaurar el usuario.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para restaurar usuarios.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer, description="Usuario no encontrado."
        ),
    },
)
