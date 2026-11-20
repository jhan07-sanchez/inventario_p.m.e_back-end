import logging
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.views.base_viewset import BaseViewSet
from apps.notifications.selectors.notification_selector import NotificationSelector
from apps.notifications.serializers.notification_serializer import (
    NotificationSerializer,
    NotificationUnreadCountSerializer,
)
from apps.notifications.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class NotificationViewSet(BaseViewSet):
    """
    ViewSet para la consulta y gestión centralizada de notificaciones y alertas.
    Endpoints:
    - GET /api/v1/notifications/ : Lista paginada y filtrable de notificaciones del usuario.
    - GET /api/v1/notifications/{id}/ : Detalle de una notificación (con validación de pertenencia).
    - GET /api/v1/notifications/unread-count/ : Conteo rápido de no leídas para la campanita.
    - POST /api/v1/notifications/{id}/read/ : Marcar como leída.
    - POST /api/v1/notifications/{id}/unread/ : Marcar como no leída.
    - POST /api/v1/notifications/mark-all-read/ : Marcar todas las notificaciones como leídas.
    - DELETE /api/v1/notifications/{id}/ : Eliminación lógica de una notificación propia.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selector = NotificationSelector()
        self.service = NotificationService()

    def get_queryset(self):
        """
        Garantiza que ningún usuario pueda acceder a notificaciones ajenas.
        Aplica filtros multi-tenant y parámetros opcionales.
        """
        user = self.request.user
        company_id = self.get_company_id(self.request)

        # Si el usuario es superuser o staff y no hay company_id especificado,
        # incluye notificaciones globales de SaaS
        is_read_param = self.request.query_params.get("is_read")
        is_read = None
        if is_read_param is not None:
            is_read = is_read_param.lower() in ("true", "1")

        category = self.request.query_params.get("category")
        priority = self.request.query_params.get("priority")
        search = self.request.query_params.get("search")

        return self.selector.get_user_notifications_queryset(
            user=user,
            company_id=company_id,
            is_read=is_read,
            category=category,
            priority=priority,
            search=search,
            include_global=True,
        )

    def list(self, request, *args, **kwargs):
        """
        Lista las notificaciones del usuario autenticado con soporte de paginación.
        """
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return self.success_response(
            data=serializer.data,
            message="Notificaciones obtenidas correctamente.",
        )

    def retrieve(self, request, pk=None, *args, **kwargs):
        """
        Retorna el detalle de una notificación propia verificando IDOR.
        """
        notif = self.selector.get_notification_for_user(pk, request.user)
        if not notif:
            return self.error_response(
                message="Notificación no encontrada o no pertenece al usuario.",
                status_code=status.HTTP_404_NOT_FOUND,
                code="NOT_FOUND",
            )

        serializer = self.get_serializer(notif)
        return self.success_response(
            data=serializer.data,
            message="Detalle de notificación obtenido correctamente.",
        )

    @action(detail=False, methods=["GET"], url_path="unread-count")
    def unread_count(self, request):
        """
        Endpoint ultra liviano para actualizar el badge de la campanita.
        """
        company_id = self.get_company_id(request)
        count = self.selector.get_user_unread_count(
            user=request.user,
            company_id=company_id,
            include_global=True,
        )

        data = {
            "unread_count": count,
            "company_id": company_id,
        }
        return self.success_response(
            data=data,
            message="Conteo de no leídas obtenido correctamente.",
        )

    @action(detail=True, methods=["POST"], url_path="read")
    def mark_read(self, request, pk=None):
        """
        Marca una notificación como leída.
        """
        notif = self.service.mark_as_read(pk, request.user)
        if not notif:
            return self.error_response(
                message="Notificación no encontrada o no pertenece al usuario.",
                status_code=status.HTTP_404_NOT_FOUND,
                code="NOT_FOUND",
            )

        serializer = self.get_serializer(notif)
        return self.success_response(
            data=serializer.data,
            message="Notificación marcada como leída.",
        )

    @action(detail=True, methods=["POST"], url_path="unread")
    def mark_unread(self, request, pk=None):
        """
        Marca una notificación como no leída.
        """
        notif = self.service.mark_as_unread(pk, request.user)
        if not notif:
            return self.error_response(
                message="Notificación no encontrada o no pertenece al usuario.",
                status_code=status.HTTP_404_NOT_FOUND,
                code="NOT_FOUND",
            )

        serializer = self.get_serializer(notif)
        return self.success_response(
            data=serializer.data,
            message="Notificación marcada como no leída.",
        )

    @action(detail=False, methods=["POST"], url_path="mark-all-read")
    def mark_all_read(self, request):
        """
        Marca todas las notificaciones pendientes del usuario como leídas.
        """
        company_id = self.get_company_id(request)
        count = self.service.mark_all_as_read(request.user, company_id=company_id)

        return self.success_response(
            data={"marked_count": count},
            message=f"Se marcaron {count} notificaciones como leídas.",
        )

    def destroy(self, request, pk=None, *args, **kwargs):
        """
        Elimina lógicamente una notificación propia.
        """
        deleted = self.service.soft_delete_notification(pk, request.user)
        if not deleted:
            return self.error_response(
                message="Notificación no encontrada o no pertenece al usuario.",
                status_code=status.HTTP_404_NOT_FOUND,
                code="NOT_FOUND",
            )

        return self.success_response(
            data={"deleted": True},
            message="Notificación eliminada correctamente.",
        )
