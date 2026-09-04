from django.apps import AppConfig


class ProductsConfig(AppConfig):
    """
    Configuración para la aplicación de productos.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.products"
    verbose_name = "Productos"
