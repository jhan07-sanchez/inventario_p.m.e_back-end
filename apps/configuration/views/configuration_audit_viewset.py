from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.configuration.docs import (
    configuration_audit_detail_schema,
    configuration_audit_list_schema,
)
from apps.configuration.selectors import ConfigurationAuditSelector
from apps.configuration.serializers import ConfigurationAuditSerializer
from apps.core.security import HasPermission
from apps.users.permissions import IsAuthenticatedAndActive


class ConfigurationAuditViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet de solo lectura para consultar el historial de cambios.
    No permite crear, editar ni borrar registros manualmente.
    """

    permission_classes = [IsAuthenticatedAndActive, HasPermission("settings.view")]

    # Filtros y búsquedas para el frontend
    filter_backends = [SearchFilter, OrderingFilter, DjangoFilterBackend]
    search_fields = ["parameter_key", "user__first_name", "user__last_name", "reason"]
    filterset_fields = ["action", "parameter"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        return ConfigurationAuditSelector.get_audits()

    def get_serializer_class(self):
        return ConfigurationAuditSerializer

    @configuration_audit_list_schema
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @configuration_audit_detail_schema
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
