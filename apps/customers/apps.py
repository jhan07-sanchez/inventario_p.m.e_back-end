from django.apps import AppConfig


class CustomersConfig(AppConfig):
    """
    Configuración para la aplicación de clientes.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.customers"
    verbose_name = "Clientes"
