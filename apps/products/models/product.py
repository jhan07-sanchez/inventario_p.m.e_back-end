from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models.base_model import BaseModel
from apps.categories.models.category import Category



class Product(BaseModel):
    """
    Modelo que representa un producto en el sistema.
    """
    class unit(models.TextChoices):
        """
        Unidadesd de medida disponibles para los productos.
        """
        UNIT = "UNIT", "Unidad"
        BOX = "BOX", "Caja"
        PACKAGE = "PACKAGE", "Paquete"
        KILOGRAM = "KG", "Kilogramo"
        GRAM = "G", "Gramo"
        METER = "M", "Metro"
        LETER = "L", "Litro"
        GALLON = "GAL", "Galón"
        ROLL = "ROLL", "Rollo"
        PAIR = "PAIR", "Par"

    id_product = models.AutoField(primary_key=True, verbose_name="ID")
    code = models.CharField(max_length=50, unique=True, db_index=True, verbose_name="Código del producto")
    barcode = models.CharField(max_length=50, unique=True, null=True, blank=True, db_index=True, verbose_name="Código de barras")
    name = models.CharField(max_length=150, unique=True, db_index=True, verbose_name="Nombre del producto")
    description = models.TextField(blank=True, null=True, default="", verbose_name="Descripción del producto")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products", verbose_name="Categoría")
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
    stock = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))], verbose_name="Cantidad en stock")
    minimum_stock = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))], verbose_name="Stock mínimo")
    maximum_stock = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))], verbose_name="Stock máximo")
    unit = models.CharField(max_length=20, choices=unit.choices, default=unit.UNIT, verbose_name="Unidad de medida")
    is_active = models.BooleanField(default=True, db_index=True, verbose_name="Activo")

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
            models.Index(
                fields=["is_active", "stock"],
                name="product_active_stock_idx",
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
                name="product_max_stock_gte_min_stock",
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

    @property
    def is_low_stock(self) -> bool:
        """Indica si el producto se encuentra por debajo del stock mínimo."""

        return self.stock <= self.minimum_stock

    @property
    def is_overstocked(self) -> bool:
        """Indica si el producto supera el stock máximo configurado."""

        if self.maximum_stock is None:
            return False

        return self.stock > self.maximum_stock
