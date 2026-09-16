from django.core.exceptions import ValidationError

from rest_framework import status
from rest_framework.decorators import action

from rest_framework.filters import SearchFilter, OrderingFilter

from apps.core.security import HasPermission
from apps.core.views.base_viewset import BaseViewSet
from apps.suppliers.models import Supplier
from apps.suppliers.selectors.supplier_selector import SupplierSelector
from apps.suppliers.serializers.supplier_serializer import (
    SupplierCreateSerializer,
    SupplierDetailSerializer,
    SupplierListSerializer,
    SupplierUpdateSerializer,
)
from apps.suppliers.docs.supplier_docs import (
    supplier_create_schema,
    supplier_delete_schema,
    supplier_detail_schema,
    supplier_list_schema,
    supplier_partial_update_schema,
    supplier_restore_schema,
    supplier_update_schema,
)
from apps.suppliers.services.supplier_service import SupplierService
from apps.users.permissions import IsAuthenticatedAndActive


class SupplierViewSet(BaseViewSet):
    """
    ViewSet encargado de administrar los proveedores
    del sistema.
    """

    queryset = Supplier.objects.all()

    permission_classes = [IsAuthenticatedAndActive]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "document_number", "contact_name", "email", "phone"]

    def get_permissions(self):
        """
        Retorna los permisos requeridos según la acción.
        """

        permission_map = {
            "list": (
                IsAuthenticatedAndActive,
                HasPermission("suppliers.view"),
            ),
            "retrieve": (
                IsAuthenticatedAndActive,
                HasPermission("suppliers.view"),
            ),
            "create": (
                IsAuthenticatedAndActive,
                HasPermission("suppliers.create"),
            ),
            "update": (
                IsAuthenticatedAndActive,
                HasPermission("suppliers.update"),
            ),
            "partial_update": (
                IsAuthenticatedAndActive,
                HasPermission("suppliers.update"),
            ),
            "destroy": (
                IsAuthenticatedAndActive,
                HasPermission("suppliers.delete"),
            ),
            "restore": (
                IsAuthenticatedAndActive,
                HasPermission("suppliers.update"),
            ),
        }

        classes = permission_map.get(
            self.action,
            (
                IsAuthenticatedAndActive,
                HasPermission("suppliers.view"),
            ),
        )

        return [permission() for permission in classes]

    def get_queryset(self):
        """
        Retorna el queryset de proveedores.

        Las consultas son delegadas al SupplierSelector.
        """

        return SupplierSelector.get_suppliers()

    def get_serializer_class(self):
        """
        Retorna el serializer correspondiente según
        la acción ejecutada.
        """

        if self.action == "list":
            return SupplierListSerializer

        if self.action == "retrieve":
            return SupplierDetailSerializer

        if self.action == "create":
            return SupplierCreateSerializer

        if self.action in (
            "update",
            "partial_update",
        ):
            return SupplierUpdateSerializer

        return SupplierDetailSerializer

    @supplier_list_schema
    def list(self, request, *args, **kwargs):
        """
        Lista todos los proveedores.
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
            message="Proveedores obtenidos correctamente.",
            code="SUPPLIERS_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @supplier_detail_schema
    def retrieve(self, request, *args, **kwargs):
        """
        Obtiene el detalle de un proveedor.
        """

        supplier = SupplierSelector.get_supplier_by_id(
            kwargs["pk"],
        )

        serializer = self.get_serializer(
            supplier,
        )

        return self.success_response(
            message="Proveedor obtenido correctamente.",
            code="SUPPLIER_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @supplier_create_schema
    def create(self, request, *args, **kwargs):
        """
        Crea un nuevo proveedor.
        """

        serializer = self.get_serializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        try:
            supplier = SupplierService.create_supplier(
                serializer.validated_data,
            )

            response_serializer = SupplierDetailSerializer(
                supplier,
            )

            return self.success_response(
                message="Proveedor creado correctamente.",
                code="SUPPLIER_CREATED",
                data=response_serializer.data,
                status_code=status.HTTP_201_CREATED,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible crear el proveedor.",
            )

    @supplier_update_schema
    def update(self, request, *args, **kwargs):
        """
        Actualiza completamente un proveedor.
        """

        supplier = SupplierSelector.get_supplier_by_id(
            kwargs["pk"],
        )

        serializer = self.get_serializer(
            supplier,
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        try:
            supplier = SupplierService.update_supplier(
                supplier,
                serializer.validated_data,
            )

            response_serializer = SupplierDetailSerializer(
                supplier,
            )

            return self.success_response(
                message="Proveedor actualizado correctamente.",
                code="SUPPLIER_UPDATED",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible actualizar el proveedor.",
            )

    @supplier_partial_update_schema
    def partial_update(self, request, *args, **kwargs):
        """
        Actualiza parcialmente un proveedor.
        """

        supplier = SupplierSelector.get_supplier_by_id(
            kwargs["pk"],
        )

        serializer = self.get_serializer(
            supplier,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        try:
            supplier = SupplierService.update_supplier(
                supplier,
                serializer.validated_data,
            )

            response_serializer = SupplierDetailSerializer(
                supplier,
            )

            return self.success_response(
                message="Proveedor actualizado correctamente.",
                code="SUPPLIER_PARTIAL_UPDATED",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible actualizar el proveedor.",
            )

    @supplier_delete_schema
    def destroy(self, request, *args, **kwargs):
        """
        Realiza el borrado lógico de un proveedor.
        """

        supplier = SupplierSelector.get_supplier_by_id(
            kwargs["pk"],
        )

        try:
            SupplierService.deactivate_supplier(
                supplier,
            )

            return self.success_response(
                message="Proveedor desactivado correctamente.",
                code="SUPPLIER_DELETED",
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible desactivar el proveedor.",
            )

    @supplier_restore_schema
    @action(
        detail=True,
        methods=["post"],
        url_path="restore",
    )
    def restore(
        self,
        request,
        pk=None,
    ):
        """
        Restaura un proveedor previamente desactivado.
        """

        supplier = SupplierSelector.get_supplier_by_id(
            pk,
        )

        try:
            SupplierService.restore_supplier(
                supplier,
            )

            serializer = SupplierDetailSerializer(
                supplier,
            )

            return self.success_response(
                message="Proveedor restaurado correctamente.",
                code="SUPPLIER_RESTORED",
                data=serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible restaurar el proveedor.",
            )
