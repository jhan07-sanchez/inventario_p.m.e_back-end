# ======================================
# Django REST Framework
# ======================================

REST_FRAMEWORK = {
    # Autenticación por defecto
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    # Permisos por defecto
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    # Paginación
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.custom_pagination.CustomPagination",
    "PAGE_SIZE": 10,
    # Esquema OpenAPI
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Renderizamos únicamente JSON
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "EXCEPTION_HANDLER": "apps.core.exceptions.exception_handler.custom_exception_handler",
    # Throttling
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "auth_login": "5/minute",
        "auth_refresh": "10/minute",
    },
}


# ======================================
# DRF Spectacular
# ======================================

SPECTACULAR_SETTINGS = {
    "TITLE": "inventario-pme API",
    "DESCRIPTION": (
        "API REST empresarial del sistema **inventario-pme**, un ERP modular "
        "diseñado para la gestión integral de inventarios, ventas, compras, "
        "facturación y administración de usuarios para pequeñas y medianas "
        "empresas (PyMEs).\n\n"
        "---\n\n"
        "## Respuestas Estandarizadas\n\n"
        "Todos los endpoints retornan un objeto JSON con la siguiente estructura:\n\n"
        "```json\n"
        "{\n"
        '  "success": true,\n'
        '  "code": "RESOURCE_ACTION",\n'
        '  "message": "Mensaje legible.",\n'
        '  "data": { ... },\n'
        '  "errors": null\n'
        "}\n"
        "```\n\n"
        "- **`success`** — `true` si la operación fue exitosa, `false` en caso de error.\n"
        "- **`code`** — Código semántico del resultado (ej. `PRODUCT_CREATED`, "
        "`SALE_COMPLETED`, `AUTHENTICATION_FAILED`).\n"
        "- **`message`** — Mensaje descriptivo para el usuario.\n"
        "- **`data`** — Payload con los datos solicitados o el recurso creado/modificado.\n"
        "- **`errors`** — Diccionario con detalle de errores de validación "
        "(`null` cuando `success` es `true`).\n\n"
        "## Autenticación (JWT Bearer)\n\n"
        "La API utiliza tokens JWT. Para autenticarse:\n\n"
        "1. Obtenga un token mediante `POST /api/v1/auth/login/`.\n"
        "2. Incluya el Access Token en el encabezado de cada solicitud:\n"
        "   ```\n"
        "   Authorization: Bearer <access_token>\n"
        "   ```\n"
        "3. Cuando el Access Token expire, renuévelo con `POST /api/v1/auth/refresh/`.\n\n"
        "## Códigos Semánticos de Error\n\n"
        "Los errores incluyen códigos descriptivos como:\n"
        "`PRODUCT_ALREADY_EXISTS`, `CATEGORY_INACTIVE`, `SALE_ALREADY_COMPLETED`, "
        "`INSUFFICIENT_STOCK`, `PURCHASE_INVALID_STATUS`, `AUTHENTICATION_FAILED`, "
        "`PERMISSION_DENIED`, `NOT_FOUND`, entre otros."
    ),
    "TOS": "https://www.inventario-pme.com/terms/",
    "CONTACT": {
        "name": "Soporte inventario-pme",
        "url": "",
        "email": "jhansancheza@gmail.com",
    },
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SORT_OPERATIONS": False,
    # Habilita el preprocesamiento de enums para componentes limpios
    "ENUM_NAME_OVERRIDES": {
        "DocumentTypeEnum": "apps.customers.models.customer.Customer.DocumentType",
        "InvoiceDocumentTypeEnum": "apps.invoices.models.invoice.Invoice.DocumentType",
        "InventoryMovementTypeEnum": "apps.inventory.models.inventory_movement.InventoryMovement.MovementType",
        "CashMovementTypeEnum": "apps.cash.models.cash_movement.CashMovement.MovementType",
        "PurchaseStatusEnum": "apps.purchases.models.purchase.Purchase.Status",
        "SaleStatusEnum": "apps.sales.models.sale.Sale.SaleStatus",
        "InvoiceStatusEnum": "apps.invoices.models.invoice.Invoice.Status",
        "CashSessionStatusEnum": "apps.cash.models.cash_session.CashSession.SessionStatus",
    },
    # Configuramos los esquemas globales y componentes de seguridad
    "COMPONENTS": {
        "securitySchemes": {
            "jwtAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Autenticación mediante JWT. Colocar el token de acceso obtenido en el login.",
            }
        }
    },
    "SECURITY": [{"jwtAuth": []}],
    # Agrupación y metadata extendida de ReDoc
    "EXTENSIONS_INFO": {},
    "TAGS": [
        # ── Seguridad y Accesos ──
        {
            "name": "Authentication",
            "description": "Ciclo de vida de sesiones y tokens JWT.",
        },
        {
            "name": "Users",
            "description": "Directorio de usuarios del sistema.",
        },
        {
            "name": "Roles",
            "description": "Roles y niveles de acceso.",
        },
        {
            "name": "User Roles",
            "description": "Asignación de roles a usuarios.",
        },
        {
            "name": "Security Dashboard",
            "description": "Panel principal de seguridad y navegación.",
        },
        # ── Catálogo ──
        {
            "name": "Categories",
            "description": "Categorías de productos.",
        },
        {
            "name": "Products",
            "description": "Catálogo de productos, precios y unidades de medida.",
        },
        # ── Inventario ──
        {
            "name": "Inventory",
            "description": "Stock actual, mínimos, máximos, alertas y movimientos de inventario.",
        },
        # ── Ventas y Facturación ──
        {
            "name": "Customers",
            "description": "Clientes y datos de facturación.",
        },
        {
            "name": "Sales",
            "description": "Ventas, ventas rápidas del POS y su ciclo de vida.",
        },
        {
            "name": "Cash",
            "description": "Gestión de cajas registradoras, apertura/cierre de sesiones y movimientos de efectivo.",
        },
        {
            "name": "Invoices",
            "description": "Facturas de venta, tickets POS y facturas de compra.",
        },
        {
            "name": "Invoice Templates",
            "description": "Plantillas documentales para impresión.",
        },
        # ── Proveedores y Compras ──
        {
            "name": "Suppliers",
            "description": "Proveedores y datos de contacto.",
        },
        {
            "name": "Purchases",
            "description": "Órdenes de compra y su ciclo de vida.",
        },
        # ── Sistema ──
        {
            "name": "Company Info",
            "description": "Datos fiscales y de contacto de la empresa.",
        },
        {
            "name": "Configuration",
            "description": "Configuración y administración del sistema.",
        },
        {
            "name": "System",
            "description": "Monitoreo y estado del sistema.",
        },
        {
            "name": "Configuration Audits",
            "description": "Historial de auditoría de cambios en la configuración.",
        },
    ],
    "EXTENSIONS_ROOT": {
        "x-tagGroups": [
            {
                "name": "Seguridad y Accesos",
                "tags": [
                    "Authentication",
                    "Users",
                    "Roles",
                    "User Roles",
                    "Security Dashboard",
                ],
            },
            {
                "name": "Catálogo",
                "tags": ["Categories", "Products"],
            },
            {
                "name": "Inventario",
                "tags": ["Inventory"],
            },
            {
                "name": "Ventas y Facturación",
                "tags": ["Customers", "Sales", "Cash", "Invoices", "Invoice Templates"],
            },
            {
                "name": "Proveedores y Compras",
                "tags": ["Suppliers", "Purchases"],
            },
            {
                "name": "Sistema",
                "tags": ["Company Info", "Configuration", "Configuration Audits", "System"],
            },
        ]
    },
    # Removemos inline serializers anónimos por defecto en Spectacular (si es posible a nivel de prefijos)
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]",
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
    ],
}
