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

    def get_queryset(self, include_deleted: bool = False) -> QuerySet[Invoice]:
        """
        Retorna el queryset optimizando relaciones de plantilla, origen y detalle.
        """
        return (
            super()
            .get_queryset(include_deleted=include_deleted)
            .select_related("template", "purchase", "sale")
            .prefetch_related("items", "items__product")
            .order_by("-created_at")
        )

    @staticmethod
    def get_invoices() -> QuerySet[Invoice]:
        return InvoiceSelector().get_all()

    @staticmethod
    def attach_payment_totals(invoices) -> None:
        """
        Pre-calcula la información de pago para una lista de facturas en batch,
        eliminando el problema N+1 en InvoiceSerializer.
        """
        import re
        from collections import defaultdict
        from decimal import Decimal

        from django.db.models import Sum

        from apps.cash.models.payment import Payment

        inv_list = list(invoices)
        if not inv_list:
            return

        sale_ids = {
            inv.sale_id for inv in inv_list if inv and getattr(inv, "sale_id", None)
        }
        pur_ids = {
            inv.purchase_id
            for inv in inv_list
            if inv and getattr(inv, "purchase_id", None)
        }

        # 1. Pagos por ventas (directo por sale_id)
        sale_payments = {}
        if sale_ids:
            qs_sales = (
                Payment.objects.filter(
                    sale_id__in=sale_ids,
                    status=Payment.PaymentStatus.COMPLETED,
                    is_active=True,
                )
                .values("sale_id")
                .annotate(total=Sum("amount"))
            )
            sale_payments = {p["sale_id"]: p["total"] for p in qs_sales}

        # 2. Pagos por compras (por prefijo COMPRA #)
        pur_payments = defaultdict(Decimal)
        if pur_ids:
            purchase_ref_re = re.compile(r"^COMPRA #(\d+)(?:\D|$)")
            relevant = Payment.objects.filter(
                reference__startswith="COMPRA #",
                status=Payment.PaymentStatus.COMPLETED,
                is_active=True,
            ).values("reference", "amount")
            for p in relevant:
                ref = p.get("reference") or ""
                m = purchase_ref_re.match(ref)
                if m:
                    pid = int(m.group(1))
                    if pid in pur_ids:
                        pur_payments[pid] += p["amount"]

        # 3. Asignar _cached_payment_info
        for inv in inv_list:
            paid = Decimal("0.00")
            if inv.purchase_id:
                paid = pur_payments.get(inv.purchase_id, Decimal("0.00"))
            elif inv.sale_id:
                paid = sale_payments.get(inv.sale_id, Decimal("0.00"))

            diff = inv.total - paid
            pending = diff if diff > Decimal("0.00") else Decimal("0.00")
            if paid >= inv.total and inv.total > Decimal("0.00"):
                p_status = "PAID"
            elif paid > Decimal("0.00"):
                p_status = "PARTIAL"
            else:
                p_status = "UNPAID"

            inv._cached_payment_info = {
                "total_paid": paid,
                "pending_balance": pending,
                "payment_status": p_status,
            }

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
    def get_by_id(invoice_id: int, include_deleted: bool = False) -> Invoice:
        return get_object_or_404(
            InvoiceSelector().get_queryset(include_deleted=include_deleted),
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
        purchase: int | None = None,
        sale: int | None = None,
        invoice_number: str | None = None,
    ) -> QuerySet[Invoice]:
        queryset = InvoiceSelector().get_queryset()

        if document_type:
            queryset = queryset.filter(document_type=document_type)

        if status:
            queryset = queryset.filter(status=status)

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        if purchase is not None:
            queryset = queryset.filter(purchase_id=purchase)

        if sale is not None:
            queryset = queryset.filter(sale_id=sale)

        if invoice_number:
            queryset = queryset.filter(
                invoice_number__icontains=invoice_number,
            )

        return queryset

    @staticmethod
    def get_for_sale(sale_id: int) -> QuerySet[Invoice]:
        """Retorna las facturas asociadas a una venta."""

        return InvoiceSelector.filter_invoices(sale=sale_id)

    @staticmethod
    def get_for_purchase(purchase_id: int) -> QuerySet[Invoice]:
        """Retorna las facturas asociadas a una compra."""

        return InvoiceSelector.filter_invoices(purchase=purchase_id)
