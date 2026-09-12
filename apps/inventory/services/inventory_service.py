from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.core.services.base_service import BaseService
from apps.inventory.models import Inventory
from apps.inventory.models.inventory_movement import InventoryMovement


class InventoryService(BaseService[Inventory]):
    """
    Servicio encargado de la lógica de negocio del inventario.

    Centraliza la creación del inventario, actualización de
    configuraciones de stock y movimientos de existencias.
    """

    def __init__(self):
        super().__init__(Inventory)

    @staticmethod
    def create_inventory(data: dict) -> Inventory:
        """
        Crea el registro de inventario de un producto.
        """

        product = data.get("product")

        if product is None:
            raise ValidationError("El producto es obligatorio.")

        if Inventory.objects.filter(product=product).exists():
            raise ValidationError("El producto ya tiene un registro de inventario.")

        return InventoryService().create(**data)

    @staticmethod
    def update_inventory(
        inventory: Inventory,
        data: dict,
    ) -> Inventory:
        """
        Actualiza la configuración del inventario.

        El stock actual no se modifica mediante este método.
        """

        data.pop("current_stock", None)

        return InventoryService().update(
            inventory,
            **data,
        )

    @staticmethod
    @transaction.atomic
    def increase_stock(
        id_inventory: int,
        quantity: Decimal,
        reference: str | None = None,
        notes: str | None = None,
    ) -> Inventory:
        """
        Incrementa el stock y registra un movimiento de entrada.
        """

        if quantity <= Decimal("0.00"):
            raise ValidationError("La cantidad de entrada debe ser mayor que cero.")

        inventory = (
            Inventory.objects.select_for_update()
            .select_related("product")
            .get(id_inventory=id_inventory)
        )

        previous_stock = inventory.current_stock
        new_stock = previous_stock + quantity

        inventory.current_stock = new_stock
        inventory.save(
            update_fields=[
                "current_stock",
                "updated_at",
            ]
        )

        InventoryMovement.objects.create(
            inventory=inventory,
            movement_type=InventoryMovement.MovementType.ENTRY,
            quantity=quantity,
            previous_stock=previous_stock,
            new_stock=new_stock,
            reference=reference,
            notes=notes,
        )

        return inventory

    @staticmethod
    @transaction.atomic
    def decrease_stock(
        id_inventory: int,
        quantity: Decimal,
        reference: str | None = None,
        notes: str | None = None,
    ) -> Inventory:
        """
        Disminuye el stock y registra un movimiento de salida.
        """

        if quantity <= Decimal("0.00"):
            raise ValidationError("La cantidad de salida debe ser mayor que cero.")

        inventory = (
            Inventory.objects.select_for_update()
            .select_related("product")
            .get(id_inventory=id_inventory)
        )

        previous_stock = inventory.current_stock

        if quantity > previous_stock:
            raise ValidationError("No hay suficiente stock disponible.")

        new_stock = previous_stock - quantity

        inventory.current_stock = new_stock
        inventory.save(
            update_fields=[
                "current_stock",
                "updated_at",
            ]
        )

        InventoryMovement.objects.create(
            inventory=inventory,
            movement_type=InventoryMovement.MovementType.EXIT,
            quantity=quantity,
            previous_stock=previous_stock,
            new_stock=new_stock,
            reference=reference,
            notes=notes,
        )

        return inventory

    @staticmethod
    @transaction.atomic
    def adjust_stock(
        id_inventory: int,
        new_stock: Decimal,
        reference: str | None = None,
        notes: str | None = None,
    ) -> Inventory:
        """
        Ajusta manualmente el stock y registra un movimiento.
        """

        if new_stock < Decimal("0.00"):
            raise ValidationError("El nuevo stock no puede ser negativo.")

        inventory = (
            Inventory.objects.select_for_update()
            .select_related("product")
            .get(id_inventory=id_inventory)
        )

        previous_stock = inventory.current_stock

        if new_stock == previous_stock:
            raise ValidationError("El nuevo stock debe ser diferente al stock actual.")

        quantity = abs(new_stock - previous_stock)

        inventory.current_stock = new_stock
        inventory.save(
            update_fields=[
                "current_stock",
                "updated_at",
            ]
        )

        InventoryMovement.objects.create(
            inventory=inventory,
            movement_type=(InventoryMovement.MovementType.ADJUSTMENT),
            quantity=quantity,
            previous_stock=previous_stock,
            new_stock=new_stock,
            reference=reference,
            notes=notes,
        )

        return inventory

    @staticmethod
    def deactivate_inventory(
        inventory: Inventory,
    ) -> None:
        """
        Desactiva lógicamente un registro de inventario.
        """

        if not inventory.is_active:
            raise ValidationError("El inventario ya se encuentra desactivado.")

        InventoryService().delete(inventory)

    @staticmethod
    def restore_inventory(
        inventory: Inventory,
    ) -> Inventory:
        """
        Restaura un registro de inventario desactivado.
        """

        if inventory.is_active:
            raise ValidationError("El inventario ya se encuentra activo.")

        return InventoryService().restore(inventory)
