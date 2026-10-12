from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models.active_model import ActiveModel
from apps.cash.models.cash_register import CashRegister


class CashSession(ActiveModel):
    """
    Modelo que representa el turno o sesión de trabajo de un cajero.
    Controla el balance de efectivo (esperado y físico).
    """

    class SessionStatus(models.TextChoices):
        OPEN = "OPEN", "Abierta"
        CLOSED = "CLOSED", "Cerrada"

    id_cash_session = models.BigAutoField(
        primary_key=True,
        verbose_name="ID",
    )

    cash_register = models.ForeignKey(
        CashRegister,
        on_delete=models.PROTECT,
        related_name="sessions",
        verbose_name="Caja",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cash_sessions",
        verbose_name="Usuario",
        help_text="Cajero responsable de la sesión.",
    )

    start_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha/Hora de Apertura",
    )

    end_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha/Hora de Cierre",
    )

    opening_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Efectivo Inicial",
    )

    expected_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Efectivo Esperado",
        help_text="Calculado solo en base a movimientos de efectivo (CASH).",
    )

    counted_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Efectivo Contado",
        help_text="Monto físico declarado en el cierre de caja.",
    )

    difference = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Diferencia",
        help_text="Diferencia entre el esperado y el contado.",
    )

    status = models.CharField(
        max_length=20,
        choices=SessionStatus.choices,
        default=SessionStatus.OPEN,
        db_index=True,
        verbose_name="Estado",
    )

    notes = models.TextField(
        blank=True,
        default="",
        verbose_name="Notas",
    )

    class Meta:
        db_table = "cash_sessions"
        verbose_name = "Sesión de Caja"
        verbose_name_plural = "Sesiones de Caja"
        ordering = ["-start_time"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["cash_register", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(status="OPEN", is_active=True),
                name="unique_open_session_per_user",
            ),
            models.UniqueConstraint(
                fields=["cash_register"],
                condition=models.Q(status="OPEN", is_active=True),
                name="unique_open_session_per_register",
            ),
            models.CheckConstraint(
                condition=models.Q(opening_balance__gte=Decimal("0.00")),
                name="check_opening_balance_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"Sesión {self.id_cash_session} - {self.cash_register.name}"
