from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.saas_admin.views.saas_admin_viewset import SaaSAdminViewSet

router = DefaultRouter()
# Registramos el ViewSet base bajo la ruta /tenants/
router.register(r"tenants", SaaSAdminViewSet, basename="saas-tenants")

urlpatterns = [
    path("", include(router.urls)),
]
