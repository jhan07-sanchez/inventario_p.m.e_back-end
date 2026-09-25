from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.core.security import HasPermission
from apps.core.views.base_viewset import BaseViewSet
from apps.invoices.models import InvoiceTemplate
from apps.invoices.docs.invoice_template_docs import (
    invoice_template_create_schema,
    invoice_template_delete_schema,
    invoice_template_list_schema,
    invoice_template_retrieve_schema,
    invoice_template_put_schema,
    invoice_template_patch_schema,
    invoice_template_restore_schema,
)
from apps.invoices.selectors.invoice_template_selector import InvoiceTemplateSelector
from apps.invoices.serializers.invoice_template_serializer import (
    InvoiceTemplateCreateSerializer,
    InvoiceTemplateListSerializer,
    InvoiceTemplateRetrieveSerializer,
    InvoiceTemplateUpdateSerializer,
)
from apps.invoices.services.invoice_template_service import InvoiceTemplateService
from apps.users.permissions import IsAuthenticatedAndActive


class InvoiceTemplateViewSet(BaseViewSet):
    """
    ViewSet encargado de administrar las plantillas de facturación del sistema.
    """

    queryset = InvoiceTemplate.objects.none()

    permission_classes = [IsAuthenticatedAndActive]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "document_type"]

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
        Retorna el queryset de plantillas.
        Las consultas son delegadas al InvoiceTemplateSelector.
        """
        return InvoiceTemplateSelector.get_templates()

    def get_serializer_class(self):
        """
        Retorna el serializer correspondiente según la acción ejecutada.
        """
        if self.action == "list":
            return InvoiceTemplateListSerializer

        if self.action == "retrieve":
            return InvoiceTemplateRetrieveSerializer

        if self.action == "create":
            return InvoiceTemplateCreateSerializer

        if self.action in ("update", "partial_update"):
            return InvoiceTemplateUpdateSerializer

        return InvoiceTemplateRetrieveSerializer

    @invoice_template_list_schema
    def list(self, request, *args, **kwargs):
        """
        Lista todas las plantillas de facturación de forma paginada o general.
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
            message="Plantillas recuperadas correctamente.",
            code="INVOICE_TEMPLATES_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @invoice_template_retrieve_schema
    def retrieve(self, request, *args, **kwargs):
        """
        Obtiene el detalle de una plantilla específica.
        """
        template = InvoiceTemplateSelector.get_by_id(
            kwargs["pk"],
        )

        serializer = self.get_serializer(
            template,
        )

        return self.success_response(
            message="Plantilla recuperada correctamente.",
            code="INVOICE_TEMPLATE_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @invoice_template_create_schema
    def create(self, request, *args, **kwargs):
        """
        Crea una nueva plantilla de factura.
        """
        serializer = self.get_serializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        dto = serializer.to_dto()

        try:
            template = InvoiceTemplateService.create_template(dto)

            response_serializer = InvoiceTemplateRetrieveSerializer(
                template,
            )

            return self.success_response(
                message="Plantilla creada exitosamente.",
                code="INVOICE_TEMPLATE_CREATED",
                data=response_serializer.data,
                status_code=status.HTTP_201_CREATED,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible crear la plantilla.",
            )

    @invoice_template_put_schema
    def update(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    @invoice_template_patch_schema
    def partial_update(self, request, *args, **kwargs):
        """
        Actualiza parcialmente una plantilla de factura.
        """
        template = InvoiceTemplateSelector.get_by_id(
            kwargs["pk"],
        )

        serializer = self.get_serializer(
            template,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        dto = serializer.to_dto()

        try:
            updated_template = InvoiceTemplateService.update_template(
                template=template,
                dto=dto,
            )

            response_serializer = InvoiceTemplateRetrieveSerializer(
                updated_template,
            )

            return self.success_response(
                message="Plantilla actualizada correctamente.",
                code="INVOICE_TEMPLATE_UPDATED",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible actualizar la plantilla.",
            )

    @invoice_template_delete_schema
    def destroy(self, request, *args, **kwargs):
        """
        Realiza la desactivación lógica de una plantilla de factura.
        """
        template = InvoiceTemplateSelector.get_by_id(
            kwargs["pk"],
        )

        try:
            InvoiceTemplateService.deactivate_template(template)

            return self.success_response(
                message="Plantilla desactivada correctamente.",
                code="INVOICE_TEMPLATE_DEACTIVATED",
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible desactivar la plantilla.",
            )

    @invoice_template_restore_schema
    @action(
        detail=True,
        methods=["post"],
        url_path="restore",
    )
    def restore(self, request, pk=None):
        """
        Restaura una plantilla de factura previamente desactivada.
        """
        template = InvoiceTemplateSelector.get_by_id(pk)

        try:
            InvoiceTemplateService.restore_template(template)
            serializer = InvoiceTemplateRetrieveSerializer(template)

            return self.success_response(
                message="Plantilla restaurada correctamente.",
                code="INVOICE_TEMPLATE_RESTORED",
                data=serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible restaurar la plantilla.",
            )
