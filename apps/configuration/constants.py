from typing import Any, Dict


class ParameterCategory:
    GENERAL = "GENERAL"
    BILLING = "BILLING"
    INVENTORY = "INVENTORY"
    SECURITY = "SECURITY"


SYSTEM_PARAMETERS_CATALOG: Dict[str, Dict[str, Any]] = {
    # --- Facturación y Finanzas ---
    "DEFAULT_TAX_RATE": {
        "key": "DEFAULT_TAX_RATE",
        "data_type": "DECIMAL",
        "default": "0.19",
        "description": "Tasa de impuesto estándar aplicada a las ventas (IVA).",
        "category": ParameterCategory.BILLING,
    },
    "SYSTEM_DEFAULT_TAX_RATE": {
        "key": "SYSTEM_DEFAULT_TAX_RATE",
        "data_type": "DECIMAL",
        "default": "0.19",
        "description": "Tasa de impuesto estándar aplicada a las ventas (alias para facturación).",
        "category": ParameterCategory.BILLING,
    },
    "CURRENCY": {
        "key": "CURRENCY",
        "data_type": "STRING",
        "default": "COP",
        "description": "Código ISO de la moneda principal del sistema.",
        "category": ParameterCategory.GENERAL,
    },
    "SYSTEM_DEFAULT_CURRENCY": {
        "key": "SYSTEM_DEFAULT_CURRENCY",
        "data_type": "STRING",
        "default": "COP",
        "description": "Código ISO de la moneda principal de la empresa.",
        "category": ParameterCategory.GENERAL,
    },
    "CURRENCY_SYMBOL": {
        "key": "CURRENCY_SYMBOL",
        "data_type": "STRING",
        "default": "$",
        "description": "Símbolo de moneda para representación visual e impresión.",
        "category": ParameterCategory.GENERAL,
    },
    "INVOICE_AUTO_NUMBERING": {
        "key": "INVOICE_AUTO_NUMBERING",
        "data_type": "BOOLEAN",
        "default": "true",
        "description": "Generación consecutiva automática de números de factura.",
        "category": ParameterCategory.BILLING,
    },
    # --- Inventario ---
    "ALLOW_NEGATIVE_STOCK": {
        "key": "ALLOW_NEGATIVE_STOCK",
        "data_type": "BOOLEAN",
        "default": "false",
        "description": "Permitir o bloquear ventas cuando no haya stock suficiente.",
        "category": ParameterCategory.INVENTORY,
    },
    "INVENTORY_ALLOW_NEGATIVE_STOCK": {
        "key": "INVENTORY_ALLOW_NEGATIVE_STOCK",
        "data_type": "BOOLEAN",
        "default": "false",
        "description": "Permitir ventas si el stock llega a cero (alias de inventario).",
        "category": ParameterCategory.INVENTORY,
    },
    "INVENTORY_MIN_STOCK_ALERT": {
        "key": "INVENTORY_MIN_STOCK_ALERT",
        "data_type": "INTEGER",
        "default": "5",
        "description": "Umbral de alerta general para existencias mínimas.",
        "category": ParameterCategory.INVENTORY,
    },
    "INVENTORY_DEFAULT_LOW_STOCK_ALERT": {
        "key": "INVENTORY_DEFAULT_LOW_STOCK_ALERT",
        "data_type": "INTEGER",
        "default": "5",
        "description": "Cantidad por defecto para alertar existencias bajas.",
        "category": ParameterCategory.INVENTORY,
    },
    # --- Seguridad y Sesiones ---
    "SECURITY_PASSWORD_MIN_LENGTH": {
        "key": "SECURITY_PASSWORD_MIN_LENGTH",
        "data_type": "INTEGER",
        "default": "8",
        "description": "Longitud mínima requerida para las contraseñas de usuario.",
        "category": ParameterCategory.SECURITY,
    },
    "SECURITY_MAX_LOGIN_ATTEMPTS": {
        "key": "SECURITY_MAX_LOGIN_ATTEMPTS",
        "data_type": "INTEGER",
        "default": "5",
        "description": "Intentos fallidos de inicio de sesión antes de bloquear la cuenta.",
        "category": ParameterCategory.SECURITY,
    },
    "SECURITY_SESSION_TIMEOUT_MINUTES": {
        "key": "SECURITY_SESSION_TIMEOUT_MINUTES",
        "data_type": "INTEGER",
        "default": "60",
        "description": "Minutos de inactividad antes de cerrar la sesión automáticamente.",
        "category": ParameterCategory.SECURITY,
    },
    "SESSION_TIMEOUT_MINUTES": {
        "key": "SESSION_TIMEOUT_MINUTES",
        "data_type": "INTEGER",
        "default": "60",
        "description": "Tiempo de inactividad antes de expirar la sesión administrativa.",
        "category": ParameterCategory.SECURITY,
    },
    # --- Preferencias Generales ---
    "SYSTEM_DATE_FORMAT": {
        "key": "SYSTEM_DATE_FORMAT",
        "data_type": "STRING",
        "default": "DD/MM/YYYY",
        "description": "Formato de visualización de fechas en el sistema.",
        "category": ParameterCategory.GENERAL,
    },
    "SYSTEM_ITEMS_PER_PAGE": {
        "key": "SYSTEM_ITEMS_PER_PAGE",
        "data_type": "INTEGER",
        "default": "10",
        "description": "Cantidad de registros por página en las tablas del sistema.",
        "category": ParameterCategory.GENERAL,
    },
    "SYSTEM_THEME": {
        "key": "SYSTEM_THEME",
        "data_type": "STRING",
        "default": "light",
        "description": "Tema visual del sistema (light / dark).",
        "category": ParameterCategory.GENERAL,
    },
}

