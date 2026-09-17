from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models.base_model import BaseModel
from apps.invoices.models.invoice import Invoice


class InvoiceItem(BaseModel):
    """
    Modelo que representa una línea de detalle dentro de una factura.
    """

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Factura",
    )
    
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="invoice_items",
        verbose_name="Producto",
    )
    
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name="Cantidad",
    )
    
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Precio unitario",
    )
    
    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Descuento",
    )
    
    tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Impuestos",
    )
    
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Subtotal (Línea)",
    )

    class Meta:
        db_table = "invoice_items"
        verbose_name = "Ítem de Factura"
        verbose_name_plural = "Ítems de Factura"
        ordering = ["id"]

        indexes = [
            models.Index(fields=["invoice"], name="invoice_item_inv_idx"),
            models.Index(fields=["product"], name="invoice_item_prod_idx"),
        ]

    def __str__(self) -> str:
        return f"Ítem {self.id} - Factura {self.invoice.invoice_number}"
