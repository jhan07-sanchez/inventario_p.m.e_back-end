from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.purchases.views.purchase_viewset import PurchaseViewSet

router = DefaultRouter()
router.register(r"purchases", PurchaseViewSet, basename="purchases")

urlpatterns = [
    path("", include(router.urls)),
]
