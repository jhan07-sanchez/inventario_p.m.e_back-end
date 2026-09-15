from django.core.exceptions import ValidationError

from rest_framework import status
from rest_framework.decorators import action

from apps.core.security import HasPermission
from apps.core.views.base_viewset import BaseViewSet
from apps.inventory.models import Inventory
from apps.inventory.selectors.inventory_selector import InventorySelector
from apps.inventory.serializers.inventory_serializer import (
    InventoryAdjustmentSerializer,
    InventoryCreateSerializer,
    InventoryDetailSerializer,
    InventoryEntrySerializer,
    InventoryExitSerializer,
    InventoryListSerializer,
    InventoryMovementSerializer,
    InventoryThresholdUpdateSerializer,
    InventoryUpdateSerializer,
)
from apps.inventory.docs.inventory_docs import (
    inventory_adjustment_schema,
    inventory_create_schema,
    inventory_delete_schema,
    inventory_detail_schema,
    inventory_entry_schema,
    inventory_exit_schema,
    inventory_list_schema,
    inventory_movements_schema,
    inventory_partial_update_schema,
    inventory_thresholds_schema,
    inventory_update_schema,
)
from apps.inventory.services.inventory_service import InventoryService
from apps.users.permissions import IsAuthenticatedAndActive


class InventoryViewSet(BaseViewSet):
    """
    ViewSet encargado de administrar el inventario
    del sistema.
    """

    queryset = Inventory.objects.none()

    permission_classes = [IsAuthenticatedAndActive]

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
            "create": (
                IsAuthenticatedAndActive,
                HasPermission("inventory.create"),
            ),
            "update": (
                IsAuthenticatedAndActive,
                HasPermission("inventory.update"),
            ),
            "partial_update": (
                IsAuthenticatedAndActive,
                HasPermission("inventory.update"),
            ),
            "destroy": (
                IsAuthenticatedAndActive,
                HasPermission("inventory.delete"),
            ),
            "thresholds": (
                IsAuthenticatedAndActive,
                HasPermission("inventory.update"),
            ),
            "entry": (
                IsAuthenticatedAndActive,
                HasPermission("inventory.movement"),
            ),
            "exit": (
                IsAuthenticatedAndActive,
                HasPermission("inventory.movement"),
            ),
            "adjustment": (
                IsAuthenticatedAndActive,
                HasPermission("inventory.movement"),
            ),
            "movements": (
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
        Retorna el queryset de inventarios.

        Las consultas son delegadas al InventorySelector.
        """

        return InventorySelector.get_inventories()

    def get_serializer_class(self):
        """
        Retorna el serializer correspondiente según
        la acción ejecutada.
        """

        if self.action == "list":
            return InventoryListSerializer

        if self.action == "retrieve":
            return InventoryDetailSerializer

        if self.action == "create":
            return InventoryCreateSerializer

        if self.action in (
            "update",
            "partial_update",
        ):
            return InventoryUpdateSerializer

        if self.action == "thresholds":
            return InventoryThresholdUpdateSerializer

        if self.action == "entry":
            return InventoryEntrySerializer

        if self.action == "exit":
            return InventoryExitSerializer

        if self.action == "adjustment":
            return InventoryAdjustmentSerializer

        if self.action == "movements":
            return InventoryMovementSerializer

        return InventoryDetailSerializer

    @inventory_list_schema
    def list(self, request, *args, **kwargs):
        """
        Lista todos los registros de inventario.
        """

        queryset = self.filter_queryset(
            self.get_queryset(),
        )

        page = self.paginate_queryset(
            queryset,
        )

        if page is not None:
            serializer = self.get_serializer(
                page,
                many=True,
            )

            return self.get_paginated_response(
                serializer.data,
            )

        serializer = self.get_serializer(
            queryset,
            many=True,
        )

        return self.success_response(
            message="Inventarios obtenidos correctamente.",
            code="INVENTORIES_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @inventory_detail_schema
    def retrieve(self, request, *args, **kwargs):
        """
        Obtiene el detalle de un inventario.
        """

        inventory = InventorySelector.get_by_id(
            kwargs["pk"],
        )

        serializer = self.get_serializer(
            inventory,
        )

        return self.success_response(
            message="Inventario obtenido correctamente.",
            code="INVENTORY_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @inventory_create_schema
    def create(self, request, *args, **kwargs):
        """
        Crea un nuevo registro de inventario.
        """

        serializer = self.get_serializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        try:
            inventory = InventoryService.create_inventory(
                serializer.validated_data,
            )

            response_serializer = InventoryDetailSerializer(
                inventory,
            )

            return self.success_response(
                message="Inventario creado correctamente.",
                code="INVENTORY_CREATED",
                data=response_serializer.data,
                status_code=status.HTTP_201_CREATED,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible crear el inventario.",
            )

    @inventory_update_schema
    def update(self, request, *args, **kwargs):
        """
        Actualiza completamente un inventario.
        """

        inventory = InventorySelector.get_by_id(
            kwargs["pk"],
        )

        serializer = self.get_serializer(
            inventory,
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        try:
            inventory = InventoryService.update_inventory(
                inventory,
                serializer.validated_data,
            )

            response_serializer = InventoryDetailSerializer(
                inventory,
            )

            return self.success_response(
                message="Inventario actualizado correctamente.",
                code="INVENTORY_UPDATED",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible actualizar el inventario.",
            )

    @inventory_partial_update_schema
    def partial_update(self, request, *args, **kwargs):
        """
        Actualiza parcialmente un inventario.
        """

        inventory = InventorySelector.get_by_id(
            kwargs["pk"],
        )

        serializer = self.get_serializer(
            inventory,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        try:
            inventory = InventoryService.update_inventory(
                inventory,
                serializer.validated_data,
            )

            response_serializer = InventoryDetailSerializer(
                inventory,
            )

            return self.success_response(
                message="Inventario actualizado correctamente.",
                code="INVENTORY_PARTIAL_UPDATED",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible actualizar el inventario.",
            )

    @inventory_delete_schema
    def destroy(self, request, *args, **kwargs):
        """
        Elimina o desactiva un registro de inventario.
        """

        inventory = InventorySelector.get_by_id(
            kwargs["pk"],
        )

        try:
            InventoryService.deactivate_inventory(
                inventory,
            )

            return self.success_response(
                message="Inventario desactivado correctamente.",
                code="INVENTORY_DEACTIVATED",
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible desactivar el inventario.",
            )

    @inventory_thresholds_schema
    @action(
        detail=True,
        methods=["patch"],
        url_path="thresholds",
    )
    def thresholds(
        self,
        request,
        pk=None,
    ):
        """
        Actualiza los umbrales de stock mínimo y máximo.
        """

        inventory = InventorySelector.get_by_id(
            pk,
        )

        serializer = self.get_serializer(
            inventory,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        try:
            inventory = InventoryService.update_thresholds(
                inventory,
                serializer.validated_data,
            )

            response_serializer = InventoryDetailSerializer(
                inventory,
            )

            return self.success_response(
                message="Umbrales actualizados correctamente.",
                code="INVENTORY_THRESHOLDS_UPDATED",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible actualizar los umbrales.",
            )

    @inventory_entry_schema
    @action(
        detail=True,
        methods=["post"],
        url_path="entry",
    )
    def entry(
        self,
        request,
        pk=None,
    ):
        """
        Registra una entrada de stock al inventario.
        """

        inventory = InventorySelector.get_by_id(
            pk,
        )

        serializer = self.get_serializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        try:
            movement = InventoryService.register_entry(
                inventory=inventory,
                data=serializer.validated_data,
                user=request.user,
            )

            response_serializer = InventoryMovementSerializer(
                movement,
            )

            return self.success_response(
                message="Entrada registrada correctamente.",
                code="INVENTORY_ENTRY_REGISTERED",
                data=response_serializer.data,
                status_code=status.HTTP_201_CREATED,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible registrar la entrada.",
            )

    @inventory_exit_schema
    @action(
        detail=True,
        methods=["post"],
        url_path="exit",
    )
    def exit(
        self,
        request,
        pk=None,
    ):
        """
        Registra una salida de stock del inventario.
        """

        inventory = InventorySelector.get_by_id(
            pk,
        )

        serializer = self.get_serializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        try:
            movement = InventoryService.register_exit(
                inventory=inventory,
                data=serializer.validated_data,
                user=request.user,
            )

            response_serializer = InventoryMovementSerializer(
                movement,
            )

            return self.success_response(
                message="Salida registrada correctamente.",
                code="INVENTORY_EXIT_REGISTERED",
                data=response_serializer.data,
                status_code=status.HTTP_201_CREATED,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible registrar la salida.",
            )

    @inventory_adjustment_schema
    @action(
        detail=True,
        methods=["post"],
        url_path="adjustment",
    )
    def adjustment(
        self,
        request,
        pk=None,
    ):
        """
        Realiza un ajuste manual del stock del inventario.
        """

        inventory = InventorySelector.get_by_id(
            pk,
        )

        serializer = self.get_serializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        try:
            movement = InventoryService.register_adjustment(
                inventory=inventory,
                data=serializer.validated_data,
                user=request.user,
            )

            response_serializer = InventoryMovementSerializer(
                movement,
            )

            return self.success_response(
                message="Ajuste registrado correctamente.",
                code="INVENTORY_ADJUSTMENT_REGISTERED",
                data=response_serializer.data,
                status_code=status.HTTP_201_CREATED,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible registrar el ajuste.",
            )

    @inventory_movements_schema
    @action(
        detail=True,
        methods=["get"],
        url_path="movements",
    )
    def movements(
        self,
        request,
        pk=None,
    ):
        """
        Obtiene el historial de movimientos de un inventario.
        """

        inventory = InventorySelector.get_by_id(
            pk,
        )

        queryset = InventorySelector.get_movements(
            inventory=inventory,
        )

        queryset = self.filter_queryset(
            queryset,
        )

        page = self.paginate_queryset(
            queryset,
        )

        if page is not None:
            serializer = self.get_serializer(
                page,
                many=True,
            )

            return self.get_paginated_response(
                serializer.data,
            )

        serializer = self.get_serializer(
            queryset,
            many=True,
        )

        return self.success_response(
            message="Historial de movimientos obtenido correctamente.",
            code="INVENTORY_MOVEMENTS_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )
