from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models.active_model import ActiveModel
from apps.categories.models.category import Category


class Product(ActiveModel):
    """
    Modelo que representa un producto en el sistema (Solo catálogo).
    """

    class Unit(models.TextChoices):
        """
        Unidades de medida disponibles para los productos.
        """

        UNIT = "UNIT", "Unidad"
        BOX = "BOX", "Caja"
        PACKAGE = "PACKAGE", "Paquete"
        KILOGRAM = "KG", "Kilogramo"
        GRAM = "G", "Gramo"
        METER = "M", "Metro"
        LITER = "L", "Litro"
        GALLON = "GAL", "Galón"
        ROLL = "ROLL", "Rollo"
        PAIR = "PAIR", "Par"

    id_product = models.AutoField(primary_key=True, verbose_name="ID")
    code = models.CharField(
        max_length=50, unique=True, db_index=True, verbose_name="Código del producto"
    )
    barcode = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Código de barras",
    )
    name = models.CharField(
        max_length=150, unique=True, db_index=True, verbose_name="Nombre del producto"
    )
    description = models.TextField(
        blank=True, null=True, default="", verbose_name="Descripción del producto"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="Categoría",
    )
    purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Precio de compra",
    )
    sale_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Precio del producto",
    )
    unit = models.CharField(
        max_length=20,
        choices=Unit.choices,
        default=Unit.UNIT,
        verbose_name="Unidad de medida",
    )

    class Meta:
        db_table = "products"
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ["name"]

        indexes = [
            models.Index(
                fields=["name"],
                name="product_name_idx",
            ),
            models.Index(
                fields=["category", "is_active"],
                name="product_category_active_idx",
            ),
        ]

    def __str__(self) -> str:
        """Retorna una representación legible del producto."""
        return f"{self.code} - {self.name}"

    @property
    def profit_amount(self) -> Decimal:
        """Calcula el valor absoluto de la ganancia por unidad."""
        return self.sale_price - self.purchase_price

    @property
    def profit_margin_percentage(self) -> Decimal:
        """Calcula el margen de ganancia porcentual."""
        if self.purchase_price == Decimal("0.00"):
            return Decimal("0.00")

        return (
            (self.sale_price - self.purchase_price) / self.purchase_price
        ) * Decimal("100")
