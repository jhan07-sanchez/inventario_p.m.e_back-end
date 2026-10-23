from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.configuration.docs import (
    global_parameter_create_schema,
    global_parameter_delete_schema,
    global_parameter_detail_schema,
    global_parameter_list_schema,
    global_parameter_partial_update_schema,
    global_parameter_restore_schema,
    global_parameter_update_schema,
)
from apps.configuration.models import GlobalParameter
from apps.configuration.selectors import GlobalParameterSelector
from apps.configuration.serializers import (
    GlobalParameterCreateSerializer,
    GlobalParameterSerializer,
    GlobalParameterUpdateSerializer,
)
from apps.configuration.services import GlobalParameterService
from apps.core.security import HasPermission
from apps.core.views.base_viewset import BaseViewSet
from apps.users.permissions import IsAuthenticatedAndActive


class GlobalParameterViewSet(BaseViewSet):
    """
    ViewSet encargado de administrar los parámetros globales del sistema.
    """

    queryset = GlobalParameter.objects.all()
    permission_classes = [IsAuthenticatedAndActive]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["key", "description"]
    ordering_fields = ["key", "created_at"]

    def get_permissions(self):
        """
        Retorna los permisos requeridos según la acción.
        """
        permission_map = {
            "list": (IsAuthenticatedAndActive, HasPermission("settings.view")),
            "retrieve": (IsAuthenticatedAndActive, HasPermission("settings.view")),
            "create": (IsAuthenticatedAndActive, HasPermission("settings.update")),
            "update": (IsAuthenticatedAndActive, HasPermission("settings.update")),
            "partial_update": (
                IsAuthenticatedAndActive,
                HasPermission("settings.update"),
            ),
            "destroy": (IsAuthenticatedAndActive, HasPermission("settings.update")),
            "restore": (IsAuthenticatedAndActive, HasPermission("settings.update")),
        }

        classes = permission_map.get(
            self.action,
            (IsAuthenticatedAndActive, HasPermission("settings.view")),
        )
        return [permission() for permission in classes]

    def get_queryset(self):
        """
        Retorna el queryset de parámetros.
        """
        return GlobalParameterSelector.get_parameters()

    def get_serializer_class(self):
        """
        Retorna el serializer correspondiente según la acción.
        """
        if self.action == "create":
            return GlobalParameterCreateSerializer
        if self.action in ("update", "partial_update"):
            return GlobalParameterUpdateSerializer
        return GlobalParameterSerializer

    @global_parameter_list_schema
    def list(self, request, *args, **kwargs):
        """
        Lista todos los parámetros globales.
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return self.success_response(
            message="Parámetros obtenidos correctamente.",
            code="GLOBAL_PARAMETERS_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @global_parameter_detail_schema
    def retrieve(self, request, *args, **kwargs):
        """
        Obtiene el detalle de un parámetro por ID.
        """
        param = GlobalParameterSelector.get_parameter_by_id(kwargs["pk"])
        serializer = self.get_serializer(param)
        return self.success_response(
            message="Parámetro obtenido correctamente.",
            code="GLOBAL_PARAMETER_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @global_parameter_create_schema
    def create(self, request, *args, **kwargs):
        """
        Crea un nuevo parámetro global.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            param = GlobalParameterService.create_parameter(serializer.to_dto(), user=request.user)
            response_serializer = GlobalParameterSerializer(param)
            return self.success_response(
                message="Parámetro creado correctamente.",
                code="GLOBAL_PARAMETER_CREATED",
                data=response_serializer.data,
                status_code=status.HTTP_201_CREATED,
            )
        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible crear el parámetro.",
            )

    @global_parameter_update_schema
    def update(self, request, *args, **kwargs):
        """
        Actualiza completamente un parámetro.
        """
        param = GlobalParameterSelector.get_parameter_by_id(kwargs["pk"])
        serializer = self.get_serializer(param, data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            param = GlobalParameterService.update_parameter(param, serializer.to_dto(), user=request.user)
            response_serializer = GlobalParameterSerializer(param)
            return self.success_response(
                message="Parámetro actualizado correctamente.",
                code="GLOBAL_PARAMETER_UPDATED",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK,
            )
        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible actualizar el parámetro.",
            )

    @global_parameter_partial_update_schema
    def partial_update(self, request, *args, **kwargs):
        """
        Actualiza parcialmente un parámetro.
        """
        param = GlobalParameterSelector.get_parameter_by_id(kwargs["pk"])
        serializer = self.get_serializer(param, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            param = GlobalParameterService.update_parameter(param, serializer.to_dto(), user=request.user)
            response_serializer = GlobalParameterSerializer(param)
            return self.success_response(
                message="Parámetro actualizado parcialmente.",
                code="GLOBAL_PARAMETER_PARTIAL_UPDATED",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK,
            )
        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible actualizar el parámetro.",
            )

    @global_parameter_delete_schema
    def destroy(self, request, *args, **kwargs):
        """
        Realiza el borrado lógico de un parámetro.
        """
        param = GlobalParameterSelector.get_parameter_by_id(kwargs["pk"])

        try:
            GlobalParameterService.deactivate_parameter(param)
            return self.success_response(
                message="Parámetro desactivado correctamente.",
                code="GLOBAL_PARAMETER_DELETED",
                status_code=status.HTTP_200_OK,
            )
        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible desactivar el parámetro.",
            )

    @global_parameter_restore_schema
    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        """
        Restaura un parámetro previamente desactivado.
        """
        param = GlobalParameterSelector.get_parameter_by_id(pk, include_deleted=True)

        try:
            GlobalParameterService.restore_parameter(param)
            serializer = GlobalParameterSerializer(param)
            return self.success_response(
                message="Parámetro restaurado correctamente.",
                code="GLOBAL_PARAMETER_RESTORED",
                data=serializer.data,
                status_code=status.HTTP_200_OK,
            )
        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible restaurar el parámetro.",
            )
