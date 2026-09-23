from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models.active_model import ActiveModel
from apps.customers.models.customer import Customer


class Sale(ActiveModel):
    """
    Modelo que representa una venta en el sistema.

    Contiene la información general de la operación comercial.
    Los productos vendidos se almacenan mediante SaleDetail.
    """

    class SaleStatus(models.TextChoices):
        """
        Estados disponibles para una venta.
        """

        PENDING = "PENDING", "Pendiente"
        COMPLETED = "COMPLETED", "Completada"
        CANCELLED = "CANCELLED", "Cancelada"

    class PaymentMethod(models.TextChoices):
        """
        Métodos de pago disponibles para una venta.
        """

        CASH = "CASH", "Efectivo"
        CARD = "CARD", "Tarjeta"
        TRANSFER = "TRANSFER", "Transferencia"
        CREDIT = "CREDIT", "Crédito"
        OTHER = "OTHER", "Otro"

    id_sale = models.BigAutoField(
        primary_key=True,
        verbose_name="ID",
    )

    sale_number = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
        verbose_name="Número de venta",
        help_text="Número único que identifica la venta.",
    )

    class SaleType(models.TextChoices):
        """
        Tipo de venta: flujo administrativo (dos pasos) o POS (quick_sale).
        """

        ADMIN = "ADMIN", "Administrativa"
        POS = "POS", "Punto de Venta"

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="sales",
        null=True,
        blank=True,
        verbose_name="Cliente",
        help_text=(
            "Cliente asociado a la venta. "
            "NULL indica venta a Consumidor Final (POS)."
        ),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sales",
        verbose_name="Usuario",
        help_text="Usuario que registra la venta.",
    )

    sale_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de venta",
    )

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
        verbose_name="Subtotal",
    )

    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
        verbose_name="Descuento",
    )

    tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
        verbose_name="Impuesto",
    )

    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
        verbose_name="Total",
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
        verbose_name="Método de pago",
    )

    status = models.CharField(
        max_length=20,
        choices=SaleStatus.choices,
        default=SaleStatus.PENDING,
        db_index=True,
        verbose_name="Estado",
    )

    sale_type = models.CharField(
        max_length=10,
        choices=SaleType.choices,
        default=SaleType.ADMIN,
        db_index=True,
        verbose_name="Tipo de venta",
        help_text="ADMIN: flujo dos pasos. POS: venta rápida desde caja.",
    )

    amount_received = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
        verbose_name="Monto recibido",
        help_text="Efectivo recibido del cliente (POS efectivo).",
    )

    change_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
        verbose_name="Cambio",
        help_text="Vuelto/cambio entregado al cliente (POS efectivo).",
    )

    notes = models.TextField(
        blank=True,
        default="",
        verbose_name="Notas",
    )

    class Meta:
        db_table = "sales"
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["status"],
                name="sale_status_idx",
            ),
            models.Index(
                fields=["customer"],
                name="sale_customer_idx",
            ),
            models.Index(
                fields=["user"],
                name="sale_user_idx",
            ),
            models.Index(
                fields=["sale_date"],
                name="sale_date_idx",
            ),
            models.Index(
                fields=["created_at"],
                name="sale_created_at_idx",
            ),
        ]

    def __str__(self) -> str:
        """Retorna una representación legible de la venta."""
        return self.sale_number
