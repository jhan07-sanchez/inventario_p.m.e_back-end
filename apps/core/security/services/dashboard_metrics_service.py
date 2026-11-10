"""
Servicio de métricas para el Dashboard.
"""

import calendar
import datetime
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.core.cache import cache as django_cache
from django.db.models import Case, Count, F, IntegerField, Q, Sum, Value, When
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone

from apps.customers.models import Customer
from apps.inventory.models import Inventory
from apps.products.models import Product
from apps.purchases.models import Purchase
from apps.sales.models.sale import Sale
from apps.sales.models.sale_detail import SaleDetail
from apps.suppliers.models import Supplier
from apps.users.models import Role, User

# Claves de cache del dashboard que están relacionadas con ventas.
_SALES_CACHE_KEYS = [
    "dashboard_metric_sales_summary",
    "dashboard_metric_sales_monthly",
    "dashboard_metric_latest_sales",
    "dashboard_metric_payment_methods",
    "dashboard_metric_top_selling_products",
]

# Claves de cache del dashboard relacionadas con inventario y productos.
_INVENTORY_CACHE_KEYS = [
    "dashboard_metric_products_total",
    "dashboard_metric_products_low_stock",
    "dashboard_metric_products_critical",
    "dashboard_metric_inventory_alerts",
    "dashboard_metric_inventory_total_value",
    "dashboard_metric_inventory_stock_distribution",
    "dashboard_metric_needs_attention",
]

# Claves de cache del dashboard relacionadas con compras.
_PURCHASES_CACHE_KEYS = [
    "dashboard_metric_purchases_summary",
    "dashboard_metric_purchases_pending",
    "dashboard_metric_purchases_monthly",
]


def _clean_company_id(company_id: Any) -> int | None:
    """Valida y castea de forma segura el ID de empresa para aislamiento de caché."""
    if isinstance(company_id, int):
        return company_id
    if isinstance(company_id, str) and company_id.isdigit():
        return int(company_id)
    return None


