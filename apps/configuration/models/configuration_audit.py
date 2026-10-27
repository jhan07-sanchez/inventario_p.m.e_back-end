from django.conf import settings
from django.db import models

from apps.configuration.models.global_parameter import GlobalParameter
from apps.core.models.active_model import ActiveModel


class ConfigurationAudit(ActiveModel):
    """
    Modelo para auditar los cambios de negocio en la configuracion.
    Guarda el valor anterior y el nuevo valor para trazabilidad.
    """

    class Action(models.TextChoices):
        CREATE = "CREATE", "Creación"
        UPDATE = "UPDATE", "Actualización"
        DEACTIVATE = "DEACTIVATE", "Desactivación"
        RESTORE = "RESTORE", "Restauración"

    parameter = models.ForeignKey(
        GlobalParameter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audits",
        verbose_name="Parametro Modificado",
    )
    parameter_key = models.CharField(
        max_length=100,
        verbose_name="Clave del Parametro",
        help_text="Se guarda la clave si el parametro es eliminado fisicamente en el futuro.",
    )
    action = models.CharField(
        max_length=20,
        choices=Action.choices,
        default=Action.UPDATE,
        verbose_name="Accion Realizada",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="configuration_audits",
        verbose_name="Usuario que realizo el cambio",
    )
    old_value = models.TextField(
        blank=True,
        null=True,
        verbose_name="Valor Anterior",
        help_text="Valor del parametro antes del cambio.",
    )
    new_value = models.TextField(
        blank=True,
        null=True,
        verbose_name="Valor Nuevo",
        help_text="Valor del parametro despues del cambio.",
    )
    reason = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Motivo del Cambio",
        help_text="Opcional: por que se realizo este cambio.",
    )

    class Meta:
        db_table = "configuration_audits"
        verbose_name = "Auditoria de Configuracion"
        verbose_name_plural = "Auditorias de Configuracion"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return (
            f"{self.action} - {self.parameter_key} por {self.user} el {self.created_at}"
        )
