from rest_framework.routers import DefaultRouter

from apps.cash.views.cash_register_viewset import CashRegisterViewSet
from apps.cash.views.cash_session_viewset import CashSessionViewSet

router = DefaultRouter()
router.register(r"registers", CashRegisterViewSet, basename="cash-register")
router.register(r"sessions", CashSessionViewSet, basename="cash-session")

urlpatterns = router.urls
