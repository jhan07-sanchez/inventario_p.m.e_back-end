from django.db import models
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from apps.core.selectors.base_selector import BaseSelector
from apps.purchases.models import Purchase


class PurchaseSelector(BaseSelector[Purchase]):
    """
    Selector encargado de las consultas relacionadas
    con las compras.

    Los selectors contienen exclusivamente lógica de lectura.
    """

    def __init__(self):
        super().__init__(Purchase)

    def get_queryset(self) -> QuerySet[Purchase]:
        """
        Retorna el queryset base de compras optimizando
        las relaciones necesarias (proveedor y líneas de detalle).
        """
        return (
            super()
            .get_queryset()
            .select_related("supplier")
            .prefetch_related("details", "details__product")
            .order_by("-id_purchase")
        )

    @staticmethod
    def get_purchases() -> QuerySet[Purchase]:
        """
        Retorna todas las compras.
        """
        return PurchaseSelector().get_all()

    @staticmethod
    def get_active_purchases() -> QuerySet[Purchase]:
        """
        Retorna únicamente las compras activas.
        """
        return PurchaseSelector().get_active()

    @staticmethod
    def get_purchase_by_id(purchase_id: int) -> Purchase:
        """
        Obtiene una compra por su identificador.
        """
        return get_object_or_404(
            PurchaseSelector().get_queryset(),
            pk=purchase_id,
        )

    @staticmethod
    def get_by_invoice_number(invoice_number: str) -> Purchase:
        """
        Obtiene una compra mediante su número de factura.
        """
        return get_object_or_404(
            PurchaseSelector().get_queryset(),
            invoices__invoice_number=invoice_number,
        )

    @staticmethod
    def purchase_exists(
        *,
        invoice_number: str | None = None,
    ) -> bool:
        """
        Verifica si existe una compra mediante su número de factura.
        """
        selector = PurchaseSelector()

        if invoice_number is not None:
            return selector.exists(invoices__invoice_number=invoice_number)

        return False

    @staticmethod
    def filter_purchases(
        *,
        supplier_id: int | None = None,
        status: str | None = None,
        invoice_number: str | None = None,
        is_active: bool | None = None,
    ) -> QuerySet[Purchase]:
        """
        Retorna compras aplicando filtros opcionales.
        """
        queryset = PurchaseSelector().get_queryset()

        if supplier_id is not None:
            queryset = queryset.filter(
                supplier_id=supplier_id,
            )

        if status:
            queryset = queryset.filter(
                status=status,
            )

        if invoice_number:
            queryset = queryset.filter(
                invoices__invoice_number__icontains=invoice_number,
            )

        if is_active is not None:
            queryset = queryset.filter(
                is_active=is_active,
            )

        return queryset.order_by("-created_at")
