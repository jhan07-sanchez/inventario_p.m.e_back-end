from django.urls import include, path


urlpatterns = [
    path("", include("apps.users.urls")),
    path("", include("apps.customers.urls")),
    path("", include("apps.suppliers.urls")),
    path("", include("apps.categories.urls")),
    path("", include("apps.products.urls")),
    path("", include("apps.inventory.urls")),
]
