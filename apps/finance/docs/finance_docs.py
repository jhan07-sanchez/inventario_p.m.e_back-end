from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema

from apps.core.docs.api_response_schema import build_api_response_schema
from apps.core.docs.error_schemas import (
    ApiErrorResponseSerializer,
    ValidationErrorResponseSerializer,
)
from apps.finance.serializers.finance_dashboard_serializer import (
    FinanceDashboardResponseSerializer,
)
from apps.finance.serializers.financial_account_serializer import (
    FinancialAccountCreateSerializer,
    FinancialAccountDetailSerializer,
    FinancialAccountListSerializer,
    FinancialAccountUpdateSerializer,
)
from apps.finance.serializers.financial_category_serializer import (
    FinancialCategoryCreateUpdateSerializer,
    FinancialCategorySerializer,
)
from apps.finance.serializers.financial_movement_serializer import (
    FinancialMovementCreateSerializer,
    FinancialMovementListSerializer,
    FinancialMovementReverseSerializer,
)
from apps.finance.serializers.financial_reconciliation_serializer import (
    FinancialReconciliationCreateSerializer,
    FinancialReconciliationListSerializer,
)
from apps.finance.serializers.financial_transfer_serializer import (
    FinancialTransferCancelSerializer,
    FinancialTransferCreateSerializer,
    FinancialTransferListSerializer,
)

TAG_FINANCE = ["Finance"]

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

# -------------------------------------------------------------------------
# Dashboard Financiero
# -------------------------------------------------------------------------

finance_dashboard_schema = extend_schema(
    tags=TAG_FINANCE,
    summary="Dashboard y Métricas Financieras",
    description=(
        "Obtiene los indicadores consolidados de tesorería: dinero disponible en efectivo y bancos, "
        "flujo de ingresos y egresos del período (excluyendo transferencias propias), cuentas por cobrar, "
        "cuentas por pagar a proveedores y distribución por método de pago."
    ),
    parameters=[
        OpenApiParameter(
            name="start_date",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description="Fecha inicial del período (YYYY-MM-DD). Por defecto primer día del mes actual.",
            required=False,
        ),
        OpenApiParameter(
            name="end_date",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description="Fecha final del período (YYYY-MM-DD). Por defecto hoy.",
            required=False,
        ),
        OpenApiParameter(
            name="company_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Filtro opcional por empresa autorizada.",
            required=False,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="FinanceDashboardApiResponse",
                data_serializer=FinanceDashboardResponseSerializer,
            ),
            description="Métricas financieras obtenidas exitosamente.",
        ),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
        403: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

# -------------------------------------------------------------------------
# Cuentas Financieras
# -------------------------------------------------------------------------

finance_account_list_schema = extend_schema(
    tags=TAG_FINANCE,
    summary="Listar Cuentas Financieras",
    description="Obtiene el listado de cuentas financieras (cajas, bancos, billeteras digitales) con sus saldos.",
    parameters=pagination_parameters,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="FinancialAccountListApiResponse",
                data_serializer=FinancialAccountListSerializer,
                is_list=True,
            ),
            description="Cuentas financieras obtenidas correctamente.",
        ),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
        403: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

finance_account_detail_schema = extend_schema(
    tags=TAG_FINANCE,
    summary="Obtener Cuenta Financiera",
    description="Obtiene los datos detallados y el saldo actual de una cuenta financiera.",
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="FinancialAccountDetailApiResponse",
                data_serializer=FinancialAccountDetailSerializer,
            ),
            description="Cuenta financiera obtenida correctamente.",
        ),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
        404: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

finance_account_create_schema = extend_schema(
    tags=TAG_FINANCE,
    summary="Registrar Cuenta Financiera",
    description="Crea una nueva cuenta financiera con su saldo inicial y entidad bancaria.",
    request=FinancialAccountCreateSerializer,
    responses={
        201: OpenApiResponse(
            response=build_api_response_schema(
                name="FinancialAccountCreateApiResponse",
                data_serializer=FinancialAccountDetailSerializer,
            ),
            description="Cuenta financiera creada correctamente.",
        ),
        400: OpenApiResponse(response=ValidationErrorResponseSerializer),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

finance_account_update_schema = extend_schema(
    tags=TAG_FINANCE,
    summary="Actualizar Cuenta Financiera",
    description="Actualiza la información descriptiva o bancaria de una cuenta financiera.",
    request=FinancialAccountUpdateSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="FinancialAccountUpdateApiResponse",
                data_serializer=FinancialAccountDetailSerializer,
            ),
            description="Cuenta financiera actualizada.",
        ),
        400: OpenApiResponse(response=ValidationErrorResponseSerializer),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

finance_account_delete_schema = extend_schema(
    tags=TAG_FINANCE,
    summary="Desactivar Cuenta Financiera",
    description="Realiza el borrado lógico (soft delete) de una cuenta financiera.",
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(name="FinancialAccountDeleteApiResponse"),
            description="Cuenta financiera desactivada correctamente.",
        ),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
        404: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

finance_account_restore_schema = extend_schema(
    tags=TAG_FINANCE,
    summary="Restaurar Cuenta Financiera",
    description="Restaura una cuenta financiera previamente desactivada (soft delete).",
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="FinancialAccountRestoreApiResponse",
                data_serializer=FinancialAccountDetailSerializer,
            ),
            description="Cuenta financiera restaurada correctamente.",
        ),
        400: OpenApiResponse(response=ValidationErrorResponseSerializer),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
        404: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

