from rest_framework import status
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.core.security import HasPermission
from apps.core.views.base_viewset import BaseViewSet
from apps.inventory.models.inventory_movement import InventoryMovement
from apps.inventory.selectors.inventory_movement_selector import InventoryMovementSelector
from apps.inventory.serializers.inventory_serializer import (
    InventoryMovementDetailSerializer,
    InventoryMovementListSerializer,
)
from apps.users.permissions import IsAuthenticatedAndActive


class InventoryMovementViewSet(BaseViewSet):
    """
    ViewSet encargado de consultar el historial
    global de movimientos de inventario.
    Solo lectura.
    """

    queryset = InventoryMovement.objects.none()

    permission_classes = [IsAuthenticatedAndActive]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = [
        "inventory__product__code",
        "inventory__product__name",
        "inventory__product__barcode",
        "reference",
    ]

    def get_permissions(self):
        """
        Retorna los permisos requeridos según la acción.
        """

        permission_map = {
            "list": (
                IsAuthenticatedAndActive,
                HasPermission("inventory.view"),
            ),
            "retrieve": (
                IsAuthenticatedAndActive,
                HasPermission("inventory.view"),
            ),
        }

        classes = permission_map.get(
            self.action,
            (
                IsAuthenticatedAndActive,
                HasPermission("inventory.view"),
            ),
        )

        return [permission() for permission in classes]

    def get_queryset(self):
        """
        Retorna el queryset global de movimientos de inventario.
        """
        return InventoryMovementSelector().get_queryset()

    def get_serializer_class(self):
        """
        Retorna el serializer correspondiente.
        """
        if self.action == "list":
            return InventoryMovementListSerializer
        
        return InventoryMovementDetailSerializer

    def list(self, request, *args, **kwargs):
        """
        Lista todos los movimientos globalmente.
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return self.success_response(
            message="Movimientos obtenidos correctamente.",
            code="MOVEMENTS_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    def retrieve(self, request, *args, **kwargs):
        """
        Obtiene el detalle de un movimiento.
        """
        movement = InventoryMovementSelector.get_by_id(kwargs["pk"])
        serializer = self.get_serializer(movement)

        return self.success_response(
            message="Movimiento obtenido correctamente.",
            code="MOVEMENT_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )
