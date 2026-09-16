from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.inventory.views.inventory_viewset import InventoryViewSet
from apps.inventory.views.inventory_movement_viewset import InventoryMovementViewSet

router = DefaultRouter()

router.register(
    r"inventory",
    InventoryViewSet,
    basename="inventory",
)

router.register(
    r"inventory-movements",
    InventoryMovementViewSet,
    basename="inventory-movements",
)

urlpatterns = [
    path("", include(router.urls)),
]
