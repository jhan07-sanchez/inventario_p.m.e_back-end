from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models.active_model import ActiveModel
from apps.products.models import Product


class Inventory(ActiveModel):
    """
    Modelo que representa el control de existencias de un producto en el sistema.
    """

    id_inventory = models.AutoField(primary_key=True, verbose_name="ID")
    product = models.OneToOneField(
        Product,
        on_delete=models.PROTECT,
        related_name="inventory",
        verbose_name="Producto",
    )
    current_stock = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Stock actual",
    )
    minimum_stock = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Stock mínimo",
    )
    maximum_stock = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Stock máximo",
    )

    class Meta:
        db_table = "inventory"
        verbose_name = "Inventario"
        verbose_name_plural = "Inventarios"
        ordering = ["product__name"]

        indexes = [
            models.Index(
                fields=["current_stock"],
                name="inventory_current_stock_idx",
            ),
            models.Index(
                fields=["minimum_stock"],
                name="inventory_min_stock_idx",
            ),
            models.Index(
                fields=["is_active", "current_stock"],
                name="inventory_active_stock_idx",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    maximum_stock__isnull=True,
                )
                | models.Q(
                    maximum_stock__gte=models.F("minimum_stock"),
                ),
                name="inventory_max_stock_gte_min_stock",
            ),
        ]

    def __str__(self) -> str:
        """Retorna una representación legible del inventario."""
        return f"{self.product.code} - {self.product.name}"

    @property
    def is_low_stock(self) -> bool:
        """Indica si el inventario se encuentra por debajo del stock mínimo."""
        return self.current_stock <= self.minimum_stock

    @property
    def is_overstocked(self) -> bool:
        """Indica si el inventario supera el stock máximo configurado."""
        if self.maximum_stock is None:
            return False
        return self.current_stock > self.maximum_stock
