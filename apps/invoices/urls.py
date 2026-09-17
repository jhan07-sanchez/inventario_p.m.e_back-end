from rest_framework.routers import DefaultRouter

from apps.invoices.views import InvoiceTemplateViewSet, InvoiceViewSet


router = DefaultRouter()

router.register(
    r"invoice-templates",
    InvoiceTemplateViewSet,
    basename="invoice-templates",
)

router.register(
    r"invoices",
    InvoiceViewSet,
    basename="invoices",
)

urlpatterns = router.urls
