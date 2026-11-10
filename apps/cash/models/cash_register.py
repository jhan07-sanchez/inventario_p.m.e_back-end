from django.db import models

from apps.core.models.tenant_model import TenantModel


class CashRegister(TenantModel):
    """
    Modelo que representa una caja registradora en el sistema.
    """

    id_cash_register = models.BigAutoField(
        primary_key=True,
        verbose_name="ID",
    )

    name = models.CharField(
        max_length=100,
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
        indexes = [
            models.Index(
                fields=["company", "is_active"],
                name="cash_reg_comp_act_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"],
                condition=models.Q(is_active=True),
                name="unique_cash_reg_per_company",
            ),
        ]

    def __str__(self) -> str:
        return self.name
