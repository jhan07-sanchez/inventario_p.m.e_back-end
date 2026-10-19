from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.customers.views.customer_viewset import CustomerViewSet

router = DefaultRouter()

router.register(
    r"customers",
    CustomerViewSet,
    basename="customers",
)


urlpatterns = [
    path("", include(router.urls)),
]
