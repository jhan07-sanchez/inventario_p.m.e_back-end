from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models.active_model import ActiveModel
from apps.products.models.product import Product


class SaleDetail(ActiveModel):
    """
    Modelo que representa un producto dentro de una venta.

    Conserva el precio utilizado en el momento de la venta para
    mantener la integridad histórica de las operaciones comerciales.
    """

    id_sale_detail = models.BigAutoField(
        primary_key=True,
        verbose_name="ID",
    )

    sale = models.ForeignKey(
        "sales.Sale",
        on_delete=models.CASCADE,
        related_name="details",
        verbose_name="Venta",
        help_text="Venta a la que pertenece el detalle.",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="sale_details",
        verbose_name="Producto",
        help_text="Producto incluido en la venta.",
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01")),
        ],
        verbose_name="Cantidad",
        help_text="Cantidad de unidades vendidas.",
    )

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
        verbose_name="Precio unitario",
        help_text="Precio del producto al momento de la venta.",
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

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
        verbose_name="Subtotal",
    )

    class Meta:
        db_table = "sale_details"
        verbose_name = "Detalle de venta"
        verbose_name_plural = "Detalles de venta"
        ordering = ["id_sale_detail"]

        indexes = [
            models.Index(
                fields=["sale"],
                name="sale_detail_sale_idx",
            ),
            models.Index(
                fields=["product"],
                name="sale_detail_product_idx",
            ),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["sale", "product"],
                name="sale_detail_unique_product",
            ),
        ]

    def __str__(self) -> str:
        """Retorna una representación legible del detalle."""
        return f"{self.sale.sale_number} - {self.product.code}"
