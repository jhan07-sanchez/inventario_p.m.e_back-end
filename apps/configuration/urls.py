from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.configuration.views import ConfigurationAuditViewSet, GlobalParameterViewSet

router = DefaultRouter()
router.register(r"parameters", GlobalParameterViewSet, basename="global-parameters")
router.register(r"audits", ConfigurationAuditViewSet, basename="configuration-audits")

urlpatterns = [
    path("", include(router.urls)),
]
