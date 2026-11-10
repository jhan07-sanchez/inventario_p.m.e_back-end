from datetime import date
from decimal import Decimal
from typing import Optional

from django.db.models import Sum, F, Q, Value, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.cash.models.cash_session import CashSession
from apps.cash.models.payment import Payment
from apps.finance.models.financial_account import FinancialAccount
from apps.finance.selectors.financial_account_selector import FinancialAccountSelector
from apps.finance.selectors.financial_movement_selector import FinancialMovementSelector
from apps.invoices.models.invoice import Invoice
from apps.purchases.models.purchase import Purchase
from apps.sales.models.sale import Sale


class FinanceDashboardSelector:
    """
    Selector centralizado de métricas e indicadores de tesorería y finanzas empresariales.

    Principios innegociables:
    - Distingue claramente entre dinero disponible en caja/bancos y obligaciones pendientes (CxC / CxP).
    - No presenta la facturación total como saldo bancario líquido.
    - Excluye transferencias entre cuentas propias para no inflar ingresos o gastos.
    - Utiliza aritmética decimal exacta (Decimal).
    """

    @classmethod
    def get_dashboard_metrics(
        cls,
        company_id: Optional[int] = None,
        period: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        today = timezone.localdate()
        if period == "today":
            start_date = today
            end_date = today
        elif period == "month":
            start_date = today.replace(day=1)
            end_date = today
        elif period == "quarter":
            quarter_month = ((today.month - 1) // 3) * 3 + 1
            start_date = today.replace(month=quarter_month, day=1)
            end_date = today
        elif period == "year":
            start_date = today.replace(month=1, day=1)
            end_date = today
        else:
            if not start_date:
                start_date = today.replace(day=1)  # Primer día del mes actual
            if not end_date:
                end_date = today

        # 1. Saldos Disponibles por Tipo de Cuenta
        accounts_qs = FinancialAccountSelector.get_accounts(company_id=company_id)

        total_available = (
            accounts_qs.aggregate(total=Sum("current_balance"))["total"]
            or Decimal("0.00")
        )

        cash_accounts_balance = (
            accounts_qs.filter(
                account_type=FinancialAccount.AccountType.CASH
            ).aggregate(total=Sum("current_balance"))["total"]
            or Decimal("0.00")
        )

        # Cajas físicas operativas actualmente abiertas
        open_cash_sessions = CashSession.objects.filter(
            status=CashSession.SessionStatus.OPEN,
            is_active=True,
        )
        if company_id is not None:
            open_cash_sessions = open_cash_sessions.filter(company_id=company_id)

        total_open_drawers = (
            open_cash_sessions.aggregate(total=Sum("expected_balance"))["total"]
            or Decimal("0.00")
        )

        bank_balance = (
            accounts_qs.filter(
                account_type__in=[
                    FinancialAccount.AccountType.BANK,
                    FinancialAccount.AccountType.DIGITAL_WALLET,
                ]
            ).aggregate(total=Sum("current_balance"))["total"]
            or Decimal("0.00")
        )

        total_cash = cash_accounts_balance + total_open_drawers
        total_liquidez_real = bank_balance + total_cash

        # 2. Flujo de Caja del Período (Ingresos y Egresos Operativos Reales)
        period_totals = FinancialMovementSelector.get_period_totals(
            company_id=company_id,
            start_date=start_date,
            end_date=end_date,
            exclude_transfers=True,
        )

        # 3. Cuentas por Cobrar (Ventas pendientes de cobro efectivo)
        # Se analizan facturas de venta emitidas pendientes o ventas administrativas no completadas
        receivables_invoices = Invoice.objects.filter(
            document_type=Invoice.DocumentType.SALE_INVOICE,
            status=Invoice.Status.ISSUED,
            is_active=True,
        )
        if company_id is not None:
            receivables_invoices = receivables_invoices.filter(company_id=company_id)

        receivables_invoices = receivables_invoices.annotate(
            paid_amount=Coalesce(
                Sum('sale__payments__amount', filter=Q(sale__payments__status=Payment.PaymentStatus.COMPLETED)),
                Value(0.00), output_field=DecimalField()
            )
        ).annotate(pending_amount=F('total') - F('paid_amount'))
        total_receivables = Decimal("0.00")
        for inv in receivables_invoices:
            # Descontar lo pagado si hay relación de venta
            if inv.sale:
                paid = (
                    inv.sale.payments.filter(
                        status=Payment.PaymentStatus.COMPLETED, is_active=True
                    ).aggregate(total=Sum("amount"))["total"]
                    or Decimal("0.00")
                )
                pending = inv.total - paid
                if pending > Decimal("0.00"):
                    total_receivables += pending
            else:
                total_receivables += inv.total

        # 4. Cuentas por Pagar (Compras confirmadas o recibidas con saldo pendiente a proveedores)
        pending_purchases = Purchase.objects.filter(
            status__in=[Purchase.Status.PENDING, Purchase.Status.RECEIVED],
            is_active=True,
        )
        if company_id is not None:
            pending_purchases = pending_purchases.filter(company_id=company_id)

        total_payables = Decimal("0.00")
        for pur in pending_purchases:
            ref_prefix = f"COMPRA #{pur.id_purchase}"
            paid_qs = Payment.objects.filter(
                reference__startswith=ref_prefix,
                status=Payment.PaymentStatus.COMPLETED,
                is_active=True,
            )
            paid = paid_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
            balance = pur.total - paid
            if balance > Decimal("0.00"):
                total_payables += balance

        # 5. Ventas / Cobros por Método de Pago en el Período
        payments_in_period = Payment.objects.filter(
            status=Payment.PaymentStatus.COMPLETED,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            is_active=True,
        )
        if company_id is not None:
            payments_in_period = payments_in_period.filter(
                Q(sale__company_id=company_id)
                | Q(cash_movements__cash_session__company_id=company_id)
            ).distinct()

        pm_aggregates = payments_in_period.values("payment_method").annotate(total=Sum("amount"))
        sales_by_method = {
            item["payment_method"]: str(item["total"] or Decimal("0.00"))
            for item in pm_aggregates
        }

        # 6. Movimientos Recientes
        recent_movements = FinancialMovementSelector.get_movements(
            company_id=company_id,
            include_deleted=False,
        )[:8]

        recent_movements_data = [
            {
                "id_financial_movement": m.id_financial_movement,
                "account_name": m.account.name,
                "movement_type": m.movement_type,
                "amount": str(m.amount),
                "movement_date": str(m.movement_date),
                "description": m.description,
                "category_name": m.category.name if m.category else None,
                "status": m.status,
            }
            for m in recent_movements
        ]

        # 7. Resumen de Cuentas Activas
        accounts_summary = [
            {
                "id_financial_account": acc.id_financial_account,
                "name": acc.name,
                "account_type": acc.account_type,
                "account_type_display": acc.get_account_type_display(),
                "bank_name": acc.bank_name,
                "account_number": acc.account_number,
                "currency": acc.currency,
                "current_balance": str(acc.current_balance),
            }
            for acc in accounts_qs
        ]

        # 8. Resumen consolidado para compatibilidad y ERP stats
        summary_payload = {
            "total_liquid_balance": str(total_liquidez_real),
            "total_inflow": str(period_totals["income"]),
            "total_outflow": str(period_totals["expense"]),
            "net_flow": str(period_totals["net"]),
        }

        sales_in_period = Sale.objects.filter(
            status=Sale.SaleStatus.COMPLETED,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            is_active=True,
        )
        if company_id is not None:
            sales_in_period = sales_in_period.filter(company_id=company_id)

        total_sales_amount = (
            sales_in_period.aggregate(total=Sum("total"))["total"] or Decimal("0.00")
        )
        total_sales_count = sales_in_period.count()

        purchases_in_period = Purchase.objects.filter(
            status=Purchase.Status.RECEIVED,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            is_active=True,
        )
        if company_id is not None:
            purchases_in_period = purchases_in_period.filter(company_id=company_id)

        total_purchases_amount = (
            purchases_in_period.aggregate(total=Sum("total"))["total"] or Decimal("0.00")
        )
        total_purchases_count = purchases_in_period.count()

        return {
            "period": {
                "start_date": str(start_date),
                "end_date": str(end_date),
            },
            "summary": summary_payload,
            "sales_summary": {
                "total_amount": str(total_sales_amount),
                "total_count": total_sales_count,
            },
            "purchases_summary": {
                "total_amount": str(total_purchases_amount),
                "total_count": total_purchases_count,
            },
            "expenses_summary": {
                "total_amount": str(period_totals["expense"]),
            },
            "liquidity": {
                "total_available_money": str(total_liquidez_real),
                "financial_accounts_balance": str(total_available),
                "cash_in_drawers": str(total_open_drawers),
                "total_cash": str(total_cash),
                "bank_balances": str(bank_balance),
            },
            "cash_flow": {
                "period_income": str(period_totals["income"]),
                "period_expense": str(period_totals["expense"]),
                "net_cash_flow": str(period_totals["net"]),
            },
            "obligations": {
                "accounts_receivable": str(total_receivables),
                "accounts_payable": str(total_payables),
            },
            "sales_by_payment_method": sales_by_method,
            "accounts": accounts_summary,
            "recent_movements": recent_movements_data,
        }

