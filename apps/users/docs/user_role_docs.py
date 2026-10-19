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
from apps.users.serializers.user_role_serializer import (
    UserRoleCreateSerializer,
    UserRoleDetailSerializer,
    UserRoleListSerializer,
    UserRoleUpdateSerializer,
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

user_role_list_schema = extend_schema(
    tags=["User Roles"],
    summary="Listar asignaciones de roles",
    description="Obtiene el listado paginado de todas las asignaciones de roles a usuarios.",
    parameters=pagination_parameters,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="UserRoleListResponse",
                data_serializer=UserRoleListSerializer,
                is_list=True,
            ),
            description="Listado de asignaciones de roles obtenido correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para consultar asignaciones.",
        ),
    },
)

user_role_detail_schema = extend_schema(
    tags=["User Roles"],
    summary="Obtener asignación de rol",
    description="Obtiene la información detallada de una asignación de rol.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la asignación.",
            required=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="UserRoleDetailResponse",
                data_serializer=UserRoleDetailSerializer,
            ),
            description="Información de la asignación obtenida correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para consultar asignaciones.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer, description="Asignación no encontrada."
        ),
    },
)

user_role_create_schema = extend_schema(
    tags=["User Roles"],
    summary="Asignar rol a usuario",
    description="Crea una nueva asignación de rol a un usuario.",
    request=UserRoleCreateSerializer,
    responses={
        201: OpenApiResponse(
            response=build_api_response_schema(
                name="UserRoleCreateResponse",
                data_serializer=UserRoleDetailSerializer,
            ),
            description="Asignación creada correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="Datos inválidos. Códigos posibles: USER_ROLE_ALREADY_EXISTS, ROLE_INACTIVE, USER_INACTIVE.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para crear asignaciones.",
        ),
    },
    examples=[
        OpenApiExample(
            name="Asignar Rol",
            request_only=True,
            value={"user": 1, "role": 2},
        )
    ],
)

user_role_update_schema = extend_schema(
    tags=["User Roles"],
    summary="Actualizar asignación",
    description="Actualiza completamente una asignación de rol.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la asignación a actualizar.",
            required=True,
        )
    ],
    request=UserRoleUpdateSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="UserRoleUpdateResponse",
                data_serializer=UserRoleDetailSerializer,
            ),
            description="Asignación actualizada correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="Datos inválidos. Códigos posibles: USER_ROLE_ALREADY_EXISTS, ROLE_INACTIVE, USER_INACTIVE.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para actualizar asignaciones.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer, description="Asignación no encontrada."
        ),
    },
)

user_role_partial_update_schema = extend_schema(
    tags=["User Roles"],
    summary="Actualizar parcialmente una asignación",
    description="Actualiza uno o varios campos de una asignación.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la asignación a actualizar parcialmente.",
            required=True,
        )
    ],
    request=UserRoleUpdateSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="UserRolePartialUpdateResponse",
                data_serializer=UserRoleDetailSerializer,
            ),
            description="Asignación actualizada correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="Datos inválidos. Códigos posibles: USER_ROLE_ALREADY_EXISTS, ROLE_INACTIVE, USER_INACTIVE.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para actualizar asignaciones.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer, description="Asignación no encontrada."
        ),
    },
)

user_role_delete_schema = extend_schema(
    tags=["User Roles"],
    summary="Desactivar asignación",
    description="Realiza el borrado lógico de la asignación.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la asignación a desactivar.",
            required=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="UserRoleDeleteResponse",
            ),
            description="Asignación desactivada correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="No fue posible desactivar la asignación.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para eliminar asignaciones.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer, description="Asignación no encontrada."
        ),
    },
)

user_role_restore_schema = extend_schema(
    tags=["User Roles"],
    summary="Restaurar asignación",
    description="Reactiva una asignación previamente desactivada.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la asignación a restaurar.",
            required=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="UserRoleRestoreResponse",
                data_serializer=UserRoleDetailSerializer,
            ),
            description="Asignación restaurada correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="No fue posible restaurar la asignación.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para restaurar asignaciones.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer, description="Asignación no encontrada."
        ),
    },
)
