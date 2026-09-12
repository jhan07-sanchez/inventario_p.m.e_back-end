from django.apps import AppConfig


class InventoryConfig(AppConfig):
    """
    Configuración para la aplicación de inventario.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.inventory"
    verbose_name = "Inventario"
