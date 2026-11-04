from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.enums import PaymentMethod
from apps.core.models.active_model import ActiveModel
from apps.finance.models.financial_account import FinancialAccount
from apps.finance.models.financial_category import FinancialCategory
from apps.finance.models.financial_transfer import FinancialTransfer


class FinancialMovement(ActiveModel):
    """
    Modelo que registra todo movimiento real o asiento operativo de entrada o salida de dinero
    sobre una cuenta financiera (Caja, Banco, Billetera Digital).
    """

    class MovementType(models.TextChoices):
        INFLOW = "INFLOW", "Ingreso"
        OUTFLOW = "OUTFLOW", "Egreso"

    class MovementStatus(models.TextChoices):
        PENDING = "PENDING", "Pendiente"
        COMPLETED = "COMPLETED", "Completado"
        CANCELLED = "CANCELLED", "Cancelado"
        REVERSED = "REVERSED", "Reversado"

    class OriginType(models.TextChoices):
        MANUAL = "MANUAL", "Manual"
        SALE = "SALE", "Venta"
        PURCHASE = "PURCHASE", "Pago a Proveedor / Compra"
        TRANSFER = "TRANSFER", "Transferencia Interna"
        ADJUSTMENT = "ADJUSTMENT", "Ajuste de Saldo / Conciliación"

    id_financial_movement = models.BigAutoField(
        primary_key=True,
        verbose_name="ID",
    )

    account = models.ForeignKey(
        FinancialAccount,
        on_delete=models.PROTECT,
        related_name="movements",
        verbose_name="Cuenta Financiera",
    )

    category = models.ForeignKey(
        FinancialCategory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movements",
        verbose_name="Categoría Financiera",
    )

    movement_type = models.CharField(
        max_length=10,
        choices=MovementType.choices,
        db_index=True,
        verbose_name="Tipo de Movimiento",
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name="Monto",
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.TRANSFER,
        verbose_name="Método de Pago",
    )

    status = models.CharField(
        max_length=20,
        choices=MovementStatus.choices,
        default=MovementStatus.COMPLETED,
        db_index=True,
        verbose_name="Estado",
    )

    movement_date = models.DateField(
        verbose_name="Fecha del Movimiento",
    )

    description = models.CharField(
        max_length=255,
        verbose_name="Concepto / Descripción",
    )

    reference = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Referencia / Nro. Comprobante",
    )

    origin_type = models.CharField(
        max_length=30,
        choices=OriginType.choices,
        default=OriginType.MANUAL,
        db_index=True,
        verbose_name="Tipo de Origen",
    )

    origin_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="ID del Documento de Origen",
        help_text="ID de la venta, compra u otro registro originador.",
    )

    transfer = models.ForeignKey(
        FinancialTransfer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movements",
        verbose_name="Transferencia Relacionada",
    )

    reversal_of = models.OneToOneField(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reversed_by",
        verbose_name="Movimiento Reversado",
        help_text="Referencia auditable al movimiento original que este movimiento anula o reversa.",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="financial_movements",
        verbose_name="Usuario Responsable",
    )

    notes = models.TextField(
        blank=True,
        default="",
        verbose_name="Notas Adicionales",
    )

    class Meta:
        db_table = "financial_movements"
        verbose_name = "Movimiento Financiero"
        verbose_name_plural = "Movimientos Financieros"
        ordering = ["-movement_date", "-created_at"]
        indexes = [
            models.Index(fields=["account", "movement_date"]),
            models.Index(fields=["movement_type", "status"]),
            models.Index(fields=["origin_type", "origin_id"]),
            models.Index(fields=["movement_date"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=Decimal("0.00")),
                name="check_financial_movement_amount_positive",
            ),
        ]

    def __str__(self) -> str:
        sign = "+" if self.movement_type == self.MovementType.INFLOW else "-"
        return (
            f"Movimiento #{self.id_financial_movement}: {self.account.name} "
            f"[{sign}${self.amount:,.2f}] - {self.description}"
        )

