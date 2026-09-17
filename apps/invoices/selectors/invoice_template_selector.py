from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from apps.core.selectors.base_selector import BaseSelector
from apps.invoices.models import InvoiceTemplate


class InvoiceTemplateSelector(BaseSelector[InvoiceTemplate]):
    """
    Selector encargado de las consultas de plantillas de facturas.
    """

    def __init__(self):
        super().__init__(InvoiceTemplate)

    def get_queryset(self) -> QuerySet[InvoiceTemplate]:
        return super().get_queryset().order_by("-is_default", "name")

    @staticmethod
    def get_templates() -> QuerySet[InvoiceTemplate]:
        return InvoiceTemplateSelector().get_all()

    @staticmethod
    def get_by_id(template_id: int) -> InvoiceTemplate:
        return get_object_or_404(
            InvoiceTemplateSelector().get_queryset(),
            id=template_id,
        )

    @staticmethod
    def get_default_template(document_type: str) -> InvoiceTemplate | None:
        """
        Retorna la plantilla por defecto para un tipo de documento.
        """
        return (
            InvoiceTemplateSelector()
            .get_queryset()
            .filter(document_type=document_type, is_active=True, is_default=True)
            .first()
        )
