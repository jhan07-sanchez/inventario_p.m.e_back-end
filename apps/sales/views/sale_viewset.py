from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.core.security import HasPermission
from apps.core.views.base_viewset import BaseViewSet
from apps.sales.models import Sale
from apps.sales.selectors.sale_selector import SaleSelector
from apps.sales.docs.sale_docs import (
    sale_cancel_schema,
    sale_complete_schema,
    sale_create_schema,
    sale_delete_schema,
    sale_detail_schema,
    sale_list_schema,
    sale_partial_update_schema,
    sale_restore_schema,
    sale_update_schema,
)
from apps.sales.serializers.sale_serializer import (
    SaleCreateSerializer,
    SaleListSerializer,
    SaleRetrieveSerializer,
    SaleUpdateSerializer,
)
from apps.sales.services.sale_service import SaleService
from apps.users.permissions import IsAuthenticatedAndActive


class SaleViewSet(BaseViewSet):
    """
    ViewSet encargado de administrar las ventas del sistema.
    """

    queryset = Sale.objects.all()

    permission_classes = [IsAuthenticatedAndActive]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = [
        "notes",
        "customer__business_name",
        "customer__first_name",
        "customer__last_name",
        "customer__document_number",
    ]

    def get_permissions(self):
        """
        Retorna los permisos requeridos según la acción.
        """

        permission_map = {
            "list": (
                IsAuthenticatedAndActive,
                HasPermission("sales.view"),
            ),
            "retrieve": (
                IsAuthenticatedAndActive,
                HasPermission("sales.view"),
            ),
            "create": (
                IsAuthenticatedAndActive,
                HasPermission("sales.create"),
            ),
            "update": (
                IsAuthenticatedAndActive,
                HasPermission("sales.update"),
            ),
            "partial_update": (
                IsAuthenticatedAndActive,
                HasPermission("sales.update"),
            ),
            "destroy": (
                IsAuthenticatedAndActive,
                HasPermission("sales.delete"),
            ),
            "complete": (
                IsAuthenticatedAndActive,
                (
                    HasPermission("sales.complete")
                    | HasPermission("sales.approve")
                    | HasPermission("sales.update")
                )
                & (
                    HasPermission("sales.invoice")
                    | HasPermission("sales.approve")
                    | HasPermission("sales.update")
                ),
            ),
            "cancel": (
                IsAuthenticatedAndActive,
                (
                    HasPermission("sales.cancel")
                    | HasPermission("sales.update")
                ),
            ),
            "restore": (
                IsAuthenticatedAndActive,
                HasPermission("sales.update"),
            ),
        }

        classes = permission_map.get(
            self.action,
            (
                IsAuthenticatedAndActive,
                HasPermission("sales.view"),
            ),
        )

        return [permission() for permission in classes]

    def get_queryset(self):
        """
        Retorna el queryset de ventas.

        Las consultas son delegadas al SaleSelector.
        """

        customer_id = self.request.query_params.get("customer_id")
        sale_status = self.request.query_params.get("status")
        invoice_number = self.request.query_params.get("invoice_number")
        invoice_status = self.request.query_params.get("invoice_status")

        is_active_param = self.request.query_params.get("is_active")
        is_active = True
        if is_active_param is not None:
            is_active = is_active_param.lower() == "true"

        return SaleSelector.filter_sales(
            customer_id=customer_id,
            status=sale_status,
            invoice_number=invoice_number,
            invoice_status=invoice_status,
            is_active=is_active,
        )

    def get_serializer_class(self):
        """
        Retorna el serializer correspondiente según la acción ejecutada.
        """

        if self.action == "list":
            return SaleListSerializer

        if self.action == "retrieve":
            return SaleRetrieveSerializer

        if self.action == "create":
            return SaleCreateSerializer

        if self.action in ("update", "partial_update"):
            return SaleUpdateSerializer

        return SaleRetrieveSerializer

    @sale_list_schema
    def list(self, request, *args, **kwargs):
        """
        Lista todas las ventas.
        """

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)

        return self.success_response(
            message="Ventas obtenidas correctamente.",
            code="SALES_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @sale_detail_schema
    def retrieve(self, request, *args, **kwargs):
        """
        Obtiene el detalle de una venta.
        """

        sale = SaleSelector.get_by_id(kwargs["pk"])
        serializer = self.get_serializer(sale)

        return self.success_response(
            message="Venta obtenida correctamente.",
            code="SALE_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @sale_create_schema
    def create(self, request, *args, **kwargs):
        """
        Crea una nueva venta.
        """

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            sale = SaleService.create_sale(
                serializer.to_dto(),
                request.user,
            )

            response_serializer = SaleRetrieveSerializer(sale)

            return self.success_response(
                message="Venta creada correctamente.",
                code="SALE_CREATED",
                data=response_serializer.data,
                status_code=status.HTTP_201_CREATED,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible crear la venta.",
            )

    @sale_update_schema
    def update(self, request, *args, **kwargs):
        """
        Actualiza completamente una venta.
        """

        sale = SaleSelector.get_by_id(kwargs["pk"])
        serializer = self.get_serializer(sale, data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            sale = SaleService.update_sale(sale, serializer.to_dto())
            response_serializer = SaleRetrieveSerializer(sale)

            return self.success_response(
                message="Venta actualizada correctamente.",
                code="SALE_UPDATED",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible actualizar la venta.",
            )

    @sale_partial_update_schema
    def partial_update(self, request, *args, **kwargs):
        """
        Actualiza parcialmente una venta.
        """

        sale = SaleSelector.get_by_id(kwargs["pk"])
        serializer = self.get_serializer(
            sale,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        try:
            sale = SaleService.update_sale(sale, serializer.to_dto())
            response_serializer = SaleRetrieveSerializer(sale)

            return self.success_response(
                message="Venta actualizada parcialmente.",
                code="SALE_PARTIAL_UPDATED",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible actualizar la venta.",
            )

    @sale_delete_schema
    def destroy(self, request, *args, **kwargs):
        """
        Realiza el borrado lógico de una venta.
        """

        sale = SaleSelector.get_by_id(kwargs["pk"])

        try:
            SaleService.deactivate_sale(sale)

            return self.success_response(
                message="Venta desactivada correctamente.",
                code="SALE_DELETED",
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible desactivar la venta.",
            )

    @sale_restore_schema
    @action(
        detail=True,
        methods=["post"],
        url_path="restore",
    )
    def restore(self, request, pk=None):
        """
        Restaura una venta previamente desactivada.
        """

        sale = SaleSelector.get_by_id(pk)

        try:
            SaleService.restore_sale(sale)
            serializer = SaleRetrieveSerializer(sale)

            return self.success_response(
                message="Venta restaurada correctamente.",
                code="SALE_RESTORED",
                data=serializer.data,
                status_code=status.HTTP_200_OK,
            )
        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible restaurar la venta.",
            )

    @sale_complete_schema
    @action(
        detail=True,
        methods=["post"],
        url_path="complete",
    )
    def complete(self, request, pk=None):
        """
        Completa una venta y descuenta el inventario.
        """

        sale = SaleSelector.get_by_id(pk)

        try:
            sale = SaleService.complete_sale(sale, request.user)
            serializer = SaleRetrieveSerializer(sale)

            return self.success_response(
                message="Venta completada y stock actualizado con éxito.",
                code="SALE_COMPLETED",
                data=serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible completar la venta.",
            )

    @sale_cancel_schema
    @action(
        detail=True,
        methods=["post"],
        url_path="cancel",
    )
    def cancel(self, request, pk=None):
        """
        Cancela una venta y revierte el inventario cuando corresponde.
        """

        sale = SaleSelector.get_by_id(pk)

        try:
            sale = SaleService.cancel_sale(sale, request.user)
            serializer = SaleRetrieveSerializer(sale)

            return self.success_response(
                message="Venta cancelada con éxito.",
                code="SALE_CANCELLED",
                data=serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible cancelar la venta.",
            )
