import logging
from typing import Optional

from django.contrib.auth import get_user_model
from django.db import OperationalError, ProgrammingError
from django.db.models import Q, QuerySet

from apps.core.selectors.base_selector import BaseSelector
from apps.notifications.models.notification import Notification

logger = logging.getLogger(__name__)
User = get_user_model()


class NotificationSelector(BaseSelector[Notification]):
    """
    Selector para consultas de lectura sobre el modelo Notification.
    Encapsula filtros multi-tenant, búsquedas por categoría, estado de lectura y ordenamiento.
    Incluye protección resiliente ante tablas pendientes de migración.
    """

    def __init__(self):
        super().__init__(Notification)

    def get_user_notifications_queryset(
        self,
        user,
        company_id: Optional[int] = None,
        is_read: Optional[bool] = None,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        search: Optional[str] = None,
        include_global: bool = True,
    ) -> QuerySet[Notification]:
        """
        Retorna el QuerySet base de notificaciones para un usuario específico,
        respetando el aislamiento multi-tenant y filtros opcionales.
        """
        try:
            qs = self.model.objects.filter(recipient=user)

            # Filtro de tenant
            if company_id is not None:
                try:
                    c_id = int(company_id)
                    if include_global:
                        qs = qs.filter(Q(company_id=c_id) | Q(company__isnull=True))
                    else:
                        qs = qs.filter(company_id=c_id)
                except (ValueError, TypeError):
                    pass

            # Filtro estado de lectura
            if is_read is not None:
                qs = qs.filter(is_read=bool(is_read))

            # Filtro de categoría
            if category:
                qs = qs.filter(category=category.upper())

            # Filtro de prioridad
            if priority:
                qs = qs.filter(priority=priority.upper())

            # Búsqueda por texto en título o mensaje
            if search:
                qs = qs.filter(
                    Q(title__icontains=search)
                    | Q(message__icontains=search)
                    | Q(event_type__icontains=search)
                )

            return qs.order_by("-created_at")

        except (ProgrammingError, OperationalError) as e:
            logger.warning(
                "Error de base de datos en NotificationSelector (posible tabla inexistente): %s",
                e,
            )
            return self.model.objects.none()

    def get_user_unread_count(
        self,
        user,
        company_id: Optional[int] = None,
        include_global: bool = True,
    ) -> int:
        """
        Calcula de forma ligera y optimizada el número de notificaciones no leídas
        para el usuario dado.
        """
        try:
            qs = self.get_user_notifications_queryset(
                user=user,
                company_id=company_id,
                is_read=False,
                include_global=include_global,
            )
            return qs.count()
        except (ProgrammingError, OperationalError) as e:
            logger.warning(
                "No se pudo consultar el contador de no leídas (tabla no disponible): %s",
                e,
            )
            return 0

    def get_notification_for_user(
        self,
        notification_id: int,
        user,
    ) -> Optional[Notification]:
        """
        Obtiene una notificación por su ID verificando propiedad del destinatario
        para prevenir vulnerabilidades de IDOR (Insecure Direct Object Reference).
        """
        try:
            return self.model.objects.filter(
                id_notification=notification_id,
                recipient=user,
            ).first()
        except (ProgrammingError, OperationalError) as e:
            logger.warning("Error al buscar notificación por ID: %s", e)
            return None
