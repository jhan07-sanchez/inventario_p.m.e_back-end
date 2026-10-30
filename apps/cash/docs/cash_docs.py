from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)

from apps.cash.serializers.cash_movement_serializer import (
    CashMovementCreateSerializer,
    CashMovementRetrieveSerializer,
)
from apps.cash.serializers.cash_register_serializer import CashRegisterSerializer
from apps.cash.serializers.cash_session_serializer import (
    CashSessionCloseSerializer,
    CashSessionOpenSerializer,
    CashSessionRetrieveSerializer,
)
from apps.core.docs.api_response_schema import build_api_response_schema
from apps.core.docs.error_schemas import (
    ApiErrorResponseSerializer,
    ValidationErrorResponseSerializer,
)

# -------------------------------------------------------------------------
# Parámetros Comunes
# -------------------------------------------------------------------------

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
        description="Cantidad de registros por página.",
        required=False,
    ),
]

search_parameters = [
    OpenApiParameter(
        name="search",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description="Búsqueda por nombre o descripción de la caja.",
        required=False,
    ),
]

# =========================================================================
# Cash Registers (Cajas Registradoras)
# =========================================================================

cash_register_list_schema = extend_schema(
    tags=["Cash"],
    summary="Listar cajas registradoras",
    description="Obtiene el listado de todas las cajas registradoras del sistema con soporte de filtrado y ordenamiento.",
    parameters=search_parameters,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="CashRegisterListResponse",
                data_serializer=CashRegisterSerializer,
                is_list=True,
            ),
            description="Listado de cajas registradoras obtenido correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para consultar cajas registradoras.",
        ),
    },
)

cash_register_detail_schema = extend_schema(
    tags=["Cash"],
    summary="Obtener caja registradora",
    description="Obtiene la información detallada de una caja registradora específica por su identificador.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la caja registradora.",
            required=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="CashRegisterDetailResponse",
                data_serializer=CashRegisterSerializer,
            ),
            description="Caja registradora obtenida correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para consultar cajas registradoras.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Caja registradora no encontrada.",
        ),
    },
)


cash_register_create_schema = extend_schema(
    tags=["Cash"],
    summary="Registrar caja registradora",
    description="Crea y registra una nueva caja registradora en el sistema.",
    request=CashRegisterSerializer,
    responses={
        201: OpenApiResponse(
            response=build_api_response_schema(
                name="CashRegisterCreateResponse",
                data_serializer=CashRegisterSerializer,
            ),
            description="Caja registradora registrada correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="Datos inválidos enviados en el formulario.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para crear cajas registradoras.",
        ),
    },
    examples=[
        OpenApiExample(
            "Crear Caja",
            request_only=True,
            value={
                "name": "Caja Principal 01",
                "description": "Caja de cobro para el mostrador principal",
                "is_active": True,
            },
        ),
    ],
)

# =========================================================================
# Cash Sessions (Sesiones de Caja)
# =========================================================================

cash_session_list_schema = extend_schema(
    tags=["Cash"],
    summary="Listar sesiones de caja",
    description="Obtiene el listado paginado del historial de aperturas y cierres de sesión de caja.",
    parameters=pagination_parameters,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="CashSessionListResponse",
                data_serializer=CashSessionRetrieveSerializer,
                is_list=True,
            ),
            description="Listado de sesiones de caja obtenido correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para consultar sesiones de caja.",
        ),
    },
)

cash_session_detail_schema = extend_schema(
    tags=["Cash"],
    summary="Obtener sesión de caja",
    description="Obtiene el detalle completo de una sesión de caja específica por su identificador.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la sesión de caja.",
            required=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="CashSessionDetailResponse",
                data_serializer=CashSessionRetrieveSerializer,
            ),
            description="Sesión de caja obtenida correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para consultar sesiones de caja.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Sesión de caja no encontrada.",
        ),
    },
)

cash_session_current_schema = extend_schema(
    tags=["Cash"],
    summary="Obtener sesión de caja actual del usuario",
    description="Retorna la sesión de caja que se encuentra actualmente abierta para el usuario autenticado.",
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="CashSessionCurrentResponse",
                data_serializer=CashSessionRetrieveSerializer,
            ),
            description="Sesión actual obtenida correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para consultar sesiones de caja.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene ninguna sesión de caja abierta.",
        ),
    },
)

cash_session_open_schema = extend_schema(
    tags=["Cash"],
    summary="Abrir sesión de caja",
    description="Abre un nuevo turno o sesión de caja asociando al usuario actual, registrando la base inicial en efectivo.",
    request=CashSessionOpenSerializer,
    responses={
        201: OpenApiResponse(
            response=build_api_response_schema(
                name="CashSessionOpenResponse",
                data_serializer=CashSessionRetrieveSerializer,
            ),
            description="Sesión de caja abierta correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="Error en la validación de los datos o la caja/usuario ya tiene una sesión abierta.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para abrir sesiones de caja.",
        ),
    },
    examples=[
        OpenApiExample(
            "Apertura de Caja",
            request_only=True,
            value={
                "cash_register_id": 1,
                "opening_balance": "50000.00",
                "notes": "Apertura turno de la mañana con base estándar.",
            },
        ),
    ],
)

cash_session_close_schema = extend_schema(
    tags=["Cash"],
    summary="Cerrar sesión de caja (Arqueo)",
    description="Cierra una sesión de caja abierta, registrando el conteo físico del efectivo y calculando discrepancias.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la sesión de caja a cerrar.",
            required=True,
        ),
    ],
    request=CashSessionCloseSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="CashSessionCloseResponse",
                data_serializer=CashSessionRetrieveSerializer,
            ),
            description="Sesión de caja cerrada correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="La sesión ya se encuentra cerrada o los datos no son válidos.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para cerrar sesiones de caja.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Sesión de caja no encontrada.",
        ),
    },
    examples=[
        OpenApiExample(
            "Cierre y Arqueo de Caja",
            request_only=True,
            value={
                "counted_balance": "285000.00",
                "notes": "Cierre de turno normal sin novedades.",
            },
        ),
    ],
)

cash_session_add_movement_schema = extend_schema(
    tags=["Cash"],
    summary="Registrar movimiento manual de caja",
    description="Registra un movimiento manual de entrada o salida de efectivo/valores en una sesión de caja activa.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la sesión de caja.",
            required=True,
        ),
    ],
    request=CashMovementCreateSerializer,
    responses={
        201: OpenApiResponse(
            response=build_api_response_schema(
                name="CashMovementCreateResponse",
                data_serializer=CashMovementRetrieveSerializer,
            ),
            description="Movimiento de caja registrado correctamente.",
        ),
        400: OpenApiResponse(
            response=ValidationErrorResponseSerializer,
            description="Error de validación o la sesión de caja está cerrada.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para registrar movimientos de caja.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Sesión de caja no encontrada.",
        ),
    },
    examples=[
        OpenApiExample(
            "Ingreso Manual de Efectivo",
            request_only=True,
            value={
                "amount": "20000.00",
                "movement_type": "IN",
                "is_cash": True,
                "reference": "SENCILLO-01",
                "description": "Ingreso de sencillo para cambio.",
            },
        ),
        OpenApiExample(
            "Retiro Manual de Efectivo",
            request_only=True,
            value={
                "amount": "15000.00",
                "movement_type": "OUT",
                "is_cash": True,
                "reference": "GASTO-MENOR-45",
                "description": "Pago de mensajería urgente.",
            },
        ),
    ],
)

cash_session_movements_schema = extend_schema(
    tags=["Cash"],
    summary="Listar movimientos de una sesión de caja",
    description="Retorna el historial completo de movimientos (ventas, entradas manuales, retiros) asociados a una sesión de caja.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador único de la sesión de caja.",
            required=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="CashSessionMovementsListResponse",
                data_serializer=CashMovementRetrieveSerializer,
                is_list=True,
            ),
            description="Movimientos de la sesión de caja obtenidos correctamente.",
        ),
        401: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Token inválido, expirado o usuario no autenticado.",
        ),
        403: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="El usuario no tiene permiso para consultar movimientos de caja.",
        ),
        404: OpenApiResponse(
            response=ApiErrorResponseSerializer,
            description="Sesión de caja no encontrada.",
        ),
    },
)

cash_session_financial_summary_schema = extend_schema(
    tags=["Cash"],
    summary="Resumen financiero global",
    description="Obtiene el resumen financiero global de las cajas.",
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(name="CashFinancialSummaryResponse"),
            description="Resumen financiero obtenido.",
        ),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

cash_session_last_closing_balance_schema = extend_schema(
    tags=["Cash"],
    summary="Obtener último saldo de cierre",
    description="Obtiene el último saldo de cierre registrado para una caja específica.",
    parameters=[
        OpenApiParameter(
            name="cash_register_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="ID de la caja registradora.",
            required=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(name="LastClosingBalanceResponse"),
            description="Último saldo obtenido.",
        ),
        400: OpenApiResponse(response=ValidationErrorResponseSerializer),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

cash_session_audit_summary_schema = extend_schema(
    tags=["Cash"],
    summary="Resumen de auditoría de sesión",
    description="Obtiene un resumen detallado de auditoría para una sesión de caja específica.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Identificador de la sesión.",
            required=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(name="CashAuditSummaryResponse"),
            description="Resumen de auditoría obtenido.",
        ),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)
