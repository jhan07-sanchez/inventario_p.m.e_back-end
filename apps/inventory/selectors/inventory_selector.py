from django.db.models import F, QuerySet
from django.shortcuts import get_object_or_404

from apps.core.selectors.base_selector import BaseSelector
from apps.inventory.models import Inventory


class InventorySelector(BaseSelector[Inventory]):
    """
    Selector encargado de las consultas relacionadas
    con los inventarios.

    Los selectors contienen exclusivamente lógica de lectura.
    """

    def __init__(self):
        super().__init__(Inventory)

    def get_queryset(self) -> QuerySet[Inventory]:
        """
        Retorna el queryset base de inventarios optimizando
        las relaciones necesarias.
        """
        return (
            super()
            .get_queryset()
            .select_related("product", "product__category")
            .order_by("id_inventory")
        )

    @staticmethod
    def get_inventories() -> QuerySet[Inventory]:
        """
        Retorna todos los inventarios.
        """
        return InventorySelector().get_all()

    @staticmethod
    def get_active_inventories() -> QuerySet[Inventory]:
        """
        Retorna únicamente los inventarios activos.
        """
        return InventorySelector().get_active()

    @staticmethod
    def get_by_id(id_inventory: int) -> Inventory:
        """
        Obtiene un inventario por su identificador.
        """
        return get_object_or_404(
            InventorySelector().get_queryset(),
            id_inventory=id_inventory,
        )

    @staticmethod
    def get_by_product(id_product: int) -> Inventory:
        """
        Obtiene el inventario asociado a un producto.
        """
        return get_object_or_404(
            InventorySelector().get_queryset(),
            product_id=id_product,
        )

    @staticmethod
    def inventory_exists(
        *,
        id_product: int | None = None,
    ) -> bool:
        """
        Verifica si existe un inventario asociado a un producto.
        """
        selector = InventorySelector()

        if id_product is not None:
            return selector.exists(product_id=id_product)

        return False

    @staticmethod
    def filter_inventories(
        *,
        product: int | None = None,
        category: int | None = None,
        is_active: bool | None = None,
        low_stock: bool | None = None,
        out_of_stock: bool | None = None,
    ) -> QuerySet[Inventory]:
        """
        Retorna inventarios aplicando filtros opcionales.
        """
        queryset = InventorySelector().get_queryset()

        if product is not None:
            queryset = queryset.filter(
                product_id=product,
            )

        if category is not None:
            queryset = queryset.filter(
                product__category_id=category,
            )

        if is_active is not None:
            queryset = queryset.filter(
                is_active=is_active,
            )

        if low_stock is True:
            queryset = queryset.filter(
                current_stock__lte=F("minimum_stock"),
            )

        if out_of_stock is True:
            queryset = queryset.filter(
                current_stock=0,
            )

        return queryset.order_by("-created_at")

    @staticmethod
    def get_movements(
        inventory: Inventory,
    ) -> QuerySet:
        """
        Obtiene el historial de movimientos de un inventario específico.
        """
        from apps.inventory.selectors.inventory_movement_selector import InventoryMovementSelector
        return InventoryMovementSelector.get_movements_by_inventory(id_inventory=inventory.id_inventory)
