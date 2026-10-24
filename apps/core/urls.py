from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.core.views.health_view import HealthCheckView
from apps.core.views.history_viewset import SystemHistoryViewSet

router= DefaultRouter()
router.register(r"health", HealthCheckView, basename="health-check")
router.register(r"history", SystemHistoryViewSet, basename="system-history")


urlpatterns = [
    path("", include(router.urls)),
]
