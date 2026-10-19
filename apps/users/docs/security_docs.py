from drf_spectacular.utils import OpenApiResponse, extend_schema

from apps.core.docs.api_response_schema import build_api_response_schema
from apps.core.docs.error_schemas import ApiErrorResponseSerializer
from apps.users.serializers.auth.dashboard_serializer import DashboardResponseSerializer
from apps.users.serializers.auth.navigation_serializer import (
    NavigationResponseSerializer,
)
from apps.users.serializers.auth.permission_catalog_serializer import (
    PermissionCatalogResponseSerializer,
)
from apps.users.serializers.auth.security_context_serializer import (
    SecurityContextResponseSerializer,
)

security_context_schema = extend_schema(
    tags=["Security Dashboard"],
    summary="Obtener contexto de autorización",
    description=(
        "Retorna roles, permisos efectivos y acciones del usuario autenticado."
    ),
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="SecurityContextApiResponse",
                data_serializer=SecurityContextResponseSerializer,
            ),
            description="Contexto de autorización obtenido correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido o expirado.",
        ),
    },
)

navigation_schema = extend_schema(
    tags=["Security Dashboard"],
    summary="Obtener navegación dinámica",
    description=(
        "Retorna el árbol de navegación filtrado según los permisos "
        "efectivos del usuario autenticado."
    ),
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="SecurityNavigationApiResponse",
                data_serializer=NavigationResponseSerializer,
            ),
            description="Navegación obtenida correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido o expirado.",
        ),
    },
)

dashboard_schema = extend_schema(
    tags=["Security Dashboard"],
    summary="Obtener dashboard dinámico",
    description=(
        "Retorna los widgets del dashboard según los permisos "
        "efectivos del usuario autenticado."
    ),
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="SecurityDashboardApiResponse",
                data_serializer=DashboardResponseSerializer,
            ),
            description="Dashboard obtenido correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido o expirado.",
        ),
    },
)


permission_catalog_schema = extend_schema(
    tags=["Security Dashboard"],
    summary="Obtener catálogo de permisos",
    description=(
        "Retorna todos los permisos y acciones disponibles en el "
        "sistema, registrados dinámicamente mediante "
        "SecurityRegistry."
    ),
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="SecurityPermissionCatalogApiResponse",
                data_serializer=PermissionCatalogResponseSerializer,
            ),
            description="Catálogo de permisos obtenido correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido o expirado.",
        ),
    },
)
