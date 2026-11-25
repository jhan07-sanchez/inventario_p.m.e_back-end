from django.db import models


class NotificationCategory(models.TextChoices):
    """
    Categorías funcionales de notificaciones en el sistema P.M.E.
    """

    INVENTORY = "INVENTORY", "Inventario"
    SALES = "SALES", "Ventas"
    PURCHASES = "PURCHASES", "Compras"
    CASH = "CASH", "Caja"
    FINANCE = "FINANCE", "Finanzas"
    SECURITY = "SECURITY", "Seguridad y Accesos"
    SUBSCRIPTION = "SUBSCRIPTION", "Planes y Suscripciones"
    SYSTEM = "SYSTEM", "Sistema y Versiones"
    CUSTOMERS = "CUSTOMERS", "Clientes"
    SUPPLIERS = "SUPPLIERS", "Proveedores"


class NotificationPriority(models.TextChoices):
    """
    Niveles de severidad y prioridad para clasificación visual y alertas.
    """

    INFO = "INFO", "Informativa"
    SUCCESS = "SUCCESS", "Éxito"
    WARNING = "WARNING", "Advertencia"
    CRITICAL = "CRITICAL", "Crítica"


class NotificationEventType:
    """
    Catálogo de códigos de eventos de negocio emitidos por el ERP.
    """

    # Inventario
    INVENTORY_STOCK_LOW = "INVENTORY.STOCK_LOW"
    INVENTORY_STOCK_EXHAUSTED = "INVENTORY.STOCK_EXHAUSTED"
    INVENTORY_MOVEMENT_ADJUSTMENT = "INVENTORY.MOVEMENT_ADJUSTMENT"

    # Ventas
    SALE_COMPLETED = "SALE.COMPLETED"
    SALE_CANCELLED = "SALE.CANCELLED"

    # Compras
    PURCHASE_REGISTERED = "PURCHASE.REGISTERED"
    PURCHASE_CANCELLED = "PURCHASE.CANCELLED"

    # Caja y Finanzas
    CASH_SESSION_OPENED = "CASH.SESSION_OPENED"
    CASH_SESSION_CLOSED = "CASH.SESSION_CLOSED"
    CASH_SESSION_CLOSED_DIFFERENCE = "CASH.SESSION_CLOSED_DIFFERENCE"

    # Seguridad y Usuarios
    USER_CREATED = "USER.CREATED"
    USER_ROLE_CHANGED = "USER.ROLE_CHANGED"
    USER_PASSWORD_RESET = "USER.PASSWORD_RESET"

    # Suscripciones y SaaS
    SUBSCRIPTION_ASSIGNED = "SUBSCRIPTION.ASSIGNED"
    SUBSCRIPTION_RENEWED = "SUBSCRIPTION.RENEWED"
    SUBSCRIPTION_CHANGED = "SUBSCRIPTION.CHANGED"
    SUBSCRIPTION_EXPIRING = "SUBSCRIPTION.EXPIRING"

    # Sistema
    SOFTWARE_VERSION_PUBLISHED = "SYSTEM.VERSION_PUBLISHED"
