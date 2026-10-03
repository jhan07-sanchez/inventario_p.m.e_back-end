"""
Servicio de métricas para el Dashboard.
"""
from decimal import Decimal
import calendar
import datetime
from typing import Any
from django.utils import timezone
from django.core.cache import cache as django_cache
from django.db.models import Sum, F, Q, Case, When, Value, IntegerField
from django.db.models.functions import TruncMonth, Coalesce, Cast
from django.db.models import DateField

from apps.users.models import User, Role
from apps.customers.models import Customer
from apps.suppliers.models import Supplier
from apps.products.models import Product
from apps.inventory.models import Inventory
from apps.purchases.models import Purchase
from apps.invoices.models import Invoice, InvoiceItem
from apps.sales.models.sale import Sale
from apps.sales.models.sale_detail import SaleDetail


class DashboardMetricsService:
    """
    Servicio encargado de calcular las métricas para los widgets del dashboard.

    Optimización: las consultas COUNT se ejecutan una sola vez y se reutilizan
    entre widgets que necesiten el mismo dato (ej. erp_activity reutiliza
    users_active, customers_total, suppliers_active).
    """

    @staticmethod
    def get_metrics(visible_widgets: list[str]) -> list[dict[str, Any]]:
        """
        Calcula y devuelve los valores para los widgets proporcionados.

        Pre-calcula todos los conteos necesarios en una sola pasada
        para evitar consultas duplicadas a PostgreSQL.
        """

        widget_set = set(visible_widgets)

        # ── Pre-computar conteos de forma lazy (solo si algún widget lo necesita) ──

        cache: dict[str, Any] = {}

        def get_cached(key: str):
            cache_key = f"dashboard_metric_{key}"
            cached_val = django_cache.get(cache_key)
            if cached_val is not None:
                cache[key] = cached_val
                return cached_val

            if key not in cache:
                if key == "users_total":
                    cache[key] = User.objects.count()
                elif key == "users_active":
                    cache[key] = User.objects.filter(is_active=True).count()
                elif key == "roles_distribution":
                    cache[key] = Role.objects.count()
                elif key == "customers_total":
                    cache[key] = Customer.objects.count()
                elif key == "customers_recent":
                    now = timezone.now()
                    cache[key] = Customer.objects.filter(
                        created_at__year=now.year, created_at__month=now.month
                    ).count()
                elif key == "suppliers_active":
                    cache[key] = Supplier.objects.filter(is_active=True).count()
                elif key == "products_total":
                    cache[key] = Product.objects.count()
                elif key == "products_low_stock":
                    cache[key] = Inventory.objects.filter(
                        is_active=True,
                        product__is_active=True,
                        current_stock__gt=0,
                        current_stock__lte=F('minimum_stock')
                    ).count()
                elif key == "products_critical":
                    cache[key] = Inventory.objects.filter(
                        is_active=True,
                        product__is_active=True,
                        current_stock=0
                    ).count()
                elif key == "inventory_alerts":
                    cache[key] = Inventory.objects.filter(
                        Q(is_active=True, product__is_active=True) & (
                            Q(current_stock=0) | 
                            (Q(maximum_stock__isnull=False) & Q(current_stock__gt=F('maximum_stock')))
                        )
                    ).count()
                elif key == "purchases_summary":
                    cache[key] = Purchase.objects.count()
                elif key == "purchases_pending":
                    cache[key] = Purchase.objects.filter(status=Purchase.Status.PENDING).count()
                elif key == "inventory_total_value":
                    val = Inventory.objects.aggregate(
                        total=Sum(F('current_stock') * F('product__purchase_price'))
                    )['total']
                    cache[key] = val if val is not None else 0

                elif key == "sales_summary":
                    now = timezone.now()
                    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    
                    total_month = Sale.objects.filter(
                        status=Sale.SaleStatus.COMPLETED,
                        updated_at__gte=start_of_month
                    ).aggregate(total=Sum("total"))["total"]
                    
                    sales_today_count = Sale.objects.filter(
                        status=Sale.SaleStatus.COMPLETED,
                        updated_at__gte=start_of_day
                    ).count()
                    
                    cache[key] = {
                        "total_month": float(total_month) if total_month is not None else 0.0,
                        "sales_today_count": sales_today_count
                    }

                elif key == "inventory_stock_distribution":
                    #Base: inventario activos de productos activos
                    base_qs = Inventory.objects.filter(is_active=True, product__is_active=True,)

                    #Stock critico: agotados
                    critical = base_qs.filter(current_stock=0).count()

                    #Bajo stock: Tiene algo pero por debajo o igual al minimo.
                    low = base_qs.filter(current_stock__gt=0, current_stock__lte=F("minimum_stock")).count()

                    #Casi bajo stock: por encima del minimo pero hasta 5 unidades mas.
                    almost_low = base_qs.filter(current_stock__gt=F("minimum_stock"), current_stock__lte=F("minimum_stock") + 5).count()

                    #Total con inventario registrado
                    total_with_inventory = base_qs.count()

                    #Normal = el resto (garantiza que todos los estados sumen el total)
                    normal = max(0, total_with_inventory - critical - low - almost_low)

                    cache[key] = [
                        {"label": "Stock Normal", "value": normal, "color": "#16A34A"},
                        {"label": "Casi Bajo Stock", "value": almost_low, "color": "#3B82F6"},
                        {"label": "Bajo Stock", "value": low, "color": "#F59E0B"},
                        {"label": "Stock Critico", "value": critical, "color": "#DC2626"},
                    ]

                elif key == "payment_methods":
                    thirty_days_ago = timezone.now() - datetime.timedelta(days=30)

                    #Mapa de etiquetas legibles
                    PAYMENT_LABELS = {
                        "CASH": "Efectivo",
                        "CARD": "Tarjeta",
                        "TRANSFER": "Transferencia",
                        "CREDIT": "Credito",
                    }
                    invoices = Sale.objects.filter(
                        status=Sale.SaleStatus.COMPLETED,
                        updated_at__gte=thirty_days_ago,
                    )

                    buckets: dict[str, float] = {}
                    for sale_obj in invoices:
                        pm_raw = sale_obj.payment_method
                        if not pm_raw:
                            continue
                        label = PAYMENT_LABELS.get(pm_raw, pm_raw)
                        buckets[label] = buckets.get(label, Decimal('0')) + (sale_obj.total or Decimal('0'))

                    cache[key] = [
                        {"label": label, "value": round(total, 2)}
                        for label, total in sorted(buckets.items(), key=lambda x: -x[1])
                    ]

                elif key == "top_selling_products":
                    thirty_days_ago = timezone.now() - datetime.timedelta(days=30)

                    rows = (
                        SaleDetail.objects.filter(
                            sale__status=Sale.SaleStatus.COMPLETED,
                            sale__updated_at__gte=thirty_days_ago
                        )
                        .values(
                            "product__id_product",
                            "product__code",
                            "product__name",
                        )
                        .annotate(total_qty=Sum("quantity"))
                        .order_by("-total_qty")[:5]
                    )
                    items = []
                    for row in rows:
                        qty = float(row["total_qty"] or 0)
                        items.append({
                            "label": row["product__name"] or "Producto",
                            "subtitle": f"Codigo: {row['product__code'] or 'S/N'}",
                            "value": f"{qty:g}",
                            "icon": "fas fa-box",
                            "color": "primary",
                        })
                    cache[key] = items


                elif key == "latest_sales":
                    sales = (
                        Sale.objects.filter(
                            status=Sale.SaleStatus.COMPLETED
                        )
                        .select_related("customer")
                        .order_by("-updated_at")[:5]
                    )
                    items = []
                    for sale_obj in sales:
                        customer_name = "Consumidor Final"
                        if sale_obj.customer:
                            c = sale_obj.customer
                            customer_name = (
                                getattr(c, "business_name", None)
                                or f"{getattr(c, 'first_name', '') or ''} {getattr(c, 'last_name', '') or ''}".strip() or "Consumidor Final"
                            )

                        if sale_obj.updated_at:
                            date_str = sale_obj.updated_at.strftime("%d/%m/%Y %H:%M")
                        else:
                            date_str = "-"

                        doc_prefix = "Factura" if sale_obj.sale_type == Sale.SaleType.ADMIN else "POS"

                        items.append({
                            "id": sale_obj.sale_number or f"#{sale_obj.pk}",
                            "cliente": customer_name,
                            "monto": float(sale_obj.total or 0),
                            "fecha": date_str,
                            "tipo": doc_prefix,
                        })
                    cache[key] = items         

            django_cache.set(cache_key, cache.get(key), timeout=300)
            return cache.get(key)

        # Determine which counts are needed (erp_activity re-uses individual counts)
        needs_users_active = "users_active" in widget_set or "erp_activity" in widget_set
        needs_customers_total = "customers_total" in widget_set or "erp_activity" in widget_set
        needs_suppliers_active = "suppliers_active" in widget_set or "erp_activity" in widget_set
        needs_inventory_value = "erp_activity" in widget_set

        if needs_users_active:
            get_cached("users_active")
        if needs_customers_total:
            get_cached("customers_total")
        if needs_suppliers_active:
            get_cached("suppliers_active")
        if needs_inventory_value:
            get_cached("inventory_total_value")

        # ── Construir métricas ──

        metrics = []

        list_widgets = {
            "roles_distribution", "sales_monthly", "purchases_monthly",
            "needs_attention", "top_selling_products", "latest_sales",
            "inventory_stock_distribution",
        }
        
        now = timezone.now()

        for code in visible_widgets:
            value: Any = 0

            if code == "users_total":
                value = get_cached("users_total")
            elif code == "users_active":
                value = cache["users_active"]
            elif code == "roles_distribution":
                value = get_cached("roles_distribution")
            elif code == "customers_total":
                value = cache["customers_total"] if "customers_total" in cache else get_cached("customers_total")
            elif code == "customers_recent":
                value = get_cached("customers_recent")
            elif code == "suppliers_active":
                value = cache["suppliers_active"] if "suppliers_active" in cache else get_cached("suppliers_active")
            elif code == "products_total":
                value = get_cached("products_total")
            elif code == "products_low_stock":
                value = get_cached("products_low_stock")
            elif code == "inventory_alerts":
                value = get_cached("inventory_alerts")
            elif code == "purchases_summary":
                value = get_cached("purchases_summary")
            elif code == "purchases_pending":
                value = get_cached("purchases_pending")
            elif code == "purchases_monthly":
                # Ventas vs Compras del año actual por meses
                sales_by_month = list(
                    Sale.objects.filter(
                        status=Sale.SaleStatus.COMPLETED,
                        updated_at__year=now.year
                    ).annotate(
                        month=TruncMonth('updated_at')
                    ).values('month').annotate(
                        total_sales=Sum('total')
                    ).order_by('month')
                )
                
                purchases_by_month = list(Purchase.objects.filter(
                    issue_date__year=now.year
                ).annotate(month=TruncMonth('issue_date')).values('month').annotate(total_purchases=Sum('total')).order_by('month'))
                
                monthly_data = []
                for i in range(1, 13):
                    month_label = calendar.month_abbr[i]
                    sales_val = sum(item['total_sales'] for item in sales_by_month if item['month'] and item['month'].month == i)
                    purchases_val = sum(item['total_purchases'] for item in purchases_by_month if item['month'] and item['month'].month == i)
                    monthly_data.append({
                        "label": month_label.capitalize(),
                        "ventas": float(sales_val),
                        "compras": float(purchases_val)
                    })
                value = monthly_data
            elif code == "erp_activity":
                inventory_val = cache.get("inventory_total_value", 0)
                formatted_inventory_val = f"${inventory_val:,.0f}".replace(",", ".")
                
                value = [
                    {"label": "Usuarios activos", "value": cache["users_active"], "icon": "fas fa-user-check", "color": "success"},
                    {"label": "Clientes", "value": cache["customers_total"], "icon": "fas fa-user-tie", "color": "info"},
                    {"label": "Proveedores", "value": cache["suppliers_active"], "icon": "fas fa-truck", "color": "secondary"},
                    {"label": "Valor inventario actual", "value": formatted_inventory_val, "icon": "fas fa-boxes", "color": "primary"},
                ]
            elif code == "needs_attention":
                alerts_query = Inventory.objects.filter(
                    is_active=True, 
                    product__is_active=True
                ).annotate(
                    alert_priority=Case(
                        When(current_stock=0, then=Value(1)),
                        When(current_stock__lte=F('minimum_stock'), then=Value(2)),
                        When(current_stock__lte=F('minimum_stock') + 5, then=Value(3)),
                        When(Q(maximum_stock__isnull=False) & Q(current_stock__gt=F('maximum_stock')), then=Value(4)),
                        default=Value(0),
                        output_field=IntegerField()
                    )
                ).filter(alert_priority__gt=0).select_related('product')
                
                total_alerts_count = alerts_query.count()
                top_alerts = alerts_query.order_by('alert_priority', 'product__name')[:8]
                
                items = []
                for inv in top_alerts:
                    if inv.alert_priority == 1:
                        lbl = "Agotado"
                        clr = "danger"
                    elif inv.alert_priority == 2:
                        lbl = "Bajo stock"
                        clr = "warning"
                    elif inv.alert_priority == 3:
                        lbl = "Casi bajo"
                        clr = "primary"
                    else:
                        lbl = "Sobrestock"
                        clr = "info"
                        
                    items.append({
                        "label": inv.product.name,
                        "subtitle": f"Stock actual: {inv.current_stock}",
                        "value": lbl,
                        "color": clr,
                        "icon": "fas fa-exclamation-circle" if inv.alert_priority <= 2 else "fas fa-info-circle"
                    })
                
                metrics.append({"code": code, "value": items, "count": total_alerts_count})
                continue

            elif code == "sales_summary":
                value = get_cached("sales_summary")

            elif code == "inventory_stock_distribution":
                value = get_cached("inventory_stock_distribution")


            elif code == "payment_methods":
                value = get_cached("payment_methods")

            elif code == "top_selling_products":
                value = get_cached("top_selling_products")

            elif code == "latest_sales":
                value = get_cached("latest_sales")       

            elif code == "products_critical":
                value = get_cached("products_critical")

            else:
                if code in list_widgets:
                    value = []
                else:
                    value = 0
            metrics.append({"code": code, "value": value})


            forced_widgets = [
                "sale_summary",
                "inventory_stock_distribution",
                "payment_methods",
                "top_selling_products",
                "lastest_sales",
                "products_critical",
            ]

            existing_codes = {m["code"] for m in metrics}
            for code in forced_widgets:
                if code not in existing_codes:
                    metrics.append({
                        "code": code,
                        "value": get_cached(code),
                    })

        return metrics
