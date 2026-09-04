from django.core.exceptions import ValidationError

from rest_framework import status
from rest_framework.decorators import action

from apps.core.security import HasPermission
from apps.core.views.base_viewset import BaseViewSet
from apps.products.models import Product
from apps.products.selectors.product_selector import ProductSelector
from apps.products.serializers.product_serializer import (
    ProductCreateSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    ProductUpdateSerializer,
)
from apps.products.docs.product_docs import (
    product_create_schema,
    product_delete_schema,
    product_detail_schema,
    product_list_schema,
    product_partial_update_schema,
    product_restore_schema,
    product_update_schema,
)
from apps.products.services.product_service import ProductService
from apps.users.permissions import IsAuthenticatedAndActive


class ProductViewSet(BaseViewSet):
    """
    ViewSet encargado de administrar los productos
    del sistema.
    """

    queryset = Product.objects.all()

    permission_classes = [IsAuthenticatedAndActive]

    def get_permissions(self):
        """
        Retorna los permisos requeridos según la acción.
        """

        permission_map = {
            "list": (
                IsAuthenticatedAndActive,
                HasPermission("products.view"),
            ),
            "retrieve": (
                IsAuthenticatedAndActive,
                HasPermission("products.view"),
            ),
            "create": (
                IsAuthenticatedAndActive,
                HasPermission("products.create"),
            ),
            "update": (
                IsAuthenticatedAndActive,
                HasPermission("products.update"),
            ),
            "partial_update": (
                IsAuthenticatedAndActive,
                HasPermission("products.update"),
            ),
            "destroy": (
                IsAuthenticatedAndActive,
                HasPermission("products.delete"),
            ),
            "restore": (
                IsAuthenticatedAndActive,
                HasPermission("products.update"),
            ),
        }

        classes = permission_map.get(
            self.action,
            (
                IsAuthenticatedAndActive,
                HasPermission("products.view"),
            ),
        )

        return [permission() for permission in classes]

    def get_queryset(self):
        """
        Retorna el queryset de productos.

        Las consultas son delegadas al ProductSelector.
        """

        return ProductSelector.get_products()

    def get_serializer_class(self):
        """
        Retorna el serializer correspondiente según
        la acción ejecutada.
        """

        if self.action == "list":
            return ProductListSerializer

        if self.action == "retrieve":
            return ProductDetailSerializer

        if self.action == "create":
            return ProductCreateSerializer

        if self.action in (
            "update",
            "partial_update",
        ):
            return ProductUpdateSerializer

        return ProductDetailSerializer

    @product_list_schema
    def list(self, request, *args, **kwargs):
        """
        Lista todos los productos.
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
            message="Productos obtenidos correctamente.",
            code="PRODUCTS_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @product_detail_schema
    def retrieve(self, request, *args, **kwargs):
        """
        Obtiene el detalle de un producto.
        """

        product = ProductSelector.get_by_id(
            kwargs["pk"],
        )

        serializer = self.get_serializer(
            product,
        )

        return self.success_response(
            message="Producto obtenido correctamente.",
            code="PRODUCT_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @product_create_schema
    def create(self, request, *args, **kwargs):
        """
        Crea un nuevo producto.
        """

        serializer = self.get_serializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        try:
            product = ProductService.create_product(
                serializer.validated_data,
            )

            response_serializer = ProductDetailSerializer(
                product,
            )

            return self.success_response(
                message="Producto creado correctamente.",
                code="PRODUCT_CREATED",
                data=response_serializer.data,
                status_code=status.HTTP_201_CREATED,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible crear el producto.",
            )

    @product_update_schema
    def update(self, request, *args, **kwargs):
        """
        Actualiza completamente un producto.
        """

        product = ProductSelector.get_by_id(
            kwargs["pk"],
        )

        serializer = self.get_serializer(
            product,
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        try:
            product = ProductService.update_product(
                product,
                serializer.validated_data,
            )

            response_serializer = ProductDetailSerializer(
                product,
            )

            return self.success_response(
                message="Producto actualizado correctamente.",
                code="PRODUCT_UPDATED",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible actualizar el producto.",
            )

    @product_partial_update_schema
    def partial_update(self, request, *args, **kwargs):
        """
        Actualiza parcialmente un producto.
        """

        product = ProductSelector.get_by_id(
            kwargs["pk"],
        )

        serializer = self.get_serializer(
            product,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        try:
            product = ProductService.update_product(
                product,
                serializer.validated_data,
            )

            response_serializer = ProductDetailSerializer(
                product,
            )

            return self.success_response(
                message="Producto actualizado correctamente.",
                code="PRODUCT_PARTIAL_UPDATED",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible actualizar el producto.",
            )

    @product_delete_schema
    def destroy(self, request, *args, **kwargs):
        """
        Realiza la desactivación lógica de un producto.
        """

        product = ProductSelector.get_by_id(
            kwargs["pk"],
        )

        try:
            ProductService.deactivate_product(
                product,
            )

            return self.success_response(
                message="Producto desactivado correctamente.",
                code="PRODUCT_DELETED",
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible desactivar el producto.",
            )

    @product_restore_schema
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
        Restaura un producto previamente desactivado.
        """

        product = ProductSelector.get_by_id(
            pk,
        )

        try:
            ProductService.restore_product(
                product,
            )

            serializer = ProductDetailSerializer(
                product,
            )

            return self.success_response(
                message="Producto restaurado correctamente.",
                code="PRODUCT_RESTORED",
                data=serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible restaurar el producto.",
            )
