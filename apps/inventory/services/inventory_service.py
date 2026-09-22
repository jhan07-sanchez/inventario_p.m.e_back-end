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
    @transaction.atomic
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
    def update_thresholds(
        inventory: Inventory,
        data: dict,
    ) -> Inventory:
        """
        Actualiza los umbrales de stock mínimo y máximo.
        """
        return InventoryService().update(
            inventory,
            **data,
        )

    @staticmethod
    @transaction.atomic
    def register_entry(
        inventory: Inventory,
        data: dict,
        user=None,
    ) -> InventoryMovement:
        """
        Incrementa el stock y registra un movimiento de entrada.
        """

        quantity = data.get("quantity")
        reference = data.get("reference", None)
        notes = data.get("notes", None)
        supplier_id = data.get("supplier_id", None)

        if quantity <= Decimal("0.00"):
            raise ValidationError("La cantidad de entrada debe ser mayor que cero.")

        # Resolver el proveedor si se proporcionó
        supplier = None
        if supplier_id:
            from apps.suppliers.models import Supplier
            try:
                supplier = Supplier.objects.get(pk=supplier_id, is_active=True)
            except Supplier.DoesNotExist:
                raise ValidationError("El proveedor seleccionado no existe o está inactivo.")

        inventory_locked = (
            Inventory.objects.select_for_update()
            .select_related("product")
            .get(pk=inventory.pk)
        )

        previous_stock = inventory_locked.current_stock
        new_stock = previous_stock + quantity

        inventory_locked.current_stock = new_stock
        inventory_locked.save(
            update_fields=[
                "current_stock",
                "updated_at",
            ]
        )

        movement = InventoryMovement.objects.create(
            inventory=inventory_locked,
            movement_type=InventoryMovement.MovementType.ENTRY,
            quantity=quantity,
            previous_stock=previous_stock,
            new_stock=new_stock,
            reference=reference,
            notes=notes,
            supplier=supplier,
        )

        return movement

    @staticmethod
    @transaction.atomic
    def register_exit(
        inventory: Inventory,
        data: dict,
        user=None,
    ) -> InventoryMovement:
        """
        Disminuye el stock y registra un movimiento de salida.
        """
        
        quantity = data.get("quantity")
        reference = data.get("reference", None)
        notes = data.get("notes", None)

        if quantity <= Decimal("0.00"):
            raise ValidationError("La cantidad de salida debe ser mayor que cero.")

        inventory_locked = (
            Inventory.objects.select_for_update()
            .select_related("product")
            .get(pk=inventory.pk)
        )

        previous_stock = inventory_locked.current_stock

        if quantity > previous_stock:
            raise ValidationError("No hay suficiente stock disponible.")

        new_stock = previous_stock - quantity

        inventory_locked.current_stock = new_stock
        inventory_locked.save(
            update_fields=[
                "current_stock",
                "updated_at",
            ]
        )

        movement = InventoryMovement.objects.create(
            inventory=inventory_locked,
            movement_type=InventoryMovement.MovementType.EXIT,
            quantity=quantity,
            previous_stock=previous_stock,
            new_stock=new_stock,
            reference=reference,
            notes=notes,
        )

        return movement

    @staticmethod
    @transaction.atomic
    def register_adjustment(
        inventory: Inventory,
        data: dict,
        user=None,
    ) -> InventoryMovement:
        """
        Ajusta manualmente el stock y registra un movimiento.
        """
        
        new_stock = data.get("new_stock")
        reference = data.get("reference", None)
        notes = data.get("notes", None)

        if new_stock < Decimal("0.00"):
            raise ValidationError("El nuevo stock no puede ser negativo.")

        inventory_locked = (
            Inventory.objects.select_for_update()
            .select_related("product")
            .get(pk=inventory.pk)
        )

        previous_stock = inventory_locked.current_stock

        if new_stock == previous_stock:
            raise ValidationError("El nuevo stock debe ser diferente al stock actual.")

        quantity = abs(new_stock - previous_stock)

        inventory_locked.current_stock = new_stock
        inventory_locked.save(
            update_fields=[
                "current_stock",
                "updated_at",
            ]
        )

        movement = InventoryMovement.objects.create(
            inventory=inventory_locked,
            movement_type=(InventoryMovement.MovementType.ADJUSTMENT),
            quantity=quantity,
            previous_stock=previous_stock,
            new_stock=new_stock,
            reference=reference,
            notes=notes,
        )

        return movement

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
            return inventory

        return InventoryService().restore(inventory)
