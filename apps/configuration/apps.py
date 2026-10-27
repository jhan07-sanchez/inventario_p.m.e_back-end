from django.apps import AppConfig


class ConfigurationConfig(AppConfig):
    """
    Configuracion para la aplicacion de parametros Globales.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.configuration"
    verbose_name = "Configuración Global"
