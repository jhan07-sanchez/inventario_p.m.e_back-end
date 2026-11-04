from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.finance.views import (
    FinanceDashboardView,
    FinancialAccountViewSet,
    FinancialCategoryViewSet,
    FinancialMovementViewSet,
    FinancialReconciliationViewSet,
    FinancialTransferViewSet,
)

router = DefaultRouter()
router.register(r"finance/accounts", FinancialAccountViewSet, basename="financial-accounts")
router.register(
    r"finance/categories", FinancialCategoryViewSet, basename="financial-categories"
)
router.register(
    r"finance/movements", FinancialMovementViewSet, basename="financial-movements"
)
router.register(
    r"finance/transfers", FinancialTransferViewSet, basename="financial-transfers"
)
router.register(
    r"finance/reconciliations",
    FinancialReconciliationViewSet,
    basename="financial-reconciliations",
)

urlpatterns = [
    path("finance/dashboard/", FinanceDashboardView.as_view(), name="finance-dashboard"),
    path(
        "finance/dashboard/summary/",
        FinanceDashboardView.as_view(),
        name="finance-dashboard-summary",
    ),
    path("", include(router.urls)),
]
