from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models.active_model import ActiveModel
from apps.notifications.enums import NotificationCategory, NotificationPriority


class Notification(ActiveModel):
    """
    Modelo representativo de una notificación individual dirigida a un usuario receptor.
    Soporta tenencia multiempresa (con company opcional para eventos globales de SaaS Admin),
    priorización, categorización por módulo, enlaces de acción profunda (action_url),
    metadatos estructurados en JSON y claves de idempotencia para prevención de duplicados.
    """

    id_notification = models.BigAutoField(
        primary_key=True,
        verbose_name="ID Notificación",
    )

    company = models.ForeignKey(
        "company_info.CompanyInfo",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name="Empresa / Tenant",
        help_text="Tenant al que pertenece la notificación. Nulo para notificaciones globales de SaaS Admin.",
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="Usuario Destinatario",
        help_text="Usuario específico que recibe esta notificación.",
    )

    title = models.CharField(
        max_length=200,
        verbose_name="Título",
        help_text="Título conciso y descriptivo del evento.",
    )

    message = models.TextField(
        verbose_name="Mensaje",
        help_text="Cuerpo o contenido detallado de la notificación.",
    )

    category = models.CharField(
        max_length=50,
        choices=NotificationCategory.choices,
        default=NotificationCategory.SYSTEM,
        db_index=True,
        verbose_name="Categoría de Módulo",
    )

    priority = models.CharField(
        max_length=20,
        choices=NotificationPriority.choices,
        default=NotificationPriority.INFO,
        db_index=True,
        verbose_name="Prioridad / Severidad",
    )

    event_type = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name="Tipo de Evento",
        help_text="Identificador único del evento en el catálogo (ej. INVENTORY.STOCK_LOW).",
    )

    action_url = models.CharField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="URL de Acción",
        help_text="Ruta relativa o enlace dentro de la interfaz para navegación directa.",
    )

    origin_id = models.CharField(
        max_length=100,
        blank=True,
        default="",
        db_index=True,
        verbose_name="ID de Origen",
        help_text="Identificador de la entidad de negocio origen (ej. ID de Venta, Compra, etc.).",
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Metadatos Adicionales",
        help_text="Carga estructurada con detalles específicos del evento.",
    )

    is_read = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Leída",
        help_text="Indica si el usuario destinatario ya visualizó o marcó como leída la notificación.",
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Lectura",
        help_text="Timestamp exacto en que la notificación fue leída.",
    )

    idempotency_key = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Clave de Idempotencia",
        help_text="Hash o identificador único para evitar disparos duplicados del mismo evento.",
    )

    class Meta:
        db_table = "notifications"
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["recipient", "is_read", "-created_at"],
                name="idx_notif_recip_read_created",
            ),
            models.Index(
                fields=["company", "recipient", "-created_at"],
                name="idx_notif_comp_recip_created",
            ),
            models.Index(
                fields=["recipient", "idempotency_key"],
                name="idx_notif_recip_idem",
            ),
            models.Index(
                fields=["category", "priority"],
                name="idx_notif_cat_prio",
            ),
        ]

    def __str__(self):
        return f"[{self.category}] {self.title} -> {self.recipient_id} ({'Leída' if self.is_read else 'No leída'})"

    def mark_as_read(self, save: bool = True) -> None:
        """
        Marca la notificación como leída y registra la fecha de lectura.
        """
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            if save:
                self.save(update_fields=["is_read", "read_at", "updated_at"])

    def mark_as_unread(self, save: bool = True) -> None:
        """
        Devuelve la notificación al estado no leída.
        """
        if self.is_read:
            self.is_read = False
            self.read_at = None
            if save:
                self.save(update_fields=["is_read", "read_at", "updated_at"])
