from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models.base_model import BaseModel
from apps.purchases.models.purchase import Purchase


class PurchaseDetail(BaseModel):
    """
    Modelo que representa el detalle (línea) de una orden de compra.
    """

    id_purchase_detail = models.BigAutoField(primary_key=True, verbose_name="ID")

    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.CASCADE,
        related_name="details",
        verbose_name="Compra",
    )

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="purchase_details",
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

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Subtotal",
    )

    class Meta:
        db_table = "purchase_details"
        verbose_name = "Detalle de Compra"
        verbose_name_plural = "Detalles de Compra"
        ordering = ["id_purchase_detail"]

        indexes = [
            models.Index(fields=["purchase"], name="purchase_detail_purch_idx"),
            models.Index(fields=["product"], name="purchase_detail_prod_idx"),
        ]

    def __str__(self) -> str:
        return f"Detalle #{self.id_purchase_detail} - Compra #{self.purchase_id} - Producto {self.product.code}"
