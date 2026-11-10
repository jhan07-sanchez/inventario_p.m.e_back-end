from typing import Any
from django.db.models import Prefetch, QuerySet
from django.shortcuts import get_object_or_404

from apps.core.selectors.base_selector import BaseSelector
from apps.invoices.models import Invoice
from apps.sales.models import Sale, SaleDetail


class SaleSelector(BaseSelector[Sale]):
    """
    Selector encargado de realizar consultas de lectura relacionadas
    con las ventas.

    La clase no modifica información y no contiene lógica de
    persistencia.
    """

    def __init__(self):
        super().__init__(Sale)

    def get_queryset(
        self, include_deleted: bool = False, company_id: Any = None
    ) -> QuerySet[Sale]:
        """
        Retorna el queryset base de ventas optimizando las relaciones
        con cliente, usuario, detalles de productos y facturas asociadas.
        """
        invoice_qs = (
            Invoice.all_objects.all()
            if include_deleted
            else Invoice.objects.filter(is_active=True).only(
                "id",
                "invoice_number",
                "status",
                "document_type",
                "is_active",
            )
        )
        return (
            super()
            .get_queryset(include_deleted=include_deleted, company_id=company_id)
            .select_related(
                "customer",
                "user",
            )
            .prefetch_related(
                "details__product",
                Prefetch(
                    "invoices",
                    queryset=invoice_qs,
                    to_attr="prefetched_invoices",
                ),
            )
            .order_by("-created_at")
        )

    @staticmethod
    def get_all(
        qs=None, include_deleted: bool = False, company_id: Any = None
    ) -> QuerySet[Sale]:
        """
        Obtiene todas las ventas activas confinado al tenant correspondiente.
        """
        if qs is not None:
            base = qs.filter(is_active=True) if not include_deleted else qs
            if company_id is not None:
                base = base.filter(company_id=company_id)
            return base
        return (
            SaleSelector().get_queryset(
                include_deleted=include_deleted, company_id=company_id
            )
            if include_deleted
            else SaleSelector()
            .get_queryset(company_id=company_id)
            .filter(is_active=True)
        )

    @staticmethod
    def get_by_id(
        sale_id: int, include_deleted: bool = False, company_id: Any = None
    ) -> Sale:
        """
        Obtiene una venta por su identificador asegurando aislamiento tenant.
        """
        return get_object_or_404(
            SaleSelector().get_queryset(
                include_deleted=include_deleted, company_id=company_id
            ),
            id_sale=sale_id,
        )

    @staticmethod
    def get_by_sale_number(
        sale_number: str, company_id: Any = None
    ) -> Sale | None:
        """
        Obtiene una venta mediante su número de venta.
        """
        qs = Sale.objects.filter(
            sale_number=sale_number,
            is_active=True,
        )
        if company_id is not None:
            qs = qs.filter(company_id=company_id)

        return (
            qs.select_related(
                "customer",
                "user",
            )
            .prefetch_related(
                "details__product",
                Prefetch(
                    "invoices",
                    queryset=Invoice.objects.filter(is_active=True).only(
                        "id",
                        "invoice_number",
                        "status",
                        "document_type",
                        "is_active",
                    ),
                    to_attr="prefetched_invoices",
                ),
            )
            .first()
        )

    @staticmethod
    def get_details(sale_id: int) -> QuerySet[SaleDetail]:
        """
        Obtiene los detalles activos de una venta.
        """
        return (
            SaleDetail.objects.filter(
                sale_id=sale_id,
                is_active=True,
            )
            .select_related("product")
            .order_by("id_sale_detail")
        )

    @staticmethod
    def exists_by_sale_number(
        sale_number: str, company_id: Any = None
    ) -> bool:
        """
        Comprueba si existe una venta con el número indicado.
        """
        qs = Sale.objects.filter(sale_number=sale_number)
        if company_id is not None:
            qs = qs.filter(company_id=company_id)
        return qs.exists()

    @staticmethod
    def filter_sales(
        *,
        customer_id: int | None = None,
        status: str | None = None,
        invoice_number: str | None = None,
        invoice_status: str | None = None,
        is_active: bool | None = True,
        company_id: int | None = None,
    ) -> QuerySet[Sale]:
        """
        Retorna ventas aplicando filtros opcionales confinado a la empresa.
        """
        queryset = SaleSelector.get_all(company_id=company_id)

        if customer_id is not None:
            queryset = queryset.filter(customer_id=customer_id)

        if status:
            queryset = queryset.filter(status=status)

        if invoice_number:
            queryset = queryset.filter(
                invoices__invoice_number__icontains=invoice_number,
            )

        if invoice_status:
            queryset = queryset.filter(
                invoices__status=invoice_status,
            )

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        return queryset.distinct().order_by("-created_at")
