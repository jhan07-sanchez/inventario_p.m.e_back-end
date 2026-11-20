from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.saas_admin.views.audit_viewset import SaaSAuditViewSet
from apps.saas_admin.views.plan_viewset import (
    SaaSAvailableModulesView,
    SaaSPlanViewSet,
)
from apps.saas_admin.views.saas_admin_viewset import SaaSAdminViewSet
from apps.saas_admin.views.subscription_viewset import SaaSSubscriptionViewSet
from apps.saas_admin.views.team_viewset import SaaSTeamViewSet

router = DefaultRouter()
router.register(r"tenants", SaaSAdminViewSet, basename="saas-tenants")
router.register(r"team", SaaSTeamViewSet, basename="saas-team")
router.register(r"audit", SaaSAuditViewSet, basename="saas-audit")
router.register(r"plans", SaaSPlanViewSet, basename="saas-plans")
router.register(r"subscriptions", SaaSSubscriptionViewSet, basename="saas-subscriptions")

urlpatterns = [
    path("modules/", SaaSAvailableModulesView.as_view(), name="saas-modules-catalog"),
    path("", include(router.urls)),
]
