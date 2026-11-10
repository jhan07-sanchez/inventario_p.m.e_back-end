from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models.active_model import ActiveModel
from apps.subscriptions.models.subscription import Subscription


class SubscriptionPayment(ActiveModel):
    """
    Registro contable de pagos y transacciones vinculadas a una suscripción SaaS.
    """

    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", "Pendiente"
        APPROVED = "APPROVED", "Aprobado"
        REJECTED = "REJECTED", "Rechazado"

    id_payment = models.BigAutoField(
        primary_key=True,
        verbose_name="ID",
    )

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name="Suscripción",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name="Monto Abonado",
    )

    payment_method = models.CharField(
        max_length=50,
        default="CREDIT_CARD",
        verbose_name="Método de Pago",
        help_text="Tarjeta de Crédito, Transferencia Bancaria, Pasarela Online, etc.",
    )

    transaction_reference = models.CharField(
        max_length=150,
        blank=True,
        default="",
        verbose_name="Referencia de Transacción",
        help_text="ID retornado por la pasarela de pagos externa.",
    )

    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
        verbose_name="Estado del Pago",
    )

    payment_date = models.DateTimeField(
        default=timezone.now,
        verbose_name="Fecha de Pago",
    )

    invoice_url = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="URL Comprobante Fiscal",
    )

    notes = models.TextField(
        blank=True,
        default="",
        verbose_name="Observaciones",
    )

    class Meta:
        db_table = "subscription_payments"
        verbose_name = "Pago de Suscripción"
        verbose_name_plural = "Pagos de Suscripciones"
        ordering = ["-payment_date"]
        indexes = [
            models.Index(fields=["subscription", "status"], name="sub_pay_sub_stat_idx"),
            models.Index(fields=["status", "payment_date"], name="sub_pay_stat_date_idx"),
        ]

    def __str__(self) -> str:
        return f"Pago #{self.id_payment} - ${self.amount} ({self.get_status_display()})"

