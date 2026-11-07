from drf_spectacular.utils import OpenApiResponse, extend_schema

from apps.configuration.serializers import (
    SoftwareVersionDetailSerializer,
    SoftwareVersionListSerializer,
    VersionChangelogEntrySerializer,
)
from apps.core.docs.api_response_schema import build_api_response_schema
from apps.core.docs.error_schemas import ApiErrorResponseSerializer

software_version_list_schema = extend_schema(
    tags=["Software Versions"],
    summary="Listar Versiones de Software",
    description="Retorna el listado de versiones de software registradas con paginación y filtros.",
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="SoftwareVersionListResponse",
                data_serializer=SoftwareVersionListSerializer,
                is_list=True,
            ),
            description="Listado de versiones obtenido correctamente.",
        ),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
        403: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

software_version_detail_schema = extend_schema(
    tags=["Software Versions"],
    summary="Detalle de Versión de Software",
    description="Obtiene el detalle completo de una versión de software con su changelog y requisitos.",
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="SoftwareVersionDetailResponse",
                data_serializer=SoftwareVersionDetailSerializer,
            ),
            description="Detalle de la versión obtenido correctamente.",
        ),
        404: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

software_version_create_schema = extend_schema(
    tags=["Software Versions"],
    summary="Crear Borrador de Versión",
    description="Registra una nueva versión de software en estado borrador (DRAFT).",
    responses={
        201: OpenApiResponse(
            response=build_api_response_schema(
                name="SoftwareVersionCreateResponse",
                data_serializer=SoftwareVersionDetailSerializer,
            ),
            description="Versión creada correctamente en estado borrador.",
        ),
        400: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

software_version_update_schema = extend_schema(
    tags=["Software Versions"],
    summary="Actualizar Borrador de Versión",
    description="Actualiza los campos de una versión de software en estado borrador.",
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="SoftwareVersionUpdateResponse",
                data_serializer=SoftwareVersionDetailSerializer,
            ),
            description="Versión actualizada correctamente.",
        ),
        400: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

software_version_publish_schema = extend_schema(
    tags=["Software Versions"],
    summary="Publicar Versión de Software",
    description="Publica una versión haciéndola disponible para notificaciones y despliegue.",
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="SoftwareVersionPublishResponse",
                data_serializer=SoftwareVersionDetailSerializer,
            ),
            description="Versión publicada exitosamente.",
        ),
        400: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

software_version_withdraw_schema = extend_schema(
    tags=["Software Versions"],
    summary="Retirar Versión de Software",
    description="Retira una versión publicada para que no aparezca en sugerencias de actualización.",
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="SoftwareVersionWithdrawResponse",
                data_serializer=SoftwareVersionDetailSerializer,
            ),
            description="Versión retirada exitosamente.",
        ),
        400: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

software_version_changelog_add_schema = extend_schema(
    tags=["Software Versions"],
    summary="Agregar Entrada de Changelog",
    description="Agrega un cambio categorizado a una versión.",
    responses={
        201: OpenApiResponse(
            response=build_api_response_schema(
                name="ChangelogEntryAddResponse",
                data_serializer=VersionChangelogEntrySerializer,
            ),
            description="Entrada de changelog creada correctamente.",
        ),
        400: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

software_version_check_updates_schema = extend_schema(
    tags=["Software Versions"],
    summary="Verificar Actualizaciones Disponibles",
    description="Compara la versión instalada con la última versión publicada.",
    responses={
        200: OpenApiResponse(
            description="Estado de actualizaciones del sistema.",
        ),
    },
)

software_version_history_schema = extend_schema(
    tags=["Software Versions"],
    summary="Historial de Versiones Publicadas",
    description="Retorna el historial de todas las versiones que han sido publicadas.",
)

software_version_latest_schema = extend_schema(
    tags=["Software Versions"],
    summary="Obtener Última Versión Publicada",
    description="Retorna los detalles de la última versión publicada disponible.",
)

software_version_destroy_schema = extend_schema(
    tags=["Software Versions"],
    summary="Eliminar Borrador de Versión",
    description="Elimina una versión que se encuentre en estado borrador.",
)

software_version_partial_update_schema = extend_schema(
    tags=["Software Versions"],
    summary="Actualizar Parcialmente Borrador",
    description="Actualiza campos específicos de una versión en borrador.",
)

software_version_delete_changelog_schema = extend_schema(
    tags=["Software Versions"],
    summary="Eliminar Entrada de Changelog",
    description="Elimina una entrada específica del changelog de una versión.",
)
