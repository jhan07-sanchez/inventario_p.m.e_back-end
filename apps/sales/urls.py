from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.sales.views.sale_viewset import SaleViewSet

router = DefaultRouter()
router.register(r"sales", SaleViewSet, basename="sales")

urlpatterns = [
    path("", include(router.urls)),
]