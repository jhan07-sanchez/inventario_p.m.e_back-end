from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.core.security import HasPermission
from apps.core.views.base_viewset import BaseViewSet
from apps.users.docs.role_docs import (
    role_create_schema,
    role_delete_schema,
    role_detail_schema,
    role_list_schema,
    role_partial_update_schema,
    role_restore_schema,
    role_update_schema,
)
from apps.users.models import Role
from apps.users.permissions import IsAuthenticatedAndActive
from apps.users.selectors.role_selector import RoleSelector
from apps.users.serializers.role_serializer import (
    RoleCreateSerializer,
    RoleDetailSerializer,
    RoleListSerializer,
    RoleUpdateSerializer,
)
from apps.users.services.role_service import RoleService


class RoleViewSet(BaseViewSet):
    """
    ViewSet encargado de administrar los roles del sistema.
    """

    queryset = Role.objects.all()

    permission_classes = [IsAuthenticatedAndActive]

    filter_backends = [SearchFilter, OrderingFilter]

    search_fields = [
        "role_name",
        "role_description",
    ]

    ordering_fields = [
        "id_role",
        "role_name",
        "role_description",
        "is_active",
    ]

    ordering = ["role_name"]

    def get_permissions(self):
        permission_map = {
            "list": (IsAuthenticatedAndActive, HasPermission("roles.view")),
            "retrieve": (IsAuthenticatedAndActive, HasPermission("roles.view")),
            "create": (IsAuthenticatedAndActive, HasPermission("roles.create")),
            "update": (IsAuthenticatedAndActive, HasPermission("roles.update")),
            "partial_update": (
                IsAuthenticatedAndActive,
                HasPermission("roles.update"),
            ),
            "destroy": (IsAuthenticatedAndActive, HasPermission("roles.delete")),
            "restore": (IsAuthenticatedAndActive, HasPermission("roles.update")),
        }
        classes = permission_map.get(
            self.action,
            (IsAuthenticatedAndActive, HasPermission("roles.view")),
        )
        return [permission() for permission in classes]

    def get_queryset(self):
        """
        Retorna el queryset de roles.

        Todas las consultas son delegadas al RoleSelector.
        """

        return RoleSelector.get_roles()

    def get_serializer_class(self):
        """
        Retorna el serializer correspondiente segun la accion.
        """

        if self.action == "list":
            return RoleListSerializer

        if self.action == "retrieve":
            return RoleDetailSerializer

        if self.action == "create":
            return RoleCreateSerializer

        if self.action in (
            "update",
            "partial_update",
        ):
            return RoleUpdateSerializer

        return RoleDetailSerializer

    @role_list_schema
    def list(self, request, *args, **kwargs):
        """
        Lista todos los roles del sistema.
        """

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)

        return self.success_response(
            message="Roles obtenidos correctamente.",
            code="ROLES_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @role_detail_schema
    def retrieve(self, request, *args, **kwargs):
        """
        Obtiene el detalle de un rol.
        """

        role = RoleSelector.get_role_by_id(kwargs["pk"])

        serializer = self.get_serializer(role)

        return self.success_response(
            message="Rol obtenido correctamente",
            code="ROLE_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @role_create_schema
    def create(self, request, *args, **kwargs):
        """
        Crea un nuevo rol.
        """

        serializer = self.get_serializer(
            data=request.data,
        )

        serializer.is_valid(raise_exception=True)

        try:
            role = RoleService.create_role(serializer.validated_data)

            response_serializer = RoleDetailSerializer(role)

            return self.success_response(
                message="Rol creado correctamente.",
                code="ROLE_CREATED",
                data=response_serializer.data,
                status_code=status.HTTP_201_CREATED,
            )
        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible crear el rol.",
            )

    @role_update_schema
    def update(self, request, *args, **kwargs):
        """
        Actualiza completamente un rol.
        """

        role = RoleSelector.get_role_by_id(kwargs["pk"])

        serializer = self.get_serializer(
            role,
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        try:
            role = RoleService.update_role(role, serializer.validated_data)

            response_serializer = RoleDetailSerializer(role)

            return self.success_response(
                message="Rol actualizado correctamente.",
                code="ROLE_UPDATED",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible actualizar el rol.",
            )

    @role_partial_update_schema
    def partial_update(self, request, *args, **kwargs):
        """
        Actualizar parcialmente un rol.
        """

        role = RoleSelector.get_role_by_id(kwargs["pk"])

        serializer = self.get_serializer(
            role,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        try:
            role = RoleService.update_role(role, serializer.validated_data)

            response_serializer = RoleDetailSerializer(role)

            return self.success_response(
                message="Rol actualizado correctamente.",
                code="ROLE_PARTIAL_UPDATED",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible actualizar el rol.",
            )

    @role_delete_schema
    def destroy(self, request, *args, **kwargs):
        """
        Realiza el borrado logico de un rol.
        """

        role = RoleSelector.get_role_by_id(kwargs["pk"])

        try:
            RoleService.deactivate_role(role)

            return self.success_response(
                message="Rol desactivado correctamente.",
                code="ROLE_DELETED",
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible desactivar el rol.",
            )

    @role_restore_schema
    @action(
        detail=True,
        methods=["post"],
        url_path="restore",
    )
    def restore(self, request, pk=None):
        """
        Restaura un rol previamente desactivado.
        """

        role = RoleSelector.get_role_by_id(pk)

        try:
            RoleService.restore_role(role)

            serializer = RoleDetailSerializer(role)

            return self.success_response(
                message="Rol restaurado correctamente.",
                code="ROLE_RESTORED",
                data=serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible restaurar el rol.",
            )
