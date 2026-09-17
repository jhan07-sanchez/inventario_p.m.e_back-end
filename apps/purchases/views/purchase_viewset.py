from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import action

from apps.purchases.models import Purchase
from apps.purchases.selectors.purchase_selector import PurchaseSelector
from apps.purchases.serializers.purchase_serializer import (
    PurchaseCreateSerializer,
    PurchaseRetrieveSerializer,
    PurchaseListSerializer,
    PurchaseUpdateSerializer,
)
from apps.purchases.docs.purchase_docs import (
    purchase_list_schema,
    purchase_detail_schema,
    purchase_create_schema,
    purchase_update_schema,
    purchase_partial_update_schema,
    purchase_delete_schema,
    purchase_confirm_schema,
    purchase_receive_schema,
    purchase_complete_schema,
    purchase_cancel_schema,
)
from apps.purchases.services.purchase_service import PurchaseService
from apps.core.security import HasPermission
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.core.views.base_viewset import BaseViewSet
from apps.users.permissions import IsAuthenticatedAndActive


class PurchaseViewSet(BaseViewSet):
    """
    ViewSet encargado de administrar las compras
    del sistema.
    """

    queryset = Purchase.objects.all()

    permission_classes = [IsAuthenticatedAndActive]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["observations", "supplier__name"]

    def get_permissions(self):
        """
        Retorna los permisos requeridos según la acción.
        """

        permission_map = {
            "list": (
                IsAuthenticatedAndActive,
                HasPermission("purchases.view"),
            ),
            "retrieve": (
                IsAuthenticatedAndActive,
                HasPermission("purchases.view"),
            ),
            "create": (
                IsAuthenticatedAndActive,
                HasPermission("purchases.create"),
            ),
            "update": (
                IsAuthenticatedAndActive,
                HasPermission("purchases.update"),
            ),
            "partial_update": (
                IsAuthenticatedAndActive,
                HasPermission("purchases.update"),
            ),
            "destroy": (
                IsAuthenticatedAndActive,
                HasPermission("purchases.delete"),
            ),
            "confirm": (
                IsAuthenticatedAndActive,
                HasPermission("purchases.update"),
            ),
            "receive": (
                IsAuthenticatedAndActive,
                HasPermission("purchases.update"),
            ),
            "complete": (
                IsAuthenticatedAndActive,
                HasPermission("purchases.update"),
            ),
            "cancel": (
                IsAuthenticatedAndActive,
                HasPermission("purchases.update"),
            ),
        }

        classes = permission_map.get(
            self.action,
            (
                IsAuthenticatedAndActive,
                HasPermission("purchases.view"),
            ),
        )

        return [permission() for permission in classes]

    def get_queryset(self):
        """
        Retorna el queryset de compras.

        Las consultas son delegadas al PurchaseSelector.
        """

        return PurchaseSelector.get_purchases()

    def get_serializer_class(self):
        """
        Retorna el serializer correspondiente
        según la acción ejecutada.
        """

        if self.action == "list":
            return PurchaseListSerializer

        if self.action == "retrieve":
            return PurchaseRetrieveSerializer

        if self.action == "create":
            return PurchaseCreateSerializer

        if self.action in (
            "update",
            "partial_update",
        ):
            return PurchaseUpdateSerializer

        return PurchaseRetrieveSerializer

    @purchase_list_schema
    def list(self, request, *args, **kwargs):
        """
        Lista todas las compras.
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
            message="Compras obtenidas correctamente.",
            code="PURCHASES_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @purchase_detail_schema
    def retrieve(self, request, *args, **kwargs):
        """
        Obtiene el detalle de una compra.
        """

        purchase = PurchaseSelector.get_purchase_by_id(
            kwargs["pk"],
        )

        serializer = self.get_serializer(
            purchase,
        )

        return self.success_response(
            message="Compra obtenida correctamente.",
            code="PURCHASE_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @purchase_create_schema
    def create(self, request, *args, **kwargs):
        """
        Crea una nueva compra.
        """

        serializer = self.get_serializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        try:
            purchase = PurchaseService.create_purchase(
                serializer.validated_data,
            )

            response_serializer = PurchaseRetrieveSerializer(
                purchase,
            )

            return self.success_response(
                message="Compra creada correctamente.",
                code="PURCHASE_CREATED",
                data=response_serializer.data,
                status_code=status.HTTP_201_CREATED,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible crear la compra.",
            )

    @purchase_update_schema
    def update(self, request, *args, **kwargs):
        """
        Actualiza completamente una compra.
        """

        purchase = PurchaseSelector.get_purchase_by_id(
            kwargs["pk"],
        )

        serializer = self.get_serializer(
            purchase,
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        try:
            purchase = PurchaseService.update_purchase(
                purchase,
                serializer.validated_data,
            )

            response_serializer = PurchaseRetrieveSerializer(
                purchase,
            )

            return self.success_response(
                message="Compra actualizada correctamente.",
                code="PURCHASE_UPDATED",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible actualizar la compra.",
            )

    @purchase_partial_update_schema
    def partial_update(self, request, *args, **kwargs):
        """
        Actualiza parcialmente una compra.
        """

        purchase = PurchaseSelector.get_purchase_by_id(
            kwargs["pk"],
        )

        serializer = self.get_serializer(
            purchase,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        try:
            purchase = PurchaseService.update_purchase(
                purchase,
                serializer.validated_data,
            )

            response_serializer = PurchaseRetrieveSerializer(
                purchase,
            )

            return self.success_response(
                message="Compra actualizada parcialmente.",
                code="PURCHASE_PARTIAL_UPDATED",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible actualizar la compra.",
            )

    @purchase_delete_schema
    def destroy(self, request, *args, **kwargs):
        """
        Realiza el borrado lógico de una compra.
        """

        purchase = PurchaseSelector.get_purchase_by_id(
            kwargs["pk"],
        )

        try:
            PurchaseService.deactivate_purchase(
                purchase,
            )

            return self.success_response(
                message="Compra desactivada correctamente.",
                code="PURCHASE_DELETED",
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible desactivar la compra.",
            )

    @purchase_confirm_schema
    @action(
        detail=True,
        methods=["post"],
        url_path="confirm",
    )
    def confirm(self, request, pk=None):
        """
        Confirma una compra (DRAFT -> PENDING).
        """
        purchase = PurchaseSelector.get_purchase_by_id(pk)

        try:
            PurchaseService.confirm_purchase(purchase)
            serializer = PurchaseRetrieveSerializer(purchase)

            return self.success_response(
                message="Compra confirmada con éxito.",
                code="PURCHASE_CONFIRMED",
                data=serializer.data,
                status_code=status.HTTP_200_OK,
            )
        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible confirmar la compra.",
            )

    @purchase_receive_schema
    @action(
        detail=True,
        methods=["post"],
        url_path="receive",
    )
    def receive(self, request, pk=None):
        """
        Recibe una compra e incrementa inventario (PENDING -> RECEIVED).
        """
        purchase = PurchaseSelector.get_purchase_by_id(pk)

        try:
            PurchaseService.receive_purchase(purchase)
            serializer = PurchaseRetrieveSerializer(purchase)

            return self.success_response(
                message="Compra recibida y stock actualizado con éxito.",
                code="PURCHASE_RECEIVED",
                data=serializer.data,
                status_code=status.HTTP_200_OK,
            )
        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible recibir la compra.",
            )

    @purchase_complete_schema
    @action(
        detail=True,
        methods=["post"],
        url_path="complete",
    )
    def complete(self, request, pk=None):
        """
        Completa una compra (RECEIVED -> COMPLETED).
        """
        purchase = PurchaseSelector.get_purchase_by_id(pk)

        try:
            PurchaseService.complete_purchase(purchase)
            serializer = PurchaseRetrieveSerializer(purchase)

            return self.success_response(
                message="Compra completada con éxito.",
                code="PURCHASE_COMPLETED",
                data=serializer.data,
                status_code=status.HTTP_200_OK,
            )
        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible completar la compra.",
            )

    @purchase_cancel_schema
    @action(
        detail=True,
        methods=["post"],
        url_path="cancel",
    )
    def cancel(self, request, pk=None):
        """
        Cancela una compra.
        """
        purchase = PurchaseSelector.get_purchase_by_id(pk)

        try:
            PurchaseService.cancel_purchase(purchase)
            serializer = PurchaseRetrieveSerializer(purchase)

            return self.success_response(
                message="Compra cancelada con éxito.",
                code="PURCHASE_CANCELLED",
                data=serializer.data,
                status_code=status.HTTP_200_OK,
            )
        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible cancelar la compra.",
            )