# -------------------------------------------------------------------------
# Categorías Financieras
# -------------------------------------------------------------------------

finance_category_list_schema = extend_schema(
    tags=TAG_FINANCE,
    summary="Listar Categorías Financieras",
    description="Obtiene el catálogo de categorías para clasificación de ingresos y egresos.",
    parameters=pagination_parameters,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="FinancialCategoryListApiResponse",
                data_serializer=FinancialCategorySerializer,
                is_list=True,
            ),
            description="Categorías financieras obtenidas correctamente.",
        ),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

finance_category_create_schema = extend_schema(
    tags=TAG_FINANCE,
    summary="Crear Categoría Financiera",
    description="Crea una nueva categoría para ingresos o egresos de tesorería.",
    request=FinancialCategoryCreateUpdateSerializer,
    responses={
        201: OpenApiResponse(
            response=build_api_response_schema(
                name="FinancialCategoryCreateApiResponse",
                data_serializer=FinancialCategorySerializer,
            ),
            description="Categoría financiera creada.",
        ),
        400: OpenApiResponse(response=ValidationErrorResponseSerializer),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

finance_category_detail_schema = extend_schema(
    tags=TAG_FINANCE,
    summary="Obtener Categoría Financiera",
    description="Obtiene los datos de una categoría financiera por su identificador.",
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="FinancialCategoryDetailApiResponse",
                data_serializer=FinancialCategorySerializer,
            ),
            description="Categoría financiera obtenida.",
        ),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
        404: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

# -------------------------------------------------------------------------
# Movimientos Financieros
# -------------------------------------------------------------------------

finance_movement_list_schema = extend_schema(
    tags=TAG_FINANCE,
    summary="Listar Movimientos Financieros",
    description="Obtiene el historial paginado de ingresos y egresos monetarios.",
    parameters=pagination_parameters + [
        OpenApiParameter(
            name="account_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Filtrar por ID de cuenta financiera.",
            required=False,
        ),
        OpenApiParameter(
            name="movement_type",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Filtrar por INFLOW o OUTFLOW.",
            required=False,
        ),
        OpenApiParameter(
            name="start_date",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description="Fecha inicial (YYYY-MM-DD).",
            required=False,
        ),
        OpenApiParameter(
            name="end_date",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description="Fecha final (YYYY-MM-DD).",
            required=False,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="FinancialMovementListApiResponse",
                data_serializer=FinancialMovementListSerializer,
                is_list=True,
            ),
            description="Movimientos financieros obtenidos correctamente.",
        ),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

finance_movement_detail_schema = extend_schema(
    tags=TAG_FINANCE,
    summary="Obtener Movimiento Financiero",
    description="Obtiene los datos detallados de un movimiento financiero.",
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="FinancialMovementDetailApiResponse",
                data_serializer=FinancialMovementListSerializer,
            ),
            description="Detalle del movimiento financiero obtenido.",
        ),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
        404: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

finance_movement_create_schema = extend_schema(
    tags=TAG_FINANCE,
    summary="Registrar Movimiento Financiero",
    description="Registra un ingreso o egreso directo afectando de forma atómica el saldo de la cuenta financiera.",
    request=FinancialMovementCreateSerializer,
    responses={
        201: OpenApiResponse(
            response=build_api_response_schema(
                name="FinancialMovementCreateApiResponse",
                data_serializer=FinancialMovementListSerializer,
            ),
            description="Movimiento registrado con éxito.",
        ),
        400: OpenApiResponse(response=ValidationErrorResponseSerializer),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

finance_movement_reverse_schema = extend_schema(
    tags=TAG_FINANCE,
    summary="Reversar Movimiento Financiero",
    description="Reversa de forma auditable un movimiento financiero completado creando un contra-asiento.",
    request=FinancialMovementReverseSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="FinancialMovementReverseApiResponse",
                data_serializer=FinancialMovementListSerializer,
            ),
            description="Movimiento reversado exitosamente.",
        ),
        400: OpenApiResponse(response=ValidationErrorResponseSerializer),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

# -------------------------------------------------------------------------
# Transferencias Financieras
# -------------------------------------------------------------------------

finance_transfer_list_schema = extend_schema(
    tags=TAG_FINANCE,
    summary="Listar Transferencias Financieras",
    description="Obtiene el historial de transferencias entre cuentas propias de la empresa.",
    parameters=pagination_parameters,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="FinancialTransferListApiResponse",
                data_serializer=FinancialTransferListSerializer,
                is_list=True,
            ),
            description="Transferencias obtenidas correctamente.",
        ),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

finance_transfer_detail_schema = extend_schema(
    tags=TAG_FINANCE,
    summary="Obtener Transferencia Financiera",
    description="Obtiene los datos detallados de una transferencia entre cuentas.",
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="FinancialTransferDetailApiResponse",
                data_serializer=FinancialTransferListSerializer,
            ),
            description="Detalle de la transferencia obtenido.",
        ),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
        404: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

