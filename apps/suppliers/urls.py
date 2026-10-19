from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.suppliers.views.supplier_viewset import SupplierViewSet

router = DefaultRouter()

router.register(
    r"suppliers",
    SupplierViewSet,
    basename="suppliers",
)


urlpatterns = [
    path("", include(router.urls)),
]
