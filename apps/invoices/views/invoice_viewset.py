from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.core.security import HasPermission
from apps.core.views.base_viewset import BaseViewSet
from apps.invoices.models import Invoice
from apps.invoices.docs.invoice_docs import (
    invoice_cancel_schema,
    invoice_create_schema,
    invoice_delete_schema,
    invoice_issue_schema,
    invoice_list_schema,
    invoice_retrieve_schema,
    invoice_put_schema,
    invoice_patch_schema,
    invoice_restore_schema,
)
from apps.invoices.selectors.invoice_selector import InvoiceSelector
from apps.invoices.serializers.invoice_serializer import (
    InvoiceCreateSerializer,
    InvoiceListSerializer,
    InvoiceRetrieveSerializer,
    InvoiceUpdateSerializer,
)
from apps.invoices.services.invoice_service import InvoiceService
from apps.users.permissions import IsAuthenticatedAndActive


class InvoiceViewSet(BaseViewSet):
    """
    ViewSet encargado de administrar las facturas
    y documentos del sistema.
    """

    queryset = Invoice.objects.none()

    permission_classes = [IsAuthenticatedAndActive]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["number", "customer_name", "customer_document"]

    def get_permissions(self):
        """
        Retorna los permisos requeridos según la acción.
        """
        permission_map = {
            "list": (
                IsAuthenticatedAndActive,
                HasPermission("invoices.view"),
            ),
            "retrieve": (
                IsAuthenticatedAndActive,
                HasPermission("invoices.view"),
            ),
            "create": (
                IsAuthenticatedAndActive,
                HasPermission("invoices.create"),
            ),
            "update": (
                IsAuthenticatedAndActive,
                HasPermission("invoices.update"),
            ),
            "partial_update": (
                IsAuthenticatedAndActive,
                HasPermission("invoices.update"),
            ),
            "destroy": (
                IsAuthenticatedAndActive,
                HasPermission("invoices.delete"),
            ),
            "issue": (
                IsAuthenticatedAndActive,
                HasPermission("invoices.update"),
            ),
            "cancel": (
                IsAuthenticatedAndActive,
                HasPermission("invoices.update"),
            ),
            "restore": (
                IsAuthenticatedAndActive,
                HasPermission("invoices.update"),
            ),
        }

        classes = permission_map.get(
            self.action,
            (
                IsAuthenticatedAndActive,
                HasPermission("invoices.view"),
            ),
        )

        return [permission() for permission in classes]

    def get_queryset(self):
        """
        Retorna el queryset de facturas filtrado opcionalmente.
        Las consultas son delegadas al InvoiceSelector.
        """
        document_type = self.request.query_params.get("document_type")
        invoice_status = self.request.query_params.get("status")
        purchase = self.request.query_params.get("purchase")
        sale = self.request.query_params.get("sale")
        invoice_number = self.request.query_params.get("invoice_number")

        is_active_param = self.request.query_params.get("is_active")
        is_active = None
        if is_active_param is not None:
            is_active = is_active_param.lower() == "true"

        return InvoiceSelector.filter_invoices(
            document_type=document_type,
            status=invoice_status,
            is_active=is_active,
            purchase=purchase,
            sale=sale,
            invoice_number=invoice_number,
        )

    def get_serializer_class(self):
        """
        Retorna el serializer correspondiente según
        la acción ejecutada.
        """
        if self.action == "list":
            return InvoiceListSerializer

        if self.action == "retrieve":
            return InvoiceRetrieveSerializer

        if self.action == "create":
            return InvoiceCreateSerializer

        if self.action in ("update", "partial_update"):
            return InvoiceUpdateSerializer

        return InvoiceRetrieveSerializer

    @invoice_list_schema
    def list(self, request, *args, **kwargs):
        """
        Lista todas las facturas de forma paginada o general.
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
            message="Facturas obtenidas correctamente.",
            code="INVOICES_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @invoice_retrieve_schema
    def retrieve(self, request, *args, **kwargs):
        """
        Obtiene el detalle de una factura específica.
        """
        invoice = InvoiceSelector.get_by_id(
            kwargs["pk"],
        )

        serializer = self.get_serializer(
            invoice,
        )

        return self.success_response(
            message="Factura obtenida correctamente.",
            code="INVOICE_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @invoice_create_schema
    def create(self, request, *args, **kwargs):
        """
        Crea una nueva factura o documento.
        """
        serializer = self.get_serializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        dto = serializer.to_dto()

        try:
            invoice = InvoiceService.create_invoice(dto)

            response_serializer = InvoiceRetrieveSerializer(
                invoice,
            )

            return self.success_response(
                message="Factura creada exitosamente.",
                code="INVOICE_CREATED",
                data=response_serializer.data,
                status_code=status.HTTP_201_CREATED,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible crear la factura.",
            )

    @invoice_put_schema
    def update(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    @invoice_patch_schema
    def partial_update(self, request, *args, **kwargs):
        """
        Actualiza parcialmente una factura.
        """
        invoice = InvoiceSelector.get_by_id(
            kwargs["pk"],
        )

        serializer = self.get_serializer(
            invoice,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        dto = serializer.to_dto()

        try:
            updated_invoice = InvoiceService.update_invoice(
                invoice=invoice,
                dto=dto,
            )

            response_serializer = InvoiceRetrieveSerializer(
                updated_invoice,
            )

            return self.success_response(
                message="Factura actualizada correctamente.",
                code="INVOICE_UPDATED",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible actualizar la factura.",
            )

    @invoice_delete_schema
    def destroy(self, request, *args, **kwargs):
        """
        Realiza la desactivación lógica de una factura.
        """
        invoice = InvoiceSelector.get_by_id(
            kwargs["pk"],
        )

        try:
            InvoiceService.deactivate_invoice(invoice)

            return self.success_response(
                message="Factura desactivada correctamente.",
                code="INVOICE_DEACTIVATED",
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible desactivar la factura.",
            )

    @invoice_restore_schema
    @action(
        detail=True,
        methods=["post"],
        url_path="restore",
    )
    def restore(self, request, pk=None):
        """
        Restaura una factura previamente desactivada.
        """
        invoice = InvoiceSelector.get_by_id(pk)

        try:
            InvoiceService.restore_invoice(invoice)
            serializer = InvoiceRetrieveSerializer(invoice)

            return self.success_response(
                message="Factura restaurada correctamente.",
                code="INVOICE_RESTORED",
                data=serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible restaurar la factura.",
            )

    @invoice_issue_schema
    @action(
        detail=True,
        methods=["patch"],
        url_path="issue",
    )
    def issue(self, request, pk=None):
        """
        Emite formalmente la factura.
        """
        invoice = InvoiceSelector.get_by_id(pk)

        try:
            issued_invoice = InvoiceService.issue_invoice(invoice)
            serializer = InvoiceRetrieveSerializer(issued_invoice)

            return self.success_response(
                message="Factura emitida correctamente.",
                code="INVOICE_ISSUED",
                data=serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible emitir la factura.",
            )

    @invoice_cancel_schema
    @action(
        detail=True,
        methods=["patch"],
        url_path="cancel",
    )
    def cancel(self, request, pk=None):
        """
        Anula una factura existente.
        """
        invoice = InvoiceSelector.get_by_id(pk)

        try:
            cancelled_invoice = InvoiceService.cancel_invoice(invoice)
            serializer = InvoiceRetrieveSerializer(cancelled_invoice)

            return self.success_response(
                message="Factura anulada correctamente.",
                code="INVOICE_CANCELLED",
                data=serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible anular la factura.",
            )
