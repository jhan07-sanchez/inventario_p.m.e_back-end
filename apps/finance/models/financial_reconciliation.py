from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.core.models.active_model import ActiveModel
from apps.finance.models.financial_account import FinancialAccount


class FinancialReconciliation(ActiveModel):
    """
    Representa una conciliación de saldo entre el extracto bancario (o conteo físico)
    y el saldo registrado en libros en el sistema.
    """

    class ReconciliationStatus(models.TextChoices):
        DRAFT = "DRAFT", "Borrador"
        RECONCILED = "RECONCILED", "Conciliado"

    id_reconciliation = models.BigAutoField(
        primary_key=True,
        verbose_name="ID",
    )

    account = models.ForeignKey(
        FinancialAccount,
        on_delete=models.PROTECT,
        related_name="reconciliations",
        verbose_name="Cuenta Financiera",
    )

    start_date = models.DateField(
        verbose_name="Fecha de Inicio del Período",
    )

    end_date = models.DateField(
        verbose_name="Fecha de Corte",
    )

    statement_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="Saldo según Extracto Bancario / Físico",
        help_text="Saldo final informado por el extracto bancario o conteo.",
    )

    book_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="Saldo en Libros (Sistema)",
        help_text="Saldo calculado por el sistema a la fecha de corte.",
    )

    difference = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Diferencia (Extracto - Libros)",
    )

    status = models.CharField(
        max_length=20,
        choices=ReconciliationStatus.choices,
        default=ReconciliationStatus.DRAFT,
        db_index=True,
        verbose_name="Estado de la Conciliación",
    )

    reconciled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha y Hora de Cierre de Conciliación",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="financial_reconciliations",
        verbose_name="Usuario Auditor",
    )

    notes = models.TextField(
        blank=True,
        default="",
        verbose_name="Observaciones / Justificación de Diferencias",
    )

    class Meta:
        db_table = "financial_reconciliations"
        verbose_name = "Conciliación Financiera"
        verbose_name_plural = "Conciliaciones Financieras"
        ordering = ["-end_date", "-created_at"]
        indexes = [
            models.Index(fields=["account", "end_date"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return (
            f"Conciliación #{self.id_reconciliation} - {self.account.name} "
            f"[{self.end_date}] (Dif: ${self.difference:,.2f})"
        )

