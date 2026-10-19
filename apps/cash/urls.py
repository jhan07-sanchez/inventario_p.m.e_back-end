from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.cash.views.cash_register_viewset import CashRegisterViewSet
from apps.cash.views.cash_session_viewset import CashSessionViewSet

router = DefaultRouter()

router.register(
    r"cash-registers",
    CashRegisterViewSet,
    basename="cash-register",
)

router.register(
    r"cash-sessions",
    CashSessionViewSet,
    basename="cash-session",
)

urlpatterns = [
    path("", include(router.urls)),
]


