from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from apps.core.selectors.base_selector import BaseSelector
from apps.configuration.models import ConfigurationAudit


class ConfigurationAuditSelector(BaseSelector[ConfigurationAudit]):
    """
    Selector encargado de las consultas relacionadas
    con la auditoría de configuración.
    """

    def __init__(self):
        super().__init__(ConfigurationAudit)

    def get_queryset(self) -> QuerySet[ConfigurationAudit]:
        """
        Retorna el queryset base de auditorías optimizando
        las relaciones con el usuario y el parámetro.
        """
        return (
            super()
            .get_queryset()
            .select_related("user", "parameter")
            .order_by("-created_at")
        )

    @staticmethod
    def get_audits() -> QuerySet[ConfigurationAudit]:
        """Retorna todos los registros de auditoría."""
        return ConfigurationAuditSelector().get_all()

    @staticmethod
    def get_audit_by_id(audit_id: int) -> ConfigurationAudit:
        """Obtiene un registro de auditoría por su ID."""
        return get_object_or_404(
            ConfigurationAuditSelector().get_queryset(),
            pk=audit_id,
        )

    @staticmethod
    def get_audits_by_parameter(parameter_id: int) -> QuerySet[ConfigurationAudit]:
        """Retorna el historial de un parámetro específico."""
        return (
            ConfigurationAuditSelector()
            .get_queryset()
            .filter(parameter_id=parameter_id)
        )
