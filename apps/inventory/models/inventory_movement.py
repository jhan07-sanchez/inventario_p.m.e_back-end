from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models.active_model import ActiveModel
from apps.inventory.models.inventory import Inventory


class InventoryMovement(ActiveModel):
    """
    Modelo que representa un movimiento en el inventario (Kardex).
    Permite registrar la trazabilidad de entradas, salidas y ajustes.
    """

    class MovementType(models.TextChoices):
        """
        Tipos de movimientos permitidos.
        """
        ENTRY = "ENTRY", "Entrada"
        EXIT = "EXIT", "Salida"
        ADJUSTMENT = "ADJUSTMENT", "Ajuste"

    id_movement = models.AutoField(primary_key=True, verbose_name="ID")
    inventory = models.ForeignKey(
        Inventory,
        on_delete=models.PROTECT,
        related_name="movements",
        verbose_name="Inventario",
    )
    movement_type = models.CharField(
        max_length=20,
        choices=MovementType.choices,
        verbose_name="Tipo de movimiento",
    )
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Cantidad",
        help_text="Cantidad del movimiento, siempre en valor positivo.",
    )
    previous_stock = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Stock anterior",
    )
    new_stock = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Stock nuevo",
    )
    reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Referencia",
        help_text="Ej. Número de factura, documento de ajuste.",
    )
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notas u observaciones",
    )
    supplier = models.ForeignKey(
        "suppliers.Supplier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_movements",
        verbose_name="Proveedor",
        help_text="Proveedor asociado al movimiento (ej. para compras o entradas).",
    )

    class Meta:
        db_table = "inventory_movements"
        verbose_name = "Movimiento de Inventario"
        verbose_name_plural = "Movimientos de Inventario"
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["inventory", "movement_type"],
                name="inv_mov_inv_type_idx",
            ),
            models.Index(
                fields=["created_at"],
                name="inv_mov_created_at_idx",
            ),
        ]

    def __str__(self) -> str:
        """Retorna una representación legible del movimiento."""
        return f"{self.get_movement_type_display()} - {self.inventory.product.code} ({self.quantity})"
