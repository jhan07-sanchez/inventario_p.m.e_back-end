from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import action

from apps.categories.models import Category
from apps.categories.selectors.category_selector import CategorySelector
from apps.categories.serializers.category_serializer import (
    CategoryCreateSerializer,
    CategoryDetailSerializer,
    CategoryListSerializer,
    CategoryUpdateSerializer,
)
from apps.categories.docs.category_docs import (
    category_create_schema,
    category_delete_schema,
    category_detail_schema,
    category_list_schema,
    category_partial_update_schema,
    category_restore_schema,
    category_update_schema,
)
from apps.categories.services.category_service import CategoryService
from apps.core.security import HasPermission
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.core.views.base_viewset import BaseViewSet
from apps.users.permissions import IsAuthenticatedAndActive


class CategoryViewSet(BaseViewSet):
    """
    ViewSet encargado de administrar las categorías
    del sistema.
    """

    queryset = Category.objects.all()

    permission_classes = [IsAuthenticatedAndActive]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "description"]

    def get_permissions(self):
        """
        Retorna los permisos requeridos según la acción.
        """

        permission_map = {
            "list": (
                IsAuthenticatedAndActive,
                HasPermission("categories.view"),
            ),
            "retrieve": (
                IsAuthenticatedAndActive,
                HasPermission("categories.view"),
            ),
            "create": (
                IsAuthenticatedAndActive,
                HasPermission("categories.create"),
            ),
            "update": (
                IsAuthenticatedAndActive,
                HasPermission("categories.update"),
            ),
            "partial_update": (
                IsAuthenticatedAndActive,
                HasPermission("categories.update"),
            ),
            "destroy": (
                IsAuthenticatedAndActive,
                HasPermission("categories.delete"),
            ),
            "restore": (
                IsAuthenticatedAndActive,
                HasPermission("categories.update"),
            ),
        }

        classes = permission_map.get(
            self.action,
            (
                IsAuthenticatedAndActive,
                HasPermission("categories.view"),
            ),
        )

        return [permission() for permission in classes]

    def get_queryset(self):
        """
        Retorna el queryset de categorías.

        Las consultas son delegadas al CategorySelector.
        """

        return CategorySelector.get_categories()

    def get_serializer_class(self):
        """
        Retorna el serializer correspondiente
        según la acción ejecutada.
        """

        if self.action == "list":
            return CategoryListSerializer

        if self.action == "retrieve":
            return CategoryDetailSerializer

        if self.action == "create":
            return CategoryCreateSerializer

        if self.action in (
            "update",
            "partial_update",
        ):
            return CategoryUpdateSerializer

        return CategoryDetailSerializer

    @category_list_schema
    def list(self, request, *args, **kwargs):
        """
        Lista todas las categorías.
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
            message="Categorías obtenidas correctamente.",
            code="CATEGORIES_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @category_detail_schema
    def retrieve(self, request, *args, **kwargs):
        """
        Obtiene el detalle de una categoría.
        """

        category = CategorySelector.get_category_by_id(
            kwargs["pk"],
        )

        serializer = self.get_serializer(
            category,
        )

        return self.success_response(
            message="Categoría obtenida correctamente.",
            code="CATEGORY_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @category_create_schema
    def create(self, request, *args, **kwargs):
        """
        Crea una nueva categoría.
        """

        serializer = self.get_serializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        try:
            category = CategoryService.create_category(
                serializer.validated_data,
            )

            response_serializer = CategoryDetailSerializer(
                category,
            )

            return self.success_response(
                message="Categoría creada correctamente.",
                code="CATEGORY_CREATED",
                data=response_serializer.data,
                status_code=status.HTTP_201_CREATED,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible crear la categoría.",
            )

    @category_update_schema
    def update(self, request, *args, **kwargs):
        """
        Actualiza completamente una categoría.
        """

        category = CategorySelector.get_category_by_id(
            kwargs["pk"],
        )

        serializer = self.get_serializer(
            category,
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        try:
            category = CategoryService.update_category(
                category,
                serializer.validated_data,
            )

            response_serializer = CategoryDetailSerializer(
                category,
            )

            return self.success_response(
                message="Categoría actualizada correctamente.",
                code="CATEGORY_UPDATED",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible actualizar la categoría.",
            )

    @category_partial_update_schema
    def partial_update(self, request, *args, **kwargs):
        """
        Actualiza parcialmente una categoría.
        """

        category = CategorySelector.get_category_by_id(
            kwargs["pk"],
        )

        serializer = self.get_serializer(
            category,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        try:
            category = CategoryService.update_category(
                category,
                serializer.validated_data,
            )

            response_serializer = CategoryDetailSerializer(
                category,
            )

            return self.success_response(
                message="Categoría actualizada parcialmente.",
                code="CATEGORY_PARTIAL_UPDATED",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible actualizar la categoría.",
            )

    @category_delete_schema
    def destroy(self, request, *args, **kwargs):
        """
        Realiza el borrado lógico de una categoría.
        """

        category = CategorySelector.get_category_by_id(
            kwargs["pk"],
        )

        try:
            CategoryService.deactivate_category(
                category,
            )

            return self.success_response(
                message="Categoría desactivada correctamente.",
                code="CATEGORY_DELETED",
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible desactivar la categoría.",
            )

    @category_restore_schema
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
        Restaura una categoría previamente desactivada.
        """

        category = CategorySelector.get_category_by_id(
            pk,
        )

        try:
            CategoryService.restore_category(
                category,
            )

            serializer = CategoryDetailSerializer(
                category,
            )

            return self.success_response(
                message="Categoría restaurada correctamente.",
                code="CATEGORY_RESTORED",
                data=serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible restaurar la categoría.",
            )
