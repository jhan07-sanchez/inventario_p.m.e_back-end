from django.core.cache import cache
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

    def get_queryset(self, include_deleted: bool = False) -> QuerySet[InvoiceTemplate]:
        return (
            super()
            .get_queryset(include_deleted=include_deleted)
            .order_by("-is_default", "name")
        )

    @staticmethod
    def get_templates() -> QuerySet[InvoiceTemplate]:
        return InvoiceTemplateSelector().get_all()

    @staticmethod
    def get_by_id(template_id: int, include_deleted: bool = False) -> InvoiceTemplate:
        return get_object_or_404(
            InvoiceTemplateSelector().get_queryset(include_deleted=include_deleted),
            id=template_id,
        )

    @staticmethod
    def get_default_template(
        document_type: str, company_id: int | None = None
    ) -> InvoiceTemplate | None:
        """
        Retorna la plantilla por defecto para un tipo de documento.
        """
        if not company_id:
            from apps.core.context import get_current_company_id

            company_id = get_current_company_id()

        cache_key = (
            f"invoice_default_template_{company_id}_{document_type}"
            if company_id
            else f"invoice_default_template_{document_type}"
        )
        cached_val = cache.get(cache_key)

        if cached_val is not None:
            return cached_val

        qs = (
            InvoiceTemplateSelector()
            .get_queryset()
            .filter(document_type=document_type, is_active=True, is_default=True)
        )
        if company_id:
            val = qs.filter(company_id=company_id).first()
            if not val:
                val = qs.filter(company__isnull=True).first()
        else:
            val = qs.first()

        cache.set(cache_key, val, timeout=3600)  # 1 hora
        return val
