from django.db.models import Prefetch, QuerySet
from django.shortcuts import get_object_or_404

from apps.invoices.models import Invoice
from apps.sales.models import Sale, SaleDetail


class SaleSelector:
    """
    Selector encargado de realizar consultas de lectura relacionadas
    con las ventas.

    La clase no modifica información y no contiene lógica de
    persistencia.
    """

    @staticmethod
    def get_all() -> QuerySet[Sale]:
        """
        Obtiene todas las ventas activas.

        Se utilizan relaciones optimizadas para evitar consultas
        innecesarias a la base de datos.
        """

        return (
            Sale.objects.filter(is_active=True)
            .select_related(
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
            .order_by("-created_at")
        )

    @staticmethod
    def get_by_id(sale_id: int) -> Sale:
        """
        Obtiene una venta por su identificador.

        Lanza Http404 si la venta no existe o está inactiva.
        """

        return get_object_or_404(
            Sale.objects.filter(
                is_active=True,
            )
            .select_related(
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
            ),
            id_sale=sale_id,
        )

    @staticmethod
    def get_by_sale_number(
        sale_number: str,
    ) -> Sale | None:
        """
        Obtiene una venta mediante su número de venta.
        """

        return (
            Sale.objects.filter(
                sale_number=sale_number,
                is_active=True,
            )
            .select_related(
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

        Incluye la información del producto para evitar consultas
        adicionales al serializar la respuesta.
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
        sale_number: str,
    ) -> bool:
        """
        Comprueba si existe una venta con el número indicado.
        """

        return Sale.objects.filter(
            sale_number=sale_number,
        ).exists()

    @staticmethod
    def filter_sales(
        *,
        customer_id: int | None = None,
        status: str | None = None,
        invoice_number: str | None = None,
        invoice_status: str | None = None,
        is_active: bool | None = True,
    ) -> QuerySet[Sale]:
        """
        Retorna ventas aplicando filtros opcionales, incluyendo
        información de sus facturas asociadas.
        """

        queryset = SaleSelector.get_all()

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
