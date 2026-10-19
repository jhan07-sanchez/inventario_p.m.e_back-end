from django.urls import include, path

from apps.core.views.health_view import HealthCheckView

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="api-health-check"),
    path("", include("apps.users.urls")),
    path("", include("apps.customers.urls")),
    path("", include("apps.suppliers.urls")),
    path("", include("apps.categories.urls")),
    path("", include("apps.products.urls")),
    path("", include("apps.inventory.urls")),
    path("", include("apps.purchases.urls")),
    path("", include("apps.sales.urls")),
    path("", include("apps.invoices.urls")),
    path("", include("apps.company_info.urls")),
    path("cash/", include("apps.cash.urls")),
]