class DashboardMetricsService:
    """
    Servicio encargado de calcular las métricas para los widgets del dashboard.

    Optimización: las consultas COUNT se ejecutan una sola vez y se reutilizan
    entre widgets que necesiten el mismo dato (ej. erp_activity reutiliza
    users_active, customers_total, suppliers_active).
    """

    @staticmethod
    def invalidate_sales_cache(company_id: int | None = None) -> None:
        """
        Invalida las claves de cache del dashboard relacionadas con ventas e inventario.

        Debe llamarse después de crear, completar o cancelar una venta
        para que el dashboard refleje tanto las métricas de venta como
        la variación de existencias inmediatamente.
        """
        clean_cid = _clean_company_id(company_id)
        for key in _SALES_CACHE_KEYS + _INVENTORY_CACHE_KEYS:
            django_cache.delete(key)
            if clean_cid is not None:
                django_cache.delete(f"{key}_company_{clean_cid}")

    @staticmethod
    def invalidate_inventory_cache(company_id: int | None = None) -> None:
        """
        Invalida las claves de cache del dashboard relacionadas con inventario y productos.

        Debe llamarse después de cualquier movimiento de stock (entradas, salidas,
        ajustes, recepción de compras) o cambio en el catálogo de productos.
        """
        clean_cid = _clean_company_id(company_id)
        for key in _INVENTORY_CACHE_KEYS:
            django_cache.delete(key)
            if clean_cid is not None:
                django_cache.delete(f"{key}_company_{clean_cid}")

    @staticmethod
    def invalidate_purchases_cache(company_id: int | None = None) -> None:
        """
        Invalida las claves de cache del dashboard relacionadas con compras.

        Debe llamarse al crear, confirmar, recibir, completar o cancelar órdenes de compra.
        """
        clean_cid = _clean_company_id(company_id)
        for key in _PURCHASES_CACHE_KEYS:
            django_cache.delete(key)
            if clean_cid is not None:
                django_cache.delete(f"{key}_company_{clean_cid}")

    @staticmethod
    def invalidate_all_cache(company_id: int | None = None) -> None:
        """
        Invalida todas las claves de métricas cacheadas del dashboard.
        """
        clean_cid = _clean_company_id(company_id)
        all_keys = set(
            _SALES_CACHE_KEYS + _INVENTORY_CACHE_KEYS + _PURCHASES_CACHE_KEYS
        )
        for key in all_keys:
            django_cache.delete(key)
            if clean_cid is not None:
                django_cache.delete(f"{key}_company_{clean_cid}")

    @staticmethod
    def get_metrics(
        visible_widgets: list[str], company_id: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Calcula y devuelve los valores para los widgets proporcionados de forma tenant-aware.

        Pre-calcula todos los conteos necesarios en una sola pasada
        para evitar consultas duplicadas a PostgreSQL.
        """

        company_id = _clean_company_id(company_id)
        widget_set = set(visible_widgets)

        # ── Pre-computar conteos de forma lazy (solo si algún widget lo necesita) ──

        cache: dict[str, Any] = {}

        def get_cached(key: str):
            cache_key = (
                f"dashboard_metric_{key}_company_{company_id}"
                if company_id is not None
                else f"dashboard_metric_{key}"
            )
            cached_val = django_cache.get(cache_key)
            if cached_val is not None:
                cache[key] = cached_val
                return cached_val

            if key not in cache:
                if key == "users_total":
                    if company_id is not None:
                        cache[key] = (
                            User.objects.filter(
                                memberships__company_id=company_id,
                                memberships__is_active=True,
                            )
                            .distinct()
                            .count()
                        )
                    else:
                        cache[key] = User.objects.count()

                elif key == "users_active":
                    if company_id is not None:
                        cache[key] = (
                            User.objects.filter(
                                is_active=True,
                                memberships__company_id=company_id,
                                memberships__is_active=True,
                            )
                            .distinct()
                            .count()
                        )
                    else:
                        cache[key] = User.objects.filter(is_active=True).count()

                elif key == "roles_distribution":
                    if company_id is not None:
                        cache[key] = (
                            Role.objects.filter(
                                memberships__company_id=company_id,
                                memberships__is_active=True,
                            )
                            .distinct()
                            .count()
                        )
                    else:
                        cache[key] = Role.objects.count()

                elif key == "customers_total":
                    if company_id is not None:
                        cache[key] = Customer.objects.filter(
                            company_id=company_id
                        ).count()
                    else:
                        cache[key] = Customer.objects.count()

                elif key == "customers_recent":
                    now = timezone.now()
                    cust_qs = Customer.objects.filter(
                        created_at__year=now.year, created_at__month=now.month
                    )
                    if company_id is not None:
                        cust_qs = cust_qs.filter(company_id=company_id)
                    cache[key] = cust_qs.count()

                elif key == "suppliers_active":
                    supp_qs = Supplier.objects.filter(is_active=True)
                    if company_id is not None:
                        supp_qs = supp_qs.filter(company_id=company_id)
                    cache[key] = supp_qs.count()

                elif key == "products_total":
                    prod_qs = Product.objects.all()
                    if company_id is not None:
                        prod_qs = prod_qs.filter(company_id=company_id)
                    cache[key] = prod_qs.count()

                elif key == "products_low_stock":
                    inv_low_qs = Inventory.objects.filter(
                        is_active=True,
                        product__is_active=True,
                        current_stock__gt=0,
                        current_stock__lte=F("minimum_stock"),
                    )
                    if company_id is not None:
                        inv_low_qs = inv_low_qs.filter(
                            product__company_id=company_id
                        )
                    cache[key] = inv_low_qs.count()

                elif key == "products_critical":
                    inv_crit_qs = Inventory.objects.filter(
                        is_active=True,
                        product__is_active=True,
                        current_stock=0,
                    )
                    if company_id is not None:
                        inv_crit_qs = inv_crit_qs.filter(
                            product__company_id=company_id
                        )
                    cache[key] = inv_crit_qs.count()

                elif key == "inventory_alerts":
                    inv_alert_qs = Inventory.objects.filter(
                        Q(is_active=True, product__is_active=True)
                        & (
                            Q(current_stock=0)
                            | (
                                Q(maximum_stock__isnull=False)
                                & Q(current_stock__gt=F("maximum_stock"))
                            )
                        )
                    )
                    if company_id is not None:
                        inv_alert_qs = inv_alert_qs.filter(
                            product__company_id=company_id
                        )
                    cache[key] = inv_alert_qs.count()

                elif key == "purchases_summary":
                    purch_qs = Purchase.objects.all()
                    if company_id is not None:
                        purch_qs = purch_qs.filter(company_id=company_id)
                    cache[key] = purch_qs.count()

                elif key == "purchases_pending":
                    purch_pend_qs = Purchase.objects.filter(
                        status=Purchase.Status.PENDING
                    )
                    if company_id is not None:
                        purch_pend_qs = purch_pend_qs.filter(
                            company_id=company_id
                        )
                    cache[key] = purch_pend_qs.count()

                elif key == "inventory_total_value":
                    inv_val_qs = Inventory.objects.all()
                    if company_id is not None:
                        inv_val_qs = inv_val_qs.filter(
                            product__company_id=company_id
                        )
                    val = inv_val_qs.aggregate(
                        total=Sum(F("current_stock") * F("product__purchase_price"))
                    )["total"]
                    cache[key] = val if val is not None else 0

                elif key == "sales_summary":
                    now = timezone.localtime(timezone.now())
                    start_of_month = now.replace(
                        day=1, hour=0, minute=0, second=0, microsecond=0
                    )
                    start_of_day = now.replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )

                    sales_qs = Sale.objects.filter(
                        status=Sale.SaleStatus.COMPLETED
                    )
                    if company_id is not None:
                        sales_qs = sales_qs.filter(company_id=company_id)

                    total_month = sales_qs.filter(
                        updated_at__gte=start_of_month
                    ).aggregate(total=Sum("total"))["total"]

                    sales_today_count = sales_qs.filter(
                        updated_at__gte=start_of_day
                    ).count()

                    cache[key] = {
                        "total_month": (
                            float(total_month)
                            if total_month is not None
                            else 0.0
                        ),
                        "sales_today_count": sales_today_count,
                    }

                elif key == "inventory_stock_distribution":
                    # Base: inventarios activos de productos activos
                    base_qs = Inventory.objects.filter(
                        is_active=True,
                        product__is_active=True,
                    )
                    if company_id is not None:
                        base_qs = base_qs.filter(product__company_id=company_id)

                    counts = base_qs.aggregate(
                        critical=Count("id_inventory", filter=Q(current_stock=0)),
                        low=Count(
                            "id_inventory",
                            filter=Q(
                                current_stock__gt=0,
                                current_stock__lte=F("minimum_stock"),
                            ),
                        ),
                        almost_low=Count(
                            "id_inventory",
                            filter=Q(
                                current_stock__gt=F("minimum_stock"),
                                current_stock__lte=F("minimum_stock") + 5,
                            ),
                        ),
                        total=Count("id_inventory"),
                    )

                    critical = counts["critical"] or 0
                    low = counts["low"] or 0
                    almost_low = counts["almost_low"] or 0
                    total_with_inventory = counts["total"] or 0

                    # Normal = el resto (garantiza que todos los estados sumen el total)
                    normal = max(0, total_with_inventory - critical - low - almost_low)

                    cache[key] = [
                        {"label": "Stock Normal", "value": normal, "color": "#16A34A"},
                        {
                            "label": "Casi Bajo Stock",
                            "value": almost_low,
                            "color": "#3B82F6",
                        },
                        {"label": "Bajo Stock", "value": low, "color": "#F59E0B"},
                        {
                            "label": "Stock Critico",
                            "value": critical,
                            "color": "#DC2626",
                        },
                    ]

                elif key == "payment_methods":
                    thirty_days_ago = timezone.now() - datetime.timedelta(days=30)

                    from apps.core.enums import PaymentMethod

                    # Mapa de etiquetas legibles desde el enum canónico
                    PAYMENT_LABELS = {
                        choice.value: choice.label for choice in PaymentMethod
                    }

                    # Agrupación y suma directamente en PostgreSQL
                    sales_pm_qs = Sale.objects.filter(
                        status=Sale.SaleStatus.COMPLETED,
                        updated_at__gte=thirty_days_ago,
                        payment_method__isnull=False,
                    )
                    if company_id is not None:
                        sales_pm_qs = sales_pm_qs.filter(company_id=company_id)

                    pm_aggregates = (
                        sales_pm_qs.values("payment_method")
                        .annotate(total=Sum("total"))
                        .order_by("-total")
                    )

                    buckets: dict[str, float] = {}
                    for item in pm_aggregates:
                        pm_raw = item["payment_method"]
                        label = PAYMENT_LABELS.get(pm_raw, pm_raw)
                        buckets[label] = buckets.get(label, Decimal("0")) + (
                            item["total"] or Decimal("0")
                        )

                    cache[key] = [
                        {"label": label, "value": round(float(total), 2)}
                        for label, total in sorted(buckets.items(), key=lambda x: -x[1])
                    ]

                elif key == "purchases_monthly":
                    # Ventas vs Compras del año actual por meses
                    now_yr = timezone.now().year
                    sales_yr_qs = Sale.objects.filter(
                        status=Sale.SaleStatus.COMPLETED, updated_at__year=now_yr
                    )
                    purch_yr_qs = Purchase.objects.filter(issue_date__year=now_yr)
                    if company_id is not None:
                        sales_yr_qs = sales_yr_qs.filter(company_id=company_id)
                        purch_yr_qs = purch_yr_qs.filter(company_id=company_id)

                    sales_by_month = list(
                        sales_yr_qs.annotate(month=TruncMonth("updated_at"))
                        .values("month")
                        .annotate(total_sales=Sum("total"))
                        .order_by("month")
                    )

                    purchases_by_month = list(
                        purch_yr_qs.annotate(month=TruncMonth("issue_date"))
                        .values("month")
                        .annotate(total_purchases=Sum("total"))
                        .order_by("month")
                    )

                    monthly_data = []
                    for i in range(1, 13):
                        month_label = calendar.month_abbr[i]
                        sales_val = sum(
                            item["total_sales"]
                            for item in sales_by_month
                            if item["month"] and item["month"].month == i
                        )
                        purchases_val = sum(
                            item["total_purchases"]
                            for item in purchases_by_month
                            if item["month"] and item["month"].month == i
                        )
                        monthly_data.append(
                            {
                                "label": month_label.capitalize(),
                                "ventas": float(sales_val or 0),
                                "compras": float(purchases_val or 0),
                            }
                        )
                    cache[key] = monthly_data

                elif key == "sales_monthly":
                    # Ventas diarias de los últimos 30 días (gráfica de línea)
                    now_local = timezone.localtime(timezone.now())
                    thirty_days_ago = now_local - datetime.timedelta(days=30)
                    start_of_30_days = thirty_days_ago.replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )

                    sales_m_qs = Sale.objects.filter(
                        status=Sale.SaleStatus.COMPLETED,
                        updated_at__gte=start_of_30_days,
                    )
                    if company_id is not None:
                        sales_m_qs = sales_m_qs.filter(company_id=company_id)

                    daily_sales = list(
                        sales_m_qs.annotate(day=TruncDate("updated_at"))
                        .values("day")
                        .annotate(total=Sum("total"))
                        .order_by("day")
                    )

                    sales_map = {
                        item["day"]: float(item["total"] or 0) for item in daily_sales
                    }

                    value_pts = []
                    for offset in range(30, -1, -1):
                        day = (now_local - datetime.timedelta(days=offset)).date()
                        value_pts.append(
                            {
                                "label": day.strftime("%d/%m"),
                                "value": sales_map.get(day, 0),
                            }
                        )
                    cache[key] = value_pts

                elif key == "needs_attention":
                    alerts_query = (
                        Inventory.objects.filter(
                            is_active=True, product__is_active=True
                        )
                        .annotate(
                            alert_priority=Case(
                                When(current_stock=0, then=Value(1)),
                                When(
                                    current_stock__lte=F("minimum_stock"),
                                    then=Value(2),
                                ),
                                When(
                                    current_stock__lte=F("minimum_stock") + 5,
                                    then=Value(3),
                                ),
                                When(
                                    Q(maximum_stock__isnull=False)
                                    & Q(current_stock__gt=F("maximum_stock")),
                                    then=Value(4),
                                ),
                                default=Value(0),
                                output_field=IntegerField(),
                            )
                        )
                        .filter(alert_priority__gt=0)
                        .select_related("product")
                    )
                    if company_id is not None:
                        alerts_query = alerts_query.filter(
                            product__company_id=company_id
                        )

                    total_alerts_count = alerts_query.count()
                    top_alerts = alerts_query.order_by(
                        "alert_priority", "product__name"
                    )[:8]

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

                        items.append(
                            {
                                "label": inv.product.name,
                                "subtitle": f"Stock actual: {inv.current_stock}",
                                "value": lbl,
                                "color": clr,
                                "icon": (
                                    "fas fa-exclamation-circle"
                                    if inv.alert_priority <= 2
                                    else "fas fa-info-circle"
                                ),
                            }
                        )
                    cache[key] = {
                        "value": items,
                        "count": total_alerts_count,
                    }

                elif key == "top_selling_products":
                    thirty_days_ago = timezone.now() - datetime.timedelta(days=30)

                    sale_det_qs = SaleDetail.objects.filter(
                        sale__status=Sale.SaleStatus.COMPLETED,
                        sale__updated_at__gte=thirty_days_ago,
                    )
                    if company_id is not None:
                        sale_det_qs = sale_det_qs.filter(
                            sale__company_id=company_id
                        )

                    rows = (
                        sale_det_qs.values(
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
                        items.append(
                            {
                                "label": row["product__name"] or "Producto",
                                "subtitle": f"Codigo: {row['product__code'] or 'S/N'}",
                                "value": f"{qty:g}",
                                "icon": "fas fa-box",
                                "color": "primary",
                            }
                        )
                    cache[key] = items

                elif key == "latest_sales":
                    sales_latest_qs = Sale.objects.filter(
                        status=Sale.SaleStatus.COMPLETED
                    )
                    if company_id is not None:
                        sales_latest_qs = sales_latest_qs.filter(
                            company_id=company_id
                        )

                    sales = (
                        sales_latest_qs.select_related("customer")
                        .order_by("-updated_at")[:5]
                    )
                    items = []
                    for sale_obj in sales:
                        customer_name = "Consumidor Final"
                        if sale_obj.customer:
                            c = sale_obj.customer
                            customer_name = (
                                getattr(c, "business_name", None)
                                or f"{getattr(c, 'first_name', '') or ''} {getattr(c, 'last_name', '') or ''}".strip()
                                or "Consumidor Final"
                            )

                        if sale_obj.updated_at:
                            local_dt = timezone.localtime(sale_obj.updated_at)
                            date_str = local_dt.strftime("%d/%m/%Y %H:%M")
                        else:
                            date_str = "-"

                        doc_prefix = (
                            "Factura"
                            if sale_obj.sale_type == Sale.SaleType.ADMIN
                            else "POS"
                        )

                        items.append(
                            {
                                "id": sale_obj.sale_number or f"#{sale_obj.pk}",
                                "cliente": customer_name,
                                "monto": float(sale_obj.total or 0),
                                "fecha": date_str,
                                "tipo": doc_prefix,
                            }
                        )
                    cache[key] = items

            timeout = getattr(settings, "CACHE_TIMEOUTS", {}).get(
                "dashboard_metrics", 300
            )
            django_cache.set(cache_key, cache.get(key), timeout=timeout)
            return cache.get(key)

        # Determine which counts are needed (erp_activity re-uses individual counts)
        needs_users_active = (
            "users_active" in widget_set or "erp_activity" in widget_set
        )
        needs_customers_total = (
            "customers_total" in widget_set or "erp_activity" in widget_set
        )
        needs_suppliers_active = (
            "suppliers_active" in widget_set or "erp_activity" in widget_set
        )
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
            "roles_distribution",
            "sales_monthly",
            "purchases_monthly",
            "needs_attention",
            "top_selling_products",
            "latest_sales",
            "inventory_stock_distribution",
        }

        for code in visible_widgets:
            value: Any = 0

            if code == "users_total":
                value = get_cached("users_total")
            elif code == "users_active":
                value = cache["users_active"]
            elif code == "roles_distribution":
                value = get_cached("roles_distribution")
            elif code == "customers_total":
                value = (
                    cache["customers_total"]
                    if "customers_total" in cache
                    else get_cached("customers_total")
                )
            elif code == "customers_recent":
                value = get_cached("customers_recent")
            elif code == "suppliers_active":
                value = (
                    cache["suppliers_active"]
                    if "suppliers_active" in cache
                    else get_cached("suppliers_active")
                )
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
                value = get_cached("purchases_monthly")

            elif code == "sales_monthly":
                value = get_cached("sales_monthly")

            elif code == "erp_activity":
                inventory_val = cache.get("inventory_total_value", 0)
                formatted_inventory_val = f"${inventory_val:,.0f}".replace(",", ".")

                value = [
                    {
                        "label": "Usuarios activos",
                        "value": cache["users_active"],
                        "icon": "fas fa-user-check",
                        "color": "success",
                    },
                    {
                        "label": "Clientes",
                        "value": cache["customers_total"],
                        "icon": "fas fa-user-tie",
                        "color": "info",
                    },
                    {
                        "label": "Proveedores",
                        "value": cache["suppliers_active"],
                        "icon": "fas fa-truck",
                        "color": "secondary",
                    },
                    {
                        "label": "Valor inventario actual",
                        "value": formatted_inventory_val,
                        "icon": "fas fa-boxes",
                        "color": "primary",
                    },
                ]
            elif code == "needs_attention":
                attn_data = get_cached("needs_attention") or {}
                metrics.append(
                    {
                        "code": code,
                        "value": attn_data.get("value", []),
                        "count": attn_data.get("count", 0),
                    }
                )
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

        # ── Widgets forzados (fuera del loop, una sola vez) ──
        forced_widgets = [
            "sales_summary",
            "inventory_stock_distribution",
            "payment_methods",
            "top_selling_products",
            "latest_sales",
            "products_critical",
        ]

        existing_codes = {m["code"] for m in metrics}
        for forced_code in forced_widgets:
            if forced_code not in existing_codes:
                metrics.append(
                    {
                        "code": forced_code,
                        "value": get_cached(forced_code),
                    }
                )

        return metrics
