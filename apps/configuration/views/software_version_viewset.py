from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.configuration.docs import (
    software_version_changelog_add_schema,
    software_version_check_updates_schema,
    software_version_create_schema,
    software_version_delete_changelog_schema,
    software_version_destroy_schema,
    software_version_detail_schema,
    software_version_history_schema,
    software_version_latest_schema,
    software_version_list_schema,
    software_version_partial_update_schema,
    software_version_publish_schema,
    software_version_update_schema,
    software_version_withdraw_schema,
)
from apps.configuration.models import SoftwareVersion
from apps.configuration.selectors import SoftwareVersionSelector
from apps.configuration.serializers import (
    ChangelogEntryCreateSerializer,
    PublishVersionSerializer,
    SoftwareVersionCreateSerializer,
    SoftwareVersionDetailSerializer,
    SoftwareVersionListSerializer,
    SoftwareVersionUpdateSerializer,
    VersionChangelogEntrySerializer,
    WithdrawVersionSerializer,
)
from apps.configuration.services import SoftwareVersionService
from apps.core.security import HasPermission
from apps.core.views.base_viewset import BaseViewSet
from apps.users.permissions import IsAuthenticatedAndActive


class SoftwareVersionViewSet(BaseViewSet):
    """
    ViewSet para la administración integral del ciclo de versiones del ERP.
    Soporta registro en borrador, edición, publicación, retiro, changelog
    y verificación de actualizaciones.
    """

    queryset = SoftwareVersion.objects.all()
    permission_classes = [IsAuthenticatedAndActive]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["version", "name", "description"]
    ordering_fields = ["version", "published_at", "created_at"]
    ordering = ["-created_at"]

    def get_permissions(self):
        permission_map = {
            "list": (IsAuthenticatedAndActive, HasPermission("settings.view")),
            "retrieve": (IsAuthenticatedAndActive, HasPermission("settings.view")),
            "history": (IsAuthenticatedAndActive, HasPermission("settings.view")),
            "latest": (IsAuthenticatedAndActive, HasPermission("settings.view")),
            "check_updates": (IsAuthenticatedAndActive,),
            "notifications": (IsAuthenticatedAndActive,),
            "mark_as_read": (IsAuthenticatedAndActive,),
            "mark_all_read": (IsAuthenticatedAndActive,),
            "create": (IsAuthenticatedAndActive, HasPermission("system.manage_releases")),
            "update": (IsAuthenticatedAndActive, HasPermission("system.manage_releases")),
            "partial_update": (IsAuthenticatedAndActive, HasPermission("system.manage_releases")),
            "destroy": (IsAuthenticatedAndActive, HasPermission("system.manage_releases")),
            "publish": (IsAuthenticatedAndActive, HasPermission("system.manage_releases")),
            "withdraw": (IsAuthenticatedAndActive, HasPermission("system.manage_releases")),
            "add_changelog": (IsAuthenticatedAndActive, HasPermission("system.manage_releases")),
            "delete_changelog": (IsAuthenticatedAndActive, HasPermission("system.manage_releases")),
        }

        classes = permission_map.get(
            self.action,
            (IsAuthenticatedAndActive, HasPermission("settings.view")),
        )
        return [permission() for permission in classes]

    def get_queryset(self):
        qs = SoftwareVersionSelector().get_queryset()
        status_param = self.request.query_params.get("status")
        if status_param and status_param in SoftwareVersion.Status.values:
            qs = qs.filter(status=status_param)
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return SoftwareVersionListSerializer
        if self.action == "create":
            return SoftwareVersionCreateSerializer
        if self.action in ("update", "partial_update"):
            return SoftwareVersionUpdateSerializer
        if self.action == "publish":
            return PublishVersionSerializer
        if self.action == "withdraw":
            return WithdrawVersionSerializer
        if self.action == "add_changelog":
            return ChangelogEntryCreateSerializer
        return SoftwareVersionDetailSerializer

    @software_version_list_schema
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = SoftwareVersionListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = SoftwareVersionListSerializer(queryset, many=True)
        return self.success_response(
            message="Versiones obtenidas correctamente.",
            code="SOFTWARE_VERSIONS_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @software_version_detail_schema
    def retrieve(self, request, *args, **kwargs):
        version = SoftwareVersionSelector.get_version_by_id(kwargs["pk"])
        if not version:
            return self.error_response(
                message="Versión no encontrada.",
                code="SOFTWARE_VERSION_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        serializer = SoftwareVersionDetailSerializer(version)
        return self.success_response(
            message="Detalle de versión obtenido correctamente.",
            code="SOFTWARE_VERSION_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @software_version_create_schema
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            dto = serializer.to_dto()
            version = SoftwareVersionService.create_version(dto, user=request.user)
            res_serializer = SoftwareVersionDetailSerializer(version)
            return self.success_response(
                message=f"Borrador de versión v{version.version} registrado correctamente.",
                code="SOFTWARE_VERSION_CREATED",
                data=res_serializer.data,
                status_code=status.HTTP_201_CREATED,
            )
        except ValidationError as exc:
            return self.handle_validation_error(exc)

    @software_version_update_schema
    def update(self, request, *args, **kwargs):
        version = SoftwareVersionSelector.get_version_by_id(kwargs["pk"])
        if not version:
            return self.error_response(
                message="Versión no encontrada.",
                code="SOFTWARE_VERSION_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            dto = serializer.to_dto()
            updated = SoftwareVersionService.update_version(version, dto, user=request.user)
            res_serializer = SoftwareVersionDetailSerializer(updated)
            return self.success_response(
                message="Versión actualizada correctamente.",
                code="SOFTWARE_VERSION_UPDATED",
                data=res_serializer.data,
                status_code=status.HTTP_200_OK,
            )
        except ValidationError as exc:
            return self.handle_validation_error(exc)

    @software_version_partial_update_schema
    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    @software_version_destroy_schema
    def destroy(self, request, *args, **kwargs):
        version = SoftwareVersionSelector.get_version_by_id(kwargs["pk"])
        if not version:
            return self.error_response(
                message="Versión no encontrada.",
                code="SOFTWARE_VERSION_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        SoftwareVersionService.delete_draft(version, user=request.user)
        return self.success_response(
            message=f"Borrador de versión v{version.version} eliminado correctamente.",
            code="SOFTWARE_VERSION_DELETED",
            status_code=status.HTTP_200_OK,
        )

    @software_version_publish_schema
    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, pk=None):
        version = SoftwareVersionSelector.get_version_by_id(pk)
        if not version:
            return self.error_response(
                message="Versión no encontrada.",
                code="SOFTWARE_VERSION_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        force = serializer.validated_data.get("force", False)
        force_reason = serializer.validated_data.get("force_reason", "")

        published = SoftwareVersionService.publish_version(
            version, user=request.user, force=force, force_reason=force_reason
        )
        res_serializer = SoftwareVersionDetailSerializer(published)
        return self.success_response(
            message=f"Versión v{published.version} publicada exitosamente.",
            code="SOFTWARE_VERSION_PUBLISHED",
            data=res_serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @software_version_withdraw_schema
    @action(detail=True, methods=["post"], url_path="withdraw")
    def withdraw(self, request, pk=None):
        version = SoftwareVersionSelector.get_version_by_id(pk)
        if not version:
            return self.error_response(
                message="Versión no encontrada.",
                code="SOFTWARE_VERSION_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reason = serializer.validated_data.get("reason", "")
        withdrawn = SoftwareVersionService.withdraw_version(
            version, user=request.user, reason=reason
        )
        res_serializer = SoftwareVersionDetailSerializer(withdrawn)
        return self.success_response(
            message=f"Versión v{withdrawn.version} retirada exitosamente.",
            code="SOFTWARE_VERSION_WITHDRAWN",
            data=res_serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @software_version_changelog_add_schema
    @action(detail=True, methods=["post"], url_path="changelog")
    def add_changelog(self, request, pk=None):
        version = SoftwareVersionSelector.get_version_by_id(pk)
        if not version:
            return self.error_response(
                message="Versión no encontrada.",
                code="SOFTWARE_VERSION_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dto = serializer.to_dto()
        entry = SoftwareVersionService.add_changelog_entry(version, dto, user=request.user)
        res_serializer = VersionChangelogEntrySerializer(entry)
        return self.success_response(
            message="Entrada de changelog agregada correctamente.",
            code="CHANGELOG_ENTRY_ADDED",
            data=res_serializer.data,
            status_code=status.HTTP_201_CREATED,
        )

    @software_version_delete_changelog_schema
    @action(
        detail=True,
        methods=["delete"],
        url_path="changelog/(?P<entry_id>[0-9]+)",
    )
    def delete_changelog(self, request, pk=None, entry_id=None):
        version = SoftwareVersionSelector.get_version_by_id(pk)
        if not version:
            return self.error_response(
                message="Versión no encontrada.",
                code="SOFTWARE_VERSION_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        SoftwareVersionService.delete_changelog_entry(int(entry_id), user=request.user)
        return self.success_response(
            message="Entrada de changelog eliminada correctamente.",
            code="CHANGELOG_ENTRY_DELETED",
            status_code=status.HTTP_200_OK,
        )

    @software_version_check_updates_schema
    @action(detail=False, methods=["get"], url_path="check-updates")
    def check_updates(self, request):
        result = SoftwareVersionSelector.check_for_updates()
        return self.success_response(
            message="Estado de versiones consultado correctamente.",
            code="VERSION_CHECK_SUCCESS",
            data=result,
            status_code=status.HTTP_200_OK,
        )

    @software_version_latest_schema
    @action(detail=False, methods=["get"], url_path="latest")
    def latest(self, request):
        latest = SoftwareVersionSelector.get_latest_published_version()
        if not latest:
            return self.success_response(
                message="No hay versiones publicadas registradas.",
                code="NO_PUBLISHED_VERSIONS",
                data=None,
                status_code=status.HTTP_200_OK,
            )
        serializer = SoftwareVersionDetailSerializer(latest)
        return self.success_response(
            message="Última versión publicada obtenida correctamente.",
            code="LATEST_VERSION_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @software_version_history_schema
    @action(detail=False, methods=["get"], url_path="history")
    def history(self, request):
        qs = SoftwareVersionSelector.get_published_history()
        serializer = SoftwareVersionListSerializer(qs, many=True)
        return self.success_response(
            message="Historial de versiones obtenido correctamente.",
            code="VERSION_HISTORY_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="notifications")
    def notifications(self, request):
        """
        Consulta las notificaciones de versiones publicadas para el usuario autenticado,
        indicando el número de versiones no leídas y el listado de lanzamientos.
        """
        data = SoftwareVersionSelector.get_user_notifications(request.user)
        return self.success_response(
            message="Notificaciones de versiones consultadas correctamente.",
            code="VERSION_NOTIFICATIONS_FETCHED",
            data=data,
            status_code=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="read")
    def mark_as_read(self, request, pk=None):
        """
        Marca una versión como leída/consultada por el usuario autenticado.
        """
        version = SoftwareVersionSelector.get_version_by_id(pk)
        if not version:
            return self.error_response(
                message="Versión no encontrada.",
                code="SOFTWARE_VERSION_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        SoftwareVersionService.mark_version_as_read(version, request.user)
        unread_count = SoftwareVersionSelector.get_user_unread_count(request.user)
        return self.success_response(
            message=f"Versión v{version.version} marcada como leída.",
            code="VERSION_MARKED_AS_READ",
            data={"unread_count": unread_count, "version_id": version.id_version},
            status_code=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        """
        Marca todas las versiones publicadas como leídas para el usuario autenticado.
        """
        marked_count = SoftwareVersionService.mark_all_versions_as_read(request.user)
        return self.success_response(
            message=f"{marked_count} versiones marcadas como leídas.",
            code="ALL_VERSIONS_MARKED_AS_READ",
            data={"marked_count": marked_count, "unread_count": 0},
            status_code=status.HTTP_200_OK,
        )

