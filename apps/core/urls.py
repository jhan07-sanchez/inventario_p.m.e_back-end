from django.urls import path

from apps.core.views.health_view import HealthCheckView

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="api-health-check"),
]
