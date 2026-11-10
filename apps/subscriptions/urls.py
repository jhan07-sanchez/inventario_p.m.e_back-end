from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.subscriptions.views import PlanViewSet, SubscriptionViewSet

router = DefaultRouter()
router.register(r"plans", PlanViewSet, basename="plan")
router.register(r"subscriptions", SubscriptionViewSet, basename="subscription")

urlpatterns = [
    path("", include(router.urls)),
]

