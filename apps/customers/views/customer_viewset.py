from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.core.security import HasPermission
from apps.core.views.base_viewset import BaseViewSet
from apps.customers.models import Customer
from apps.customers.selectors.customer_selector import CustomerSelector
from apps.customers.serializers.customer_serializer import (
    CustomerCreateSerializer,
    CustomerDetailSerializer,
    CustomerListSerializer,
    CustomerUpdateSerializer,
)
from apps.customers.services.customer_service import CustomerService
from apps.users.permissions import IsAuthenticatedAndActive
from apps.customers.docs.customer_docs import (
    customer_create_schema,
    customer_delete_schema,
    customer_detail_schema,
    customer_list_schema,
    customer_partial_update_schema,
    customer_restore_schema,
    customer_update_schema,
)




class CustomerViewSet(BaseViewSet):
    """
    ViewSet encargado de administrar los clientes del sistema.
    """

    queryset = Customer.objects.all()

    permission_classes = [IsAuthenticatedAndActive]

    filter_backends = [SearchFilter, OrderingFilter]

    search_fields = [
        "document_number",
        "first_name",
        "last_name",
        "business_name",
        "email",
    ]

    ordering_fields = [
        "id_customer",
        "first_name",
        "last_name",
        "business_name",
        "email",
        "is_active",
    ]

    ordering = ["id_customer"]

    def get_permissions(self):
        """
        Retorna los permisos requeridos según la acción.
        """

        permission_map = {
            "list": (
                IsAuthenticatedAndActive,
                HasPermission("customers.view"),
            ),
            "retrieve": (
                IsAuthenticatedAndActive,
                HasPermission("customers.view"),
            ),
            "create": (
                IsAuthenticatedAndActive,
                HasPermission("customers.create"),
            ),
            "update": (
                IsAuthenticatedAndActive,
                HasPermission("customers.update"),
            ),
            "partial_update": (
                IsAuthenticatedAndActive,
                HasPermission("customers.update"),
            ),
            "destroy": (
                IsAuthenticatedAndActive,
                HasPermission("customers.delete"),
            ),
            "restore": (
                IsAuthenticatedAndActive,
                HasPermission("customers.update"),
            ),
        }

        classes = permission_map.get(
            self.action,
            (
                IsAuthenticatedAndActive,
                HasPermission("customers.view"),
            ),
        )

        return [permission() for permission in classes]

    def get_queryset(self):
        """
        Retorna el queryset de clientes.

        Las consultas son delegadas al CustomerSelector.
        """

        return CustomerSelector.get_customers()

    def get_serializer_class(self):
        """
        Retorna el serializer correspondiente
        según la acción ejecutada.
        """

        if self.action == "list":
            return CustomerListSerializer

        if self.action == "retrieve":
            return CustomerDetailSerializer

        if self.action == "create":
            return CustomerCreateSerializer

        if self.action in (
            "update",
            "partial_update",
        ):
            return CustomerUpdateSerializer

        return CustomerDetailSerializer

    @customer_list_schema
    def list(self, request, *args, **kwargs):
        """
        Lista todos los clientes.
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
            message="Clientes obtenidos correctamente.",
            code="CUSTOMERS_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @customer_detail_schema
    def retrieve(self, request, *args, **kwargs):
        """
        Obtiene el detalle de un cliente.
        """

        customer = CustomerSelector.get_customer_by_id(
            kwargs["pk"],
        )

        serializer = self.get_serializer(
            customer,
        )

        return self.success_response(
            message="Cliente obtenido correctamente.",
            code="CUSTOMER_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @customer_create_schema
    def create(self, request, *args, **kwargs):
        """
        Crea un nuevo cliente.
        """

        serializer = self.get_serializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        try:
            customer = CustomerService.create_customer(
                serializer.validated_data,
            )

            response_serializer = CustomerDetailSerializer(
                customer,
            )

            return self.success_response(
                message="Cliente creado correctamente.",
                code="CUSTOMER_CREATED",
                data=response_serializer.data,
                status_code=status.HTTP_201_CREATED,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible crear el cliente.",
            )

    @customer_update_schema
    def update(self, request, *args, **kwargs):
        """
        Actualiza completamente un cliente.
        """

        customer = CustomerSelector.get_customer_by_id(
            kwargs["pk"],
        )

        serializer = self.get_serializer(
            customer,
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        try:
            customer = CustomerService.update_customer(
                customer,
                serializer.validated_data,
            )

            response_serializer = CustomerDetailSerializer(
                customer,
            )

            return self.success_response(
                message="Cliente actualizado correctamente.",
                code="CUSTOMER_UPDATED",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible actualizar el cliente.",
            )

    @customer_partial_update_schema
    def partial_update(self, request, *args, **kwargs):
        """
        Actualiza parcialmente un cliente.
        """

        customer = CustomerSelector.get_customer_by_id(
            kwargs["pk"],
        )

        serializer = self.get_serializer(
            customer,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        try:
            customer = CustomerService.update_customer(
                customer,
                serializer.validated_data,
            )

            response_serializer = CustomerDetailSerializer(
                customer,
            )

            return self.success_response(
                message="Cliente actualizado correctamente.",
                code="CUSTOMER_PARTIAL_UPDATED",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible actualizar el cliente.",
            )

    @customer_delete_schema
    def destroy(self, request, *args, **kwargs):
        """
        Realiza el borrado lógico de un cliente.
        """

        customer = CustomerSelector.get_customer_by_id(
            kwargs["pk"],
        )

        try:
            CustomerService.deactivate_customer(
                customer,
            )

            return self.success_response(
                message="Cliente desactivado correctamente.",
                code="CUSTOMER_DELETED",
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible desactivar el cliente.",
            )

    @customer_restore_schema
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
        Restaura un cliente previamente desactivado.
        """

        customer = CustomerSelector.get_customer_by_id(
            pk,
        )

        try:
            CustomerService.restore_customer(
                customer,
            )

            serializer = CustomerDetailSerializer(
                customer,
            )

            return self.success_response(
                message="Cliente restaurado correctamente.",
                code="CUSTOMER_RESTORED",
                data=serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible restaurar el cliente.",
            )