finance_transfer_create_schema = extend_schema(
    tags=TAG_FINANCE,
    summary="Realizar Transferencia Entre Cuentas",
    description="Transfiere fondos entre dos cuentas propias en una transacción atómica sin alterar ingresos/gastos.",
    request=FinancialTransferCreateSerializer,
    responses={
        201: OpenApiResponse(
            response=build_api_response_schema(
                name="FinancialTransferCreateApiResponse",
                data_serializer=FinancialTransferListSerializer,
            ),
            description="Transferencia ejecutada correctamente.",
        ),
        400: OpenApiResponse(response=ValidationErrorResponseSerializer),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

finance_transfer_cancel_schema = extend_schema(
    tags=TAG_FINANCE,
    summary="Cancelar Transferencia",
    description="Cancela una transferencia previa restaurando los fondos en ambas cuentas.",
    request=FinancialTransferCancelSerializer,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="FinancialTransferCancelApiResponse",
                data_serializer=FinancialTransferListSerializer,
            ),
            description="Transferencia cancelada con éxito.",
        ),
        400: OpenApiResponse(response=ValidationErrorResponseSerializer),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

# -------------------------------------------------------------------------
# Conciliaciones Financieras
# -------------------------------------------------------------------------

finance_reconciliation_list_schema = extend_schema(
    tags=TAG_FINANCE,
    summary="Listar Conciliaciones",
    description="Obtiene el historial de conciliaciones y arqueos de saldos de cuentas.",
    parameters=pagination_parameters,
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="FinancialReconciliationListApiResponse",
                data_serializer=FinancialReconciliationListSerializer,
                is_list=True,
            ),
            description="Conciliaciones obtenidas.",
        ),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

finance_reconciliation_detail_schema = extend_schema(
    tags=TAG_FINANCE,
    summary="Obtener Conciliación",
    description="Obtiene los detalles de una conciliación de cuenta.",
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="FinancialReconciliationDetailApiResponse",
                data_serializer=FinancialReconciliationListSerializer,
            ),
            description="Detalle de la conciliación obtenido.",
        ),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
        404: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

finance_reconciliation_create_schema = extend_schema(
    tags=TAG_FINANCE,
    summary="Crear Conciliación",
    description="Inicia un proceso de conciliación comparando el saldo de extracto/físico con el saldo en libros.",
    request=FinancialReconciliationCreateSerializer,
    responses={
        201: OpenApiResponse(
            response=build_api_response_schema(
                name="FinancialReconciliationCreateApiResponse",
                data_serializer=FinancialReconciliationListSerializer,
            ),
            description="Conciliación iniciada.",
        ),
        400: OpenApiResponse(response=ValidationErrorResponseSerializer),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)

finance_reconciliation_close_schema = extend_schema(
    tags=TAG_FINANCE,
    summary="Cerrar y Aprobar Conciliación",
    description="Cierra formalmente una conciliación marcándola como conciliada.",
    responses={
        200: OpenApiResponse(
            response=build_api_response_schema(
                name="FinancialReconciliationCloseApiResponse",
                data_serializer=FinancialReconciliationListSerializer,
            ),
            description="Conciliación aprobada y cerrada.",
        ),
        400: OpenApiResponse(response=ValidationErrorResponseSerializer),
        401: OpenApiResponse(response=ApiErrorResponseSerializer),
    },
)
