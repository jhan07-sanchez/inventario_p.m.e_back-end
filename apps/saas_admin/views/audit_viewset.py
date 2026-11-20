from rest_framework import status
from django.db.models import Q

from apps.core.models.audit_log import AuditLog
from apps.core.pagination.custom_pagination import CustomPagination
from apps.core.views.base_viewset import BaseGenericViewSet
from apps.saas_admin.permissions import IsSaaSAdmin
from apps.saas_admin.serializers.audit_serializer import SaaSAuditLogSerializer


class SaaSAuditViewSet(BaseGenericViewSet):
    """
    ViewSet administrativo para la consulta y auditoría de eventos de la plataforma SaaS.
    Permite auditar accesos, inicios de sesión de soporte, modificaciones de empresas y operaciones críticas.
    Protegido por IsSaaSAdmin.
    """

    permission_classes = [IsSaaSAdmin]
    pagination_class = CustomPagination
    serializer_class = SaaSAuditLogSerializer

    def list(self, request, *args, **kwargs):
        """Consulta los registros de auditoría global con filtros y orden cronológico."""
        search = request.query_params.get("search")
        method = request.query_params.get("method")
        status_code = request.query_params.get("status_code")
        security_event = request.query_params.get("security_event")

        qs = AuditLog.objects.select_related("user", "company").order_by("-created_at")

        if search:
            term = search.strip()
            qs = qs.filter(
                Q(path__icontains=term)
                | Q(user__email__icontains=term)
                | Q(user__username__icontains=term)
                | Q(company__business_name__icontains=term)
                | Q(ip_address__icontains=term)
            )

        if method:
            qs = qs.filter(method=method.upper())

        if status_code:
            try:
                qs = qs.filter(status_code=int(status_code))
            except ValueError:
                pass

        if security_event:
            qs = qs.filter(payload__security_event=security_event)

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = SaaSAuditLogSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = SaaSAuditLogSerializer(qs, many=True)
        return self.success_response(
            data=serializer.data,
            code="SAAS_AUDIT_LOGS_FETCHED",
            message="Registros de auditoría obtenidos correctamente.",
        )
