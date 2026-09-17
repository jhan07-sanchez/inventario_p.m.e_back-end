from django.apps import AppConfig


class InvoicesConfig(AppConfig):
    """
    Configuración para la aplicación de facturas.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.invoices"
    verbose_name = "Facturación y Documentos"
