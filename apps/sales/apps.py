from django.apps import AppConfig


class SalesConfig(AppConfig):
    """
    Configuración para la aplicación de Ventas.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.sales"
    verbose_name = "Ventas"
