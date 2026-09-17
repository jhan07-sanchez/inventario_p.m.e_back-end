from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from apps.core.selectors.base_selector import BaseSelector
from apps.invoices.models import Invoice


class InvoiceSelector(BaseSelector[Invoice]):
    """
    Selector encargado de las consultas de facturas.
    """

    def __init__(self):
        super().__init__(Invoice)

    def get_queryset(self) -> QuerySet[Invoice]:
        """
        Retorna el queryset optimizando relaciones de plantilla, compra y detalle.
        """
        return (
            super()
            .get_queryset()
            .select_related("template", "purchase")
            .prefetch_related("items", "items__product")
            .order_by("-created_at")
        )

    @staticmethod
    def get_invoices() -> QuerySet[Invoice]:
        return InvoiceSelector().get_all()


    @staticmethod
    def get_active_invoices() -> QuerySet[Invoice]:
        """
        Retorna únicamente las facturas activas.
        """
        return InvoiceSelector().get_active()

    @staticmethod
    def invoice_exists(*, invoice_number: str) -> bool:
        """
        Verifica si existe una factura por su número.
        """
        return InvoiceSelector().exists(invoice_number=invoice_number)


    @staticmethod
    def get_by_id(invoice_id: int) -> Invoice:
        return get_object_or_404(
            InvoiceSelector().get_queryset(),
            id=invoice_id,
        )

    @staticmethod
    def get_by_number(invoice_number: str) -> Invoice:
        return get_object_or_404(
            InvoiceSelector().get_queryset(),
            invoice_number=invoice_number,
        )

    @staticmethod
    def filter_invoices(
        *,
        document_type: str | None = None,
        status: str | None = None,
        is_active: bool | None = None,
    ) -> QuerySet[Invoice]:
        queryset = InvoiceSelector().get_queryset()

        if document_type:
            queryset = queryset.filter(document_type=document_type)

        if status:
            queryset = queryset.filter(status=status)

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        return queryset


