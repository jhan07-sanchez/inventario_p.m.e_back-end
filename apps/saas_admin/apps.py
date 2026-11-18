from django.apps import AppConfig


class SaasAdminConfig(AppConfig):
    """
    Configuración para la aplicación de administración del SaaS.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.saas_admin"
    verbose_name = "Administración SaaS"
