from django.conf import settings
from django.db import models

from apps.core.models.base_model import BaseModel


class AuditLog(BaseModel):
    """
    Modelo para registrar las acciones realizadas por los usuarios
    (Auditoría / Audit Trail).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        help_text="Usuario que realizó la acción. Nulo si fue un usuario anónimo.",
    )
    method = models.CharField(
        max_length=10,
        help_text="Método HTTP utilizado (ej. POST, PUT, DELETE).",
    )
    path = models.CharField(
        max_length=255,
        help_text="Ruta del endpoint consumido.",
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Dirección IP del cliente.",
    )
    user_agent = models.TextField(
        null=True,
        blank=True,
        help_text="User-Agent del cliente (navegador, herramienta, etc).",
    )
    status_code = models.IntegerField(
        help_text="Código de estado HTTP retornado.",
    )
    payload = models.JSONField(
        null=True,
        blank=True,
        help_text="Cuerpo de la petición (ocultando datos sensibles).",
    )

    class Meta:
        verbose_name = "Registro de Auditoría"
        verbose_name_plural = "Registros de Auditoría"
        ordering = ["-created_at"]
        db_table = "inventario-pme_audit_logs"

    def __str__(self):
        return f"[{self.method}] {self.path} - {self.status_code} ({self.created_at.strftime('%Y-%m-%d %H:%M:%S')})"
