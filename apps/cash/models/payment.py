from decimal import Decimal

from django.db import models

from apps.core.models.active_model import ActiveModel
from apps.sales.models.sale import Sale


class Payment(ActiveModel):
    """
    Modelo que representa el pago real de una transacción.
    Permite pagos divididos (varios Payments por Sale) y diferentes métodos de pago.
    """

    class PaymentMethod(models.TextChoices):
        CASH = "CASH", "Efectivo"
        CARD = "CARD", "Tarjeta"
        TRANSFER = "TRANSFER", "Transferencia"
        CREDIT = "CREDIT", "Crédito"
        OTHER = "OTHER", "Otro"

    class PaymentStatus(models.TextChoices):
        COMPLETED = "COMPLETED", "Completado"
        CANCELLED = "CANCELLED", "Cancelado"
        REFUNDED = "REFUNDED", "Reembolsado"

    id_payment = models.BigAutoField(
        primary_key=True,
        verbose_name="ID",
    )

    sale = models.ForeignKey(
        Sale,
        on_delete=models.PROTECT,
        related_name="payments",
        null=True,
        blank=True,
        verbose_name="Venta Asociada",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Monto",
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
        verbose_name="Método de Pago",
    )

    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.COMPLETED,
        db_index=True,
        verbose_name="Estado",
    )

    reference = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Referencia/Voucher",
        help_text="Nro. de transacción, voucher de tarjeta, etc.",
    )

    notes = models.TextField(
        blank=True,
        default="",
        verbose_name="Notas",
    )

    class Meta:
        db_table = "payments"
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["sale"]),
            models.Index(fields=["payment_method"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"Pago {self.id_payment} - {self.get_payment_method_display()} - ${self.amount}"
