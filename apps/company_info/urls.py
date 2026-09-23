from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.company_info.views.company_info_viewset import CompanyInfoViewSet

router = DefaultRouter()
router.register(r"company-info", CompanyInfoViewSet, basename="company-info")

urlpatterns = [
    path("", include(router.urls)),
]
