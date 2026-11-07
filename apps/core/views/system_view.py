from django.conf import settings
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.configuration.selectors import SoftwareVersionSelector
from apps.configuration.serializers import (
    SoftwareVersionListSerializer,
)


class SystemInfoView(viewsets.ViewSet):
    """
    Endpoint público para consultar metadatos del sistema y sincronización de versiones.
    Retorna la versión instalada en el backend y el estado de actualizaciones disponibles.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="system_info",
        tags=["System_Info"],
        summary="Información y versión del sistema",
        description="Retorna la versión instalada en el software para sincronización con el frontend.",
        responses={
            200: inline_serializer(
                name="SystemInfoResponse",
                fields={
                    "app_name": serializers.CharField(),
                    "version": serializers.CharField(),
                    "installed_version": serializers.CharField(),
                    "installed_version_published_at": serializers.CharField(allow_null=True),
                    "latest_version": serializers.CharField(),
                    "has_update": serializers.BooleanField(),
                    "is_mandatory": serializers.BooleanField(),
                    "priority": serializers.CharField(),
                    "environment": serializers.CharField(),
                },
            )
        },
    )
    def list(self, request):
        installed_version = SoftwareVersionSelector.get_installed_version()
        update_info = SoftwareVersionSelector.check_for_updates()

        return Response(
            {
                "app_name": "Inventario P.M.E",
                "version": installed_version,
                "installed_version": installed_version,
                "installed_version_published_at": update_info.get("installed_version_published_at"),
                "latest_version": update_info.get("latest_version", installed_version),
                "has_update": update_info.get("has_update", False),
                "is_mandatory": update_info.get("is_mandatory", False),
                "priority": update_info.get("priority", "OPTIONAL"),
                "environment": "production" if not settings.DEBUG else "development",
            }
        )

    @extend_schema(
        operation_id="system_check_updates",
        tags=["System_Info"],
        summary="Verificar actualizaciones del sistema",
        description="Consulta si existe una versión superior publicada respecto a la instalada.",
    )
    @action(detail=False, methods=["get"], url_path="check-updates")
    def check_updates(self, request):
        result = SoftwareVersionSelector.check_for_updates()
        return Response(result)

    @extend_schema(
        operation_id="system_releases",
        tags=["System_Info"],
        summary="Historial público de versiones y lanzamientos",
        description="Retorna el listado de versiones publicadas y sus novedades.",
    )
    @action(detail=False, methods=["get"], url_path="releases")
    def releases(self, request):
        qs = SoftwareVersionSelector.get_published_history()
        serializer = SoftwareVersionListSerializer(qs, many=True)
        return Response(serializer.data)
