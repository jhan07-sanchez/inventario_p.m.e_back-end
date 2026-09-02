from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.core.helpers.boolean_parser import parse_bool
from apps.core.security import HasPermission
from apps.core.views.base_viewset import BaseViewSet
from apps.users.docs.user_role_docs import (
    user_role_create_schema,
    user_role_delete_schema,
    user_role_detail_schema,
    user_role_list_schema,
    user_role_partial_update_schema,
    user_role_restore_schema,
    user_role_update_schema,
)
from apps.users.models import UserRole
from apps.users.permissions import IsAuthenticatedAndActive
from apps.users.selectors.user_role_selector import UserRoleSelector
from apps.users.serializers.user_role_serializer import (
    UserRoleCreateSerializer,
    UserRoleDetailSerializer,
    UserRoleListSerializer,
    UserRoleUpdateSerializer,
)
from apps.users.services.user_role_service import UserRoleService


class UserRoleViewSet(BaseViewSet):
    """
    ViewSet encargado de administrar
    las asignaciones de roles a usuarios.
    """

    queryset = UserRole.objects.all()

    permission_classes = (IsAuthenticatedAndActive,)

    filter_backends = [SearchFilter, OrderingFilter]

    search_fields = [
        "user__username",
        "user__email",
        "role__role_name",
    ]

    ordering_fields = [
        "id_user_role",
        "user__username",
        "role__role_name",
        "is_active",
    ]

    ordering = ["id_user_role"]

    def get_permissions(self):
        """
        Retorna los permisos correspondientes según
        la acción ejecutada.
        """

        permission_classes = {
            "list": (
                IsAuthenticatedAndActive,
                HasPermission("user_roles.view"),
            ),
            "retrieve": (
                IsAuthenticatedAndActive,
                HasPermission("user_roles.view"),
            ),
            "create": (
                IsAuthenticatedAndActive,
                HasPermission("user_roles.create"),
            ),
            "update": (
                IsAuthenticatedAndActive,
                HasPermission("user_roles.update"),
            ),
            "partial_update": (
                IsAuthenticatedAndActive,
                HasPermission("user_roles.update"),
            ),
            "destroy": (
                IsAuthenticatedAndActive,
                HasPermission("user_roles.delete"),
            ),
            "restore": (
                IsAuthenticatedAndActive,
                HasPermission("user_roles.update"),
            ),
        }

        permissions = permission_classes.get(
            self.action,
            (IsAuthenticatedAndActive,),
        )

        return [permission() for permission in permissions]

    def get_queryset(self):
        """
        Retorna las asignaciones aplicando filtros.
        """
        return UserRoleSelector.filter_user_roles(
            user=self.request.query_params.get("user"),
            role=self.request.query_params.get("role"),
            is_active=parse_bool(self.request.query_params.get("is_active")),
        )

    def get_serializer_class(self):
        """
        Retorna el serializer correspondiente segun la accion.
        """

        serializer_classes = {
            "list": UserRoleListSerializer,
            "retrieve": UserRoleDetailSerializer,
            "create": UserRoleCreateSerializer,
            "update": UserRoleUpdateSerializer,
            "partial_update": UserRoleUpdateSerializer,
        }

        return serializer_classes.get(
            self.action,
            UserRoleDetailSerializer,
        )

    @user_role_list_schema
    def list(self, request, *args, **kwargs):
        """
        Lista todas las asignaciones de roles.
        """

        queryset = self.get_queryset()

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(
            queryset,
            many=True,
        )

        return self.success_response(
            data=serializer.data,
            message="Asignaciones de roles obtenidas correctamente.",
            status_code=status.HTTP_200_OK,
        )

    @user_role_detail_schema
    def retrieve(self, request, *args, **kwargs):
        """
        Obtiene el detalle de una asignacion de rol.
        """

        user_role = UserRoleSelector.get_by_id(
            kwargs["pk"],
        )

        serializer = self.get_serializer(
            user_role,
        )

        return self.success_response(
            data=serializer.data,
            message="Asignacion obtenida correctamente.",
            status_code=status.HTTP_200_OK,
        )

    @user_role_create_schema
    def create(self, request, *args, **kwargs):
        """
        Asignar un rol a un usuario.
        """

        serializer = self.get_serializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        user_role = UserRoleService.create_user_role(
            serializer.validated_data,
        )

        response_serializer = UserRoleDetailSerializer(
            user_role,
        )

        return self.success_response(
            data=response_serializer.data,
            message="Rol asignado al usuario correctamente.",
            status_code=status.HTTP_201_CREATED,
        )

    @user_role_update_schema
    def update(self, request, *args, **kwargs):
        """
        Actualiza completamente una asignacion de rol.
        """

        user_role = UserRoleSelector.get_by_id(
            kwargs["pk"],
        )

        serializer = self.get_serializer(
            user_role,
            data=request.data,
        )

        serializer.is_valid(raise_exception=True)

        user_role = UserRoleService.update_user_role(
            user_role=user_role,
            validated_data=serializer.validated_data,
        )

        responce_serializer = UserRoleDetailSerializer(
            user_role,
        )

        return self.success_response(
            data=responce_serializer.data,
            message="Asignacion actualizada correctamente",
            status_code=status.HTTP_200_OK,
        )

    @user_role_partial_update_schema
    def partial_update(self, request, *args, **kwargs):
        """
        actualiza parcialmente una asignacion de rol.
        """

        user_role = UserRoleSelector.get_by_id(
            kwargs["pk"],
        )

        serializer = self.get_serializer(
            user_role,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        user_role = UserRoleService.update_user_role(
            user_role=user_role,
            validated_data=serializer.validated_data,
        )

        responce_serializer = UserRoleDetailSerializer(
            user_role,
        )

        return self.success_response(
            data=responce_serializer.data,
            message="Asignacion actualizada correctamente.",
            status_code=status.HTTP_200_OK,
        )

    @user_role_delete_schema
    def destroy(self, request, *args, **kwargs):
        """
        Realiza el borrado logico de una asignacion de rol.
        """

        user_role = UserRoleSelector.get_by_id(
            kwargs["pk"],
        )

        UserRoleService.deactivate_user_role(
            user_role,
        )

        return self.success_response(
            message="Asignacion desactivada correctamente.",
            status_code=status.HTTP_200_OK,
        )

    @user_role_restore_schema
    @action(
        detail=True,
        methods=["post"],
        url_path="restore",
    )
    def restore(self, request, pk=None):
        """
        Restaura una asignacion previamente desactivada.
        """

        user_role = UserRoleSelector.get_by_id(
            pk,
        )

        UserRoleService.restore_user_role(
            user_role,
        )

        serializer = UserRoleDetailSerializer(
            user_role,
        )

        return self.success_response(
            data=serializer.data,
            message="Asignacion restaurada correctamente.",
            status_code=status.HTTP_200_OK,
        )
