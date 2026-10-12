from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models.active_model import ActiveModel
from apps.cash.models.cash_session import CashSession
from apps.cash.models.payment import Payment


class CashMovement(ActiveModel):
    """
    Modelo que representa el impacto monetario dentro de una Sesión de Caja.
    Se asocia a un Payment en caso de ventas, o se crea manualmente (ingreso/egreso libre).
    """

    class MovementType(models.TextChoices):
        IN = "IN", "Ingreso"
        OUT = "OUT", "Egreso"

    id_cash_movement = models.BigAutoField(
        primary_key=True,
        verbose_name="ID",
    )

    cash_session = models.ForeignKey(
        CashSession,
        on_delete=models.PROTECT,
        related_name="movements",
        verbose_name="Sesión de Caja",
    )

    payment = models.ForeignKey(
        Payment,
        on_delete=models.PROTECT,
        related_name="cash_movements",
        null=True,
        blank=True,
        verbose_name="Pago Asociado",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name="Monto",
    )

    movement_type = models.CharField(
        max_length=10,
        choices=MovementType.choices,
        verbose_name="Tipo de Movimiento",
    )

    is_cash = models.BooleanField(
        default=True,
        verbose_name="Es Efectivo",
        help_text="Determina si este movimiento afecta el arqueo físico de caja (efectivo).",
    )

    reference = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Referencia",
    )

    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Descripción",
    )

    class Meta:
        db_table = "cash_movements"
        verbose_name = "Movimiento de Caja"
        verbose_name_plural = "Movimientos de Caja"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["cash_session"]),
            models.Index(fields=["movement_type"]),
            models.Index(fields=["is_cash"]),
            models.Index(fields=["cash_session", "created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=Decimal("0.00")),
                name="check_movement_amount_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"Movimiento {self.id_cash_movement} - {self.get_movement_type_display()} - ${self.amount}"
