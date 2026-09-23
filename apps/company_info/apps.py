from django.apps import AppConfig


class CompanyInfoConfig(AppConfig):
    """
    Configuración para la aplicación de Información de Empresa.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.company_info"
    verbose_name = "Información de Empresa"
