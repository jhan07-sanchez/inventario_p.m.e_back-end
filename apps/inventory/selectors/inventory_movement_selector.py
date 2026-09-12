from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from apps.core.selectors.base_selector import BaseSelector
from apps.inventory.models.inventory_movement import InventoryMovement


class InventoryMovementSelector(BaseSelector[InventoryMovement]):
    """
    Selector encargado de las consultas relacionadas
    con los movimientos de inventario.
    """

    def __init__(self):
        super().__init__(InventoryMovement)

    def get_queryset(self) -> QuerySet[InventoryMovement]:
        """
        Retorna el queryset base optimizando relaciones.
        """
        return (
            super()
            .get_queryset()
            .select_related("inventory", "inventory__product")
            .order_by("-created_at")
        )

    @staticmethod
    def get_movements_by_inventory(id_inventory: int) -> QuerySet[InventoryMovement]:
        """
        Obtiene el historial de movimientos de un inventario específico.
        """
        return (
            InventoryMovementSelector()
            .get_queryset()
            .filter(inventory_id=id_inventory)
        )

    @staticmethod
    def get_by_id(id_movement: int) -> InventoryMovement:
        """
        Obtiene un movimiento por su ID.
        """
        return get_object_or_404(
            InventoryMovementSelector().get_queryset(),
            id_movement=id_movement,
        )

    @staticmethod
    def filter_movements(
        *,
        inventory: int | None = None,
        movement_type: str | None = None,
    ) -> QuerySet[InventoryMovement]:
        """
        Retorna movimientos aplicando filtros.
        """
        queryset = InventoryMovementSelector().get_queryset()

        if inventory is not None:
            queryset = queryset.filter(inventory_id=inventory)

        if movement_type is not None:
            queryset = queryset.filter(movement_type=movement_type)

        return queryset
