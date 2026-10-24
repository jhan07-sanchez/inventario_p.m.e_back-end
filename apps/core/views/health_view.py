import logging

from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def check_system_health():
    """
    Función interna que verifica la disponibilidad de base de datos y caché.
    """
    health_status = {
        "status": "healthy",
        "database": "healthy",
        "cache": "healthy",
    }
    is_healthy = True

    # 1. Comprobación de Base de Datos
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:  # noqa: BLE001
        logger.error("Health check fallo en conexion de base de datos: %s", exc)
        health_status["database"] = "unhealthy"
        is_healthy = False

    # 2. Comprobación de Caché
    try:
        cache.set("health_check_ping", "ok", 10)
        if cache.get("health_check_ping") != "ok":
            health_status["cache"] = "degraded"
    except Exception as exc:  # noqa: BLE001
        logger.warning("Health check fallo en cache: %s", exc)
        health_status["cache"] = "degraded"

    if not is_healthy:
        health_status["status"] = "unhealthy"

    return is_healthy, health_status


class HealthCheckView(viewsets.ViewSet):
    """
    Endpoint de comprobación de salud para la API (/api/v1/health/).
    Documentado en Swagger/OpenAPI.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="system_health_check",
        tags=["System"],
        summary="Comprobación de salud de la aplicación",
        description="Verifica que el servicio web, la base de datos y la caché estén operacionales sin exponer datos sensibles.",
        responses={
            200: inline_serializer(
                name="HealthCheckSuccessResponse",
                fields={
                    "status": serializers.CharField(),
                    "database": serializers.CharField(),
                    "cache": serializers.CharField(),
                },
            ),
            503: inline_serializer(
                name="HealthCheckErrorResponse",
                fields={
                    "status": serializers.CharField(),
                    "database": serializers.CharField(),
                    "cache": serializers.CharField(),
                },
            ),
        },
    )
    def list(self, request, *args, **kwargs):
        is_healthy, health_status = check_system_health()
        http_status = (
            status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return Response(health_status, status=http_status)


def root_health_check(request):
    """
    Endpoint liviano en la raíz (/health/) para pings de Render y balanceadores.
    Excluido de la documentación OpenAPI para evitar duplicidad de esquemas.
    """
    is_healthy, health_status = check_system_health()
    status_code = 200 if is_healthy else 503
    return JsonResponse(health_status, status=status_code)
