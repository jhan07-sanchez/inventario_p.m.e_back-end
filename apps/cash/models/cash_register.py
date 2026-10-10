from django.db import models

from apps.core.models.active_model import ActiveModel


class CashRegister(ActiveModel):
    """
    Modelo que representa una caja registradora en el sistema.
    """

    id_cash_register = models.BigAutoField(
        primary_key=True,
        verbose_name="ID",
    )

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nombre de Caja",
        help_text="Ej: Caja Principal, Caja POS 1",
    )

    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Descripción",
    )

    class Meta:
        db_table = "cash_registers"
        verbose_name = "Caja"
        verbose_name_plural = "Cajas"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
