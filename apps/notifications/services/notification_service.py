import logging
from typing import Any, Iterable, List, Optional, Union

from django.contrib.auth import get_user_model
from django.db import OperationalError, ProgrammingError, transaction
from django.utils import timezone

from apps.core.services.base_service import BaseService
from apps.notifications.enums import NotificationCategory, NotificationPriority, NotificationEventType
from apps.notifications.models.notification import Notification
from apps.notifications.selectors.notification_selector import NotificationSelector
from apps.notifications.services.recipient_resolver import RecipientResolver

logger = logging.getLogger(__name__)
User = get_user_model()


class NotificationService(BaseService[Notification]):
    """
    Servicio central de creación, gestión y despacho de notificaciones y alertas.
    Garantiza:
    - Desacoplamiento de las transacciones de negocio.
    - Idempotencia mediante claves únicas para evitar eventos duplicados.
    - Resolución automática de destinatarios basada en roles/permisos.
    - Resiliencia ante fallos transitorios de base de datos.
    """

    def __init__(self):
        super().__init__(Notification)
        self.selector = NotificationSelector()

    def notify(
        self,
        title: str,
        message: str,
        category: str = NotificationCategory.SYSTEM,
        priority: str = NotificationPriority.INFO,
        event_type: str = "",
        company_id: Optional[Union[int, str]] = None,
        recipients: Optional[Iterable[Any]] = None,
        action_url: str = "",
        origin_id: str = "",
        metadata: Optional[dict] = None,
        idempotency_key: Optional[str] = None,
        permission_code: Optional[str] = None,
        role_name: Optional[str] = None,
        is_saas_admin: bool = False,
        include_owners: bool = True,
        exclude_user_ids: Optional[Iterable[int]] = None,
    ) -> List[Notification]:
        """
        Crea y despacha notificaciones a los destinatarios resueltos.
        """
        created_notifications = []

        try:
            # 1. Resolver lista de usuarios receptores
            if recipients is None:
                resolved_users = RecipientResolver.resolve_recipients(
                    company_id=company_id,
                    permission_code=permission_code,
                    role_name=role_name,
                    is_saas_admin=is_saas_admin,
                    include_owners=include_owners,
                    exclude_user_ids=exclude_user_ids,
                )
            else:
                resolved_users = RecipientResolver.resolve_recipients(
                    specific_users=recipients,
                    exclude_user_ids=exclude_user_ids,
                )

            if not resolved_users:
                logger.debug(
                    "NotificationService.notify: No se encontraron destinatarios para evento %s (company_id=%s)",
                    event_type,
                    company_id,
                )
                return []

            meta = metadata or {}
            c_id = None
            if company_id is not None:
                try:
                    c_id = int(company_id)
                except (ValueError, TypeError):
                    c_id = None

            # 2. Creación individual con verificación de idempotencia
            for user in resolved_users:
                if idempotency_key:
                    # Chequeo de idempotencia por usuario y clave
                    existing = self.model.objects.filter(
                        recipient=user,
                        idempotency_key=idempotency_key,
                    ).first()
                    if existing:
                        logger.debug(
                            "Notificación descartada por clave de idempotencia existente '%s' para usuario %s",
                            idempotency_key,
                            user.pk,
                        )
                        continue

                notif = self.model(
                    company_id=c_id,
                    recipient=user,
                    title=title,
                    message=message,
                    category=category,
                    priority=priority,
                    event_type=event_type,
                    action_url=action_url,
                    origin_id=str(origin_id) if origin_id is not None else "",
                    metadata=meta,
                    idempotency_key=idempotency_key,
                )
                notif.save()
                created_notifications.append(notif)

            logger.info(
                "Notificación emitida [evento=%s, categoría=%s, total=%d]",
                event_type,
                category,
                len(created_notifications),
            )

        except (ProgrammingError, OperationalError) as e:
            logger.warning(
                "No se pudo guardar la notificación en base de datos (posible tabla no migrada): %s",
                e,
            )
        except Exception as e:
            logger.error("Error inesperado en NotificationService.notify: %s", e, exc_info=True)

        return created_notifications

    def notify_on_commit(self, **kwargs) -> None:
        """
        Ejecuta la emisión de la notificación una vez que la transacción activa haga commit exitoso.
        Si no hay transacción activa, se ejecuta inmediatamente.
        """
        def _execute():
            self.notify(**kwargs)

        transaction.on_commit(_execute)

    def mark_as_read(self, notification_id: int, user) -> Optional[Notification]:
        """
        Marca como leída una notificación validando que pertenezca al usuario (IDOR protection).
        """
        notif = self.selector.get_notification_for_user(notification_id, user)
        if not notif:
            return None

        notif.mark_as_read(save=True)
        return notif

    def mark_as_unread(self, notification_id: int, user) -> Optional[Notification]:
        """
        Marca como no leída una notificación validando que pertenezca al usuario.
        """
        notif = self.selector.get_notification_for_user(notification_id, user)
        if not notif:
            return None

        notif.mark_as_unread(save=True)
        return notif

    def mark_all_as_read(self, user, company_id: Optional[int] = None) -> int:
        """
        Marca todas las notificaciones pendientes del usuario como leídas.
        """
        try:
            qs = self.selector.get_user_notifications_queryset(
                user=user,
                company_id=company_id,
                is_read=False,
            )
            count = qs.update(
                is_read=True,
                read_at=timezone.now(),
                updated_at=timezone.now(),
            )
            return count
        except (ProgrammingError, OperationalError) as e:
            logger.warning("Error en mark_all_as_read: %s", e)
            return 0

    def soft_delete_notification(self, notification_id: int, user) -> bool:
        """
        Elimina lógicamente una notificación asegurando pertenencia al usuario.
        """
        notif = self.selector.get_notification_for_user(notification_id, user)
        if not notif:
            return False

        notif.soft_delete(save=True)
        return True

    # -------------------------------------------------------------------------
    # MÉTODOS DE INTEGRACIÓN RÁPIDA POR EVENTO DE DOMINIO
    # -------------------------------------------------------------------------

    def notify_inventory_stock_low(
        self,
        product_name: str,
        current_stock: float,
        min_stock: float,
        company_id: int,
        origin_id: str = "",
    ):
        """Notificación de stock bajo."""
        idem = f"stock_low_{company_id}_{origin_id}_{timezone.now().strftime('%Y%m%d')}"
        return self.notify(
            title="Alerta de Stock Bajo",
            message=f"El producto '{product_name}' tiene existencias bajas ({current_stock} de {min_stock} mínimas).",
            category=NotificationCategory.INVENTORY,
            priority=NotificationPriority.WARNING,
            event_type=NotificationEventType.INVENTORY_STOCK_LOW,
            company_id=company_id,
            action_url="/inventario",
            origin_id=str(origin_id),
            metadata={"product_name": product_name, "current_stock": current_stock, "min_stock": min_stock},
            idempotency_key=idem,
            permission_code="inventory.view",
        )

    def notify_inventory_stock_exhausted(
        self,
        product_name: str,
        company_id: int,
        origin_id: str = "",
    ):
        """Notificación de stock agotado."""
        idem = f"stock_exhausted_{company_id}_{origin_id}_{timezone.now().strftime('%Y%m%d')}"
        return self.notify(
            title="¡Stock Agotado!",
            message=f"El producto '{product_name}' se ha quedado sin existencias.",
            category=NotificationCategory.INVENTORY,
            priority=NotificationPriority.CRITICAL,
            event_type=NotificationEventType.INVENTORY_STOCK_EXHAUSTED,
            company_id=company_id,
            action_url="/inventario",
            origin_id=str(origin_id),
            metadata={"product_name": product_name, "current_stock": 0},
            idempotency_key=idem,
            permission_code="inventory.view",
        )

    def notify_sale_completed(
        self,
        sale_number: str,
        total_amount: float,
        company_id: int,
        origin_id: str = "",
        exclude_user_id: Optional[int] = None,
    ):
        """Notificación de venta completada."""
        return self.notify(
            title="Nueva Venta Registrada",
            message=f"Se completó la venta #{sale_number} por un total de ${total_amount:,.2f}.",
            category=NotificationCategory.SALES,
            priority=NotificationPriority.SUCCESS,
            event_type=NotificationEventType.SALE_COMPLETED,
            company_id=company_id,
            action_url="/ventas",
            origin_id=str(origin_id),
            metadata={"sale_number": sale_number, "total": total_amount},
            idempotency_key=f"sale_completed_{company_id}_{origin_id}",
            permission_code="sales.view",
            exclude_user_ids=[exclude_user_id] if exclude_user_id else None,
        )

    def notify_sale_cancelled(
        self,
        sale_number: str,
        reason: str,
        company_id: int,
        origin_id: str = "",
        exclude_user_id: Optional[int] = None,
    ):
        """Notificación de venta anulada."""
        return self.notify(
            title="Venta Anulada",
            message=f"La venta #{sale_number} fue anulada. Motivo: {reason or 'No especificado'}.",
            category=NotificationCategory.SALES,
            priority=NotificationPriority.WARNING,
            event_type=NotificationEventType.SALE_CANCELLED,
            company_id=company_id,
            action_url="/ventas",
            origin_id=str(origin_id),
            metadata={"sale_number": sale_number, "reason": reason},
            idempotency_key=f"sale_cancelled_{company_id}_{origin_id}",
            permission_code="sales.view",
            exclude_user_ids=[exclude_user_id] if exclude_user_id else None,
        )

    def notify_purchase_registered(
        self,
        purchase_number: str,
        total_amount: float,
        supplier_name: str,
        company_id: int,
        origin_id: str = "",
        exclude_user_id: Optional[int] = None,
    ):
        """Notificación de compra registrada."""
        return self.notify(
            title="Compra Registrada",
            message=f"Se registró la compra #{purchase_number} a '{supplier_name}' por ${total_amount:,.2f}.",
            category=NotificationCategory.PURCHASES,
            priority=NotificationPriority.INFO,
            event_type=NotificationEventType.PURCHASE_REGISTERED,
            company_id=company_id,
            action_url="/compras",
            origin_id=str(origin_id),
            metadata={"purchase_number": purchase_number, "total": total_amount, "supplier": supplier_name},
            idempotency_key=f"purchase_registered_{company_id}_{origin_id}",
            permission_code="purchases.view",
            exclude_user_ids=[exclude_user_id] if exclude_user_id else None,
        )

    def notify_purchase_cancelled(
        self,
        purchase_number: str,
        reason: str,
        company_id: int,
        origin_id: str = "",
        exclude_user_id: Optional[int] = None,
    ):
        """Notificación de compra anulada."""
        return self.notify(
            title="Compra Anulada",
            message=f"La compra #{purchase_number} fue anulada. Motivo: {reason or 'No especificado'}.",
            category=NotificationCategory.PURCHASES,
            priority=NotificationPriority.WARNING,
            event_type=NotificationEventType.PURCHASE_CANCELLED,
            company_id=company_id,
            action_url="/compras",
            origin_id=str(origin_id),
            metadata={"purchase_number": purchase_number, "reason": reason},
            idempotency_key=f"purchase_cancelled_{company_id}_{origin_id}",
            permission_code="purchases.view",
            exclude_user_ids=[exclude_user_id] if exclude_user_id else None,
        )

    def notify_cash_session_opened(
        self,
        register_name: str,
        user_name: str,
        company_id: int,
        origin_id: str = "",
    ):
        """Notificación de apertura de caja."""
        return self.notify(
            title="Caja Abierta",
            message=f"El usuario {user_name} ha abierto el turno en '{register_name}'.",
            category=NotificationCategory.CASH,
            priority=NotificationPriority.INFO,
            event_type=NotificationEventType.CASH_SESSION_OPENED,
            company_id=company_id,
            action_url="/caja",
            origin_id=str(origin_id),
            metadata={"register": register_name, "user": user_name},
            permission_code="cash.view",
        )

    def notify_cash_session_closed_difference(
        self,
        register_name: str,
        difference: float,
        company_id: int,
        origin_id: str = "",
    ):
        """Notificación de cierre de caja con sobrante o faltante."""
        tipo = "sobrante" if difference > 0 else "faltante"
        return self.notify(
            title="Diferencia en Cierre de Caja",
            message=f"Se detectó un {tipo} de ${abs(difference):,.2f} al cerrar '{register_name}'.",
            category=NotificationCategory.CASH,
            priority=NotificationPriority.CRITICAL if abs(difference) > 100 else NotificationPriority.WARNING,
            event_type=NotificationEventType.CASH_SESSION_CLOSED_DIFFERENCE,
            company_id=company_id,
            action_url="/caja",
            origin_id=str(origin_id),
            metadata={"register": register_name, "difference": difference},
            idempotency_key=f"cash_closed_diff_{company_id}_{origin_id}",
            include_owners=True,
            permission_code="cash.manage",
        )

    def notify_user_created(
        self,
        username: str,
        company_id: int,
        origin_id: str = "",
    ):
        """Notificación de nuevo usuario incorporado a la empresa."""
        return self.notify(
            title="Nuevo Usuario Asignado",
            message=f"Se ha creado el usuario '{username}' en la organización.",
            category=NotificationCategory.SECURITY,
            priority=NotificationPriority.INFO,
            event_type=NotificationEventType.USER_CREATED,
            company_id=company_id,
            action_url="/usuarios",
            origin_id=str(origin_id),
            metadata={"username": username},
            include_owners=True,
            permission_code="users.view",
        )

    def notify_subscription_assigned(
        self,
        company_name: str,
        plan_name: str,
        company_id: int,
        origin_id: str = "",
    ):
        """Notificación de asignación de plan SaaS."""
        return self.notify(
            title="Plan Asignado Exitosamente",
            message=f"Se asignó el plan '{plan_name}' para la empresa '{company_name}'.",
            category=NotificationCategory.SUBSCRIPTION,
            priority=NotificationPriority.SUCCESS,
            event_type=NotificationEventType.SUBSCRIPTION_ASSIGNED,
            company_id=company_id,
            action_url="/saas-admin/suscripciones",
            origin_id=str(origin_id),
            metadata={"company_name": company_name, "plan_name": plan_name},
            include_owners=True,
            is_saas_admin=True,
        )

    def notify_subscription_renewed(
        self,
        company_name: str,
        plan_name: str,
        company_id: int,
        origin_id: str = "",
    ):
        """Notificación de renovación de suscripción."""
        return self.notify(
            title="Suscripción Renovada",
            message=f"La suscripción al plan '{plan_name}' de '{company_name}' ha sido renovada.",
            category=NotificationCategory.SUBSCRIPTION,
            priority=NotificationPriority.SUCCESS,
            event_type=NotificationEventType.SUBSCRIPTION_RENEWED,
            company_id=company_id,
            action_url="/saas-admin/suscripciones",
            origin_id=str(origin_id),
            metadata={"company_name": company_name, "plan_name": plan_name},
            include_owners=True,
            is_saas_admin=True,
        )

    def notify_version_published(
        self,
        version_name: str,
        version_number: str,
        is_critical: bool = False,
    ):
        """
        Notificación global de nueva versión del sistema para todos los usuarios activos.
        """
        try:
            active_users = User.objects.filter(is_active=True)
            prio = NotificationPriority.CRITICAL if is_critical else NotificationPriority.INFO
            title = f"Nueva Actualización P.M.E. v{version_number}"
            msg = f"Se ha publicado la versión {version_number}: '{version_name}'. Consulta las novedades del sistema."

            return self.notify(
                title=title,
                message=msg,
                category=NotificationCategory.SYSTEM,
                priority=prio,
                event_type=NotificationEventType.SOFTWARE_VERSION_PUBLISHED,
                company_id=None,  # Notificación global de plataforma
                recipients=active_users,
                action_url="/configuracion/versiones",
                origin_id=version_number,
                metadata={"version_number": version_number, "version_name": version_name},
                idempotency_key=f"version_published_{version_number}",
            )
        except Exception as e:
            logger.error("Error al notificar publicación de versión: %s", e)
            return []
