from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)

from apps.company_info.serializers.company_info_serializer import (
    CompanyInfoCreateSerializer,
    CompanyInfoSerializer,
    CompanyInfoUpdateSerializer,
)
from apps.core.docs.api_response_schema import build_api_response_schema
from apps.core.docs.error_schemas import (
    ApiErrorResponseSerializer,
    ValidationErrorResponseSerializer,
)

company_info_list_schema = extend_schema(
    tags=["Company Info"],
    summary="Listar Información de Empresa",
    description=(
        "Obtiene la lista de registros de información de empresa. "
        "En condiciones normales solo existe un registro activo."
    ),
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="CompanyInfoListApiResponse",
                data_serializer=CompanyInfoSerializer,
                is_list=True,
            ),
            description="Información de empresa obtenida correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso.",
        ),
    },
)

company_info_detail_schema = extend_schema(
    tags=["Company Info"],
    summary="Obtener Información de Empresa",
    description="Obtiene los detalles completos de la empresa por su ID.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la empresa.",
            required=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="CompanyInfoDetailApiResponse",
                data_serializer=CompanyInfoSerializer,
            ),
            description="Información de empresa obtenida correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Empresa no encontrada.",
        ),
    },
)

company_info_current_schema = extend_schema(
    tags=["Company Info"],
    summary="Obtener Empresa Actual",
    description=(
        "Obtiene la información de la empresa activa actual (singleton). "
        "Este es el endpoint principal para obtener los datos del negocio "
        "en tickets POS, facturas y reportes."
    ),
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="CompanyInfoCurrentApiResponse",
                data_serializer=CompanyInfoSerializer,
            ),
            description="Información de empresa obtenida correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="No hay empresa configurada.",
        ),
    },
)

company_info_create_schema = extend_schema(
    tags=["Company Info"],
    summary="Crear Información de Empresa",
    description=(
        "Crea el registro de información de empresa. "
        "Solo se permite un registro activo en el sistema."
    ),
    request=CompanyInfoCreateSerializer,
    responses={
        201: OpenApiResponse(
            response=build_api_response_schema(
                name="CompanyInfoCreateApiResponse",
                data_serializer=CompanyInfoSerializer,
            ),
            description="Información de empresa creada correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="Los datos enviados no son válidos.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso.",
        ),
    },
    examples=[
        OpenApiExample(
            "Crear Empresa",
            request_only=True,
            value={
                "business_name": "Mi Empresa S.A.S",
                "trade_name": "Mi Tienda",
                "tax_id": "900123456-7",
                "phone": "6011234567",
                "mobile": "3001234567",
                "email": "contacto@miempresa.com",
                "address": "Calle 123 #45-67",
                "city": "Bogotá",
                "state": "Cundinamarca",
                "country": "Colombia",
                "description": "Distribuidora de productos.",
                "receipt_footer": "Gracias por su compra",
            },
        )
    ],
)

company_info_update_schema = extend_schema(
    tags=["Company Info"],
    summary="Actualizar Información de Empresa",
    description="Actualiza la información de la empresa.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador de la empresa.",
            required=True,
        )
    ],
    request=CompanyInfoUpdateSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="CompanyInfoUpdateApiResponse",
                data_serializer=CompanyInfoSerializer,
            ),
            description="Información de empresa actualizada correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="Los datos enviados no son válidos.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Empresa no encontrada.",
        ),
    },
)

company_info_partial_update_schema = extend_schema(
    tags=["Company Info"],
    summary="Actualizar Parcialmente Empresa",
    description="Actualiza de forma parcial la información de la empresa.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador de la empresa.",
            required=True,
        )
    ],
    request=CompanyInfoUpdateSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="CompanyInfoPartialUpdateApiResponse",
                data_serializer=CompanyInfoSerializer,
            ),
            description="Información de empresa actualizada correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="Datos no válidos.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
        ),
    },
)

company_info_delete_schema = extend_schema(
    tags=["Company Info"],
    summary="Desactivar Empresa",
    description="Realiza un borrado lógico de la información de empresa.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador de la empresa a desactivar.",
            required=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="CompanyInfoDeleteApiResponse",
            ),
            description="Empresa desactivada correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
        ),
    },
)

company_info_upload_logo_schema = extend_schema(
    tags=["Company Info"],
    summary="Subir Logo de Empresa",
    description="Sube o reemplaza el logo de la empresa.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador de la empresa.",
            required=True,
        )
    ],
    request={
        "multipart/form-data": {
            "type": "object",
            "properties": {
                "logo": {
                    "type": "string",
                    "format": "binary",
                    "description": "Archivo de imagen del logo.",
                }
            },
            "required": ["logo"],
        }
    },
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="CompanyInfoUploadLogoApiResponse",
                data_serializer=CompanyInfoSerializer,
            ),
            description="Logo actualizado correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
        ),
    },
)
