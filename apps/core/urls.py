from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.core.views.health_view import HealthCheckView
from apps.core.views.history_viewset import SystemHistoryViewSet
from apps.core.views.system_view import SystemInfoView

router= DefaultRouter()
router.register(r"health", HealthCheckView, basename="health-check")
router.register(r"system", SystemInfoView, basename="system-info")
router.register(r"history", SystemHistoryViewSet, basename="system-history")


urlpatterns = [
    path("health/", HealthCheckView.as_view({"get": "list"}), name="api-health-check"),
    path("", include(router.urls)),
]
