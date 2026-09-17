from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models.active_model import ActiveModel


class Purchase(ActiveModel):
    """
    Modelo que representa una orden de compra o ingreso de mercancía de un proveedor.
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Borrador"
        PENDING = "PENDING", "Pendiente"
        RECEIVED = "RECEIVED", "Recibida"
        COMPLETED = "COMPLETED", "Completada"
        CANCELLED = "CANCELLED", "Cancelada"

    id_purchase = models.BigAutoField(primary_key=True, verbose_name="ID")

    supplier = models.ForeignKey(
        "suppliers.Supplier",
        on_delete=models.PROTECT,
        related_name="purchases",
        verbose_name="Proveedor",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Estado de la compra",
    )

    issue_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de emisión",
    )

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Subtotal",
    )

    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Total",
    )

    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observaciones",
    )

    class Meta:
        db_table = "purchases"
        verbose_name = "Compra"
        verbose_name_plural = "Compras"
        ordering = ["-created_at"]

        indexes = [
            models.Index(fields=["status"], name="purchase_status_idx"),
            models.Index(fields=["issue_date"], name="purchase_issue_date_idx"),
            models.Index(fields=["supplier", "status"], name="purchase_supp_status_idx"),
        ]

    def __str__(self) -> str:
        return f"Compra #{self.id_purchase} - {self.supplier.business_name or self.supplier.document_number}"
