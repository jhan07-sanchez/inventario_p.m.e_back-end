from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny  # <--- Importante para acceso libre en desarrollo

from apps.core.security import HasPermission
from apps.core.views.base_viewset import BaseViewSet
from apps.users.docs.user_docs import (
    user_create_schema,
    user_delete_schema,
    user_detail_schema,
    user_list_schema,
    user_partial_update_schema,
    user_restore_schema,
    user_update_schema,
)
from apps.users.models import User
from apps.users.permissions import IsAuthenticatedAndActive
from apps.users.selectors.user_selector import UserSelector
from apps.users.serializers.user_serializer import (
    UserCreateSerializer,
    UserDetailSerializer,
    UserListSerializer,
    UserUpdateSerializer,
)
from apps.users.services.user_service import UserService


class UserViewSet(BaseViewSet):
    """
    ViewSet encargado de administrar los usuarios del sistema.

    Responsabilidades:
    -Listar usuarios.
    -Obtener un usuario.
    -Crear usuarios.
    -Actualizar usuarios.
    -Eliminar usuarios.
    """

    queryset = User.objects.all()

    serializer_class = UserDetailSerializer

    permission_classes = [
        IsAuthenticatedAndActive,
    ]

    def get_queryset(self):
        """
        Obtiene el queryset de usuarios desde la capa
        de Selectors.
        """
        return UserSelector.get_users()

    def get_serializer_class(self):
        """
        Retorna el serializer correspondiente segun la accion
        ejecutada por el ViewSet
        """

        serializer_classes = {
            "list": UserListSerializer,
            "retrieve": UserDetailSerializer,
            "create": UserCreateSerializer,
            "update": UserUpdateSerializer,
            "partial_update": UserUpdateSerializer,
        }

        return serializer_classes.get(
            self.action,
            UserDetailSerializer,
        )

    def get_permissions(self):
        """
        Retorna los permisos correspondiente segun
        la accion ejecutada
        """

        permission_classes = {
            "list": (
                AllowAny,  # <--- Permitimos listar públicamente para que DataTables cargue sin token por ahora
            ),
            "retrieve": (
                IsAuthenticatedAndActive,
                HasPermission("users.view"),
            ),
            "create": (
                IsAuthenticatedAndActive,
                HasPermission("users.create"),
            ),
            "update": (
                IsAuthenticatedAndActive,
                HasPermission("users.update"),
            ),
            "partial_update": (
                IsAuthenticatedAndActive,
                HasPermission("users.update"),
            ),
            "destroy": (
                IsAuthenticatedAndActive,
                HasPermission("users.delete"),
            ),
            "restore": (
                IsAuthenticatedAndActive,
                HasPermission("users.update"),
            ),
        }

        permissions = permission_classes.get(
            self.action,
            (IsAuthenticatedAndActive,),
        )

        return [permission() for permission in permissions]

    @user_list_schema
    def list(self, request, *args, **kwargs):
        """
        Lista todos los usuarios del sistema.
        """
        queryset = self.filter_queryset(self.get_queryset())

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
            code="USERS_FETCHED",
            message="Usuarios obtenidos correctamente.",
        )

    @user_detail_schema
    def retrieve(self, request, *args, **kwargs):
        """
        Obtiene el detalle de un usuario.
        """

        user = self.get_object()

        serializer = self.get_serializer(user)

        return self.success_response(
            data=serializer.data,
            code="USER_FETCHED",
            message="Usuarios obtenidos correctamente.",
        )

    @user_create_schema
    def create(self, request, *args, **kwargs):
        """
        Crea un nuevo usuario.
        """

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = UserService.create_user(serializer.validated_data)

        response_serializer = UserDetailSerializer(user)

        return self.success_response(
            data=response_serializer.data,
            code="USER_CREATED",
            message="Usuario creado correctamente.",
            status_code=status.HTTP_201_CREATED,
        )

    @user_update_schema
    def update(self, request, *args, **kwargs):
        """
        Actualiza completamente un usuario.
        """

        user = self.get_object()

        serializer = self.get_serializer(
            user,
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        update_user = UserService.update_user(
            user=user,
            validated_data=serializer.validated_data,
        )

        response_serializer = UserDetailSerializer(update_user)

        return self.success_response(
            data=response_serializer.data,
            code="USER_UPDATED",
            message="Usuario actualizado correctamente",
        )

    @user_partial_update_schema
    def partial_update(self, request, *args, **kwargs):
        """
        Actualizar parcialmente un usuario.
        """

        user = self.get_object()

        serializer = self.get_serializer(
            user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        update_user = UserService.update_user(
            user=user,
            validated_data=serializer.validated_data,
        )

        response_serializer = UserDetailSerializer(update_user)

        return self.success_response(
            data=response_serializer.data,
            code="USER_PARTIAL_UPDATED",
            message="Usuario actualizado correctamente.",
        )

    @user_delete_schema
    def destroy(self, request, *args, **kwargs):
        """
        Realiza el borrado logico de un usuario.
        """

        user = self.get_object()
        UserService.deactivate_user(user)

        return self.success_response(
            code="USER_DELETED",
            message="Usuario desactivado correctamente.",
            data=None,
        )

    @user_restore_schema
    @action(
        detail=True,
        methods=["post"],
        url_path="restore",
    )
    def restore(self, request, pk=None):
        """
        Restaura un usuario previamente desactivado.
        """

        user = UserSelector.get_by_id(pk)

        try:
            UserService.restore_user(user)

            serializer = UserDetailSerializer(user)

            return self.success_response(
                message="Usuario restaurado correctamente.",
                code="USER_RESTORED",
                data=serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible restaurar el usuario.",
            )