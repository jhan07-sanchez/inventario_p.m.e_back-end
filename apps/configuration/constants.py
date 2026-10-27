from typing import Any, Dict


class ParameterCategory:
    GENERAL = "GENERAL"
    BILLING = "BILLING"
    INVENTORY = "INVENTORY"
    SECURITY = "SECURITY"


SYSTEM_PARAMETERS_CATALOG: Dict[str, Dict[str, Any]] = {
    "DEFAULT_TAX_RATE": {
        "key": "DEFAULT_TAX_RATE",
        "data_type": "DECIMAL",
        "default": "0.19",
        "description": "Tasa de impuesto estándar aplicada a las ventas (IVA).",
        "category": ParameterCategory.BILLING,
    },
    "CURRENCY": {
        "key": "CURRENCY",
        "data_type": "STRING",
        "default": "COP",
        "description": "Código ISO de la moneda principal del sistema.",
        "category": ParameterCategory.GENERAL,
    },
    "CURRENCY_SYMBOL": {
        "key": "CURRENCY_SYMBOL",
        "data_type": "STRING",
        "default": "$",
        "description": "Símbolo de moneda para representación visual e impresión.",
        "category": ParameterCategory.GENERAL,
    },
    "ALLOW_NEGATIVE_STOCK": {
        "key": "ALLOW_NEGATIVE_STOCK",
        "data_type": "BOOLEAN",
        "default": "false",
        "description": "Permitir o bloquear ventas cuando no haya stock suficiente.",
        "category": ParameterCategory.INVENTORY,
    },
    "INVENTORY_MIN_STOCK_ALERT": {
        "key": "INVENTORY_MIN_STOCK_ALERT",
        "data_type": "INTEGER",
        "default": "5",
        "description": "Umbral de alerta general para existencias mínimas.",
        "category": ParameterCategory.INVENTORY,
    },
    "INVOICE_AUTO_NUMBERING": {
        "key": "INVOICE_AUTO_NUMBERING",
        "data_type": "BOOLEAN",
        "default": "true",
        "description": "Generación consecutiva automática de números de factura.",
        "category": ParameterCategory.BILLING,
    },
    "SESSION_TIMEOUT_MINUTES": {
        "key": "SESSION_TIMEOUT_MINUTES",
        "data_type": "INTEGER",
        "default": "120",
        "description": "Tiempo de inactividad antes de expirar la sesión administrativa.",
        "category": ParameterCategory.SECURITY,
    },
}
