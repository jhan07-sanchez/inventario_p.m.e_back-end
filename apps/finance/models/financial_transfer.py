from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models.active_model import ActiveModel
from apps.finance.models.financial_account import FinancialAccount


class FinancialTransfer(ActiveModel):
    """
    Modelo que representa una transferencia entre dos cuentas financieras propias
    (ej: de Caja General a Banco, o entre dos cuentas bancarias de la empresa).

    Propiedades innegociables:
    - Es neutra para el estado de resultados: no es ni ingreso operativo ni gasto.
    - No duplica fondos ni incrementa artificialmente el dinero global de la empresa.
    - Se procesa en una transacción atómica estricta que genera o actualiza los movimientos vinculados.
    """

    class TransferStatus(models.TextChoices):
        COMPLETED = "COMPLETED", "Completada"
        CANCELLED = "CANCELLED", "Cancelada"

    id_financial_transfer = models.BigAutoField(
        primary_key=True,
        verbose_name="ID",
    )

    source_account = models.ForeignKey(
        FinancialAccount,
        on_delete=models.PROTECT,
        related_name="transfers_sent",
        verbose_name="Cuenta de Origen",
    )

    destination_account = models.ForeignKey(
        FinancialAccount,
        on_delete=models.PROTECT,
        related_name="transfers_received",
        verbose_name="Cuenta de Destino",
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name="Monto Transferido",
    )

    transfer_date = models.DateField(
        verbose_name="Fecha de Transferencia",
    )

    reference = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Referencia / Nro. Comprobante Bancario",
    )

    notes = models.TextField(
        blank=True,
        default="",
        verbose_name="Notas / Justificación",
    )

    status = models.CharField(
        max_length=20,
        choices=TransferStatus.choices,
        default=TransferStatus.COMPLETED,
        db_index=True,
        verbose_name="Estado de la Transferencia",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="financial_transfers",
        verbose_name="Usuario Responsable",
    )

    class Meta:
        db_table = "financial_transfers"
        verbose_name = "Transferencia Financiera"
        verbose_name_plural = "Transferencias Financieras"
        ordering = ["-transfer_date", "-created_at"]
        indexes = [
            models.Index(fields=["source_account"]),
            models.Index(fields=["destination_account"]),
            models.Index(fields=["transfer_date"]),
            models.Index(fields=["status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(source_account=models.F("destination_account")),
                name="check_transfer_different_accounts",
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gt=Decimal("0.00")),
                name="check_transfer_amount_positive",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Transferencia #{self.id_financial_transfer}: "
            f"{self.source_account.name} -> {self.destination_account.name} "
            f"(${self.amount:,.2f})"
        )

