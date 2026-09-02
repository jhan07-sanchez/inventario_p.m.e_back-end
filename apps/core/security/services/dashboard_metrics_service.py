"""
Servicio de métricas para el Dashboard.
"""

from typing import Any
from django.utils import timezone

from apps.users.models import User, Role
from apps.customers.models import Customer
from apps.suppliers.models import Supplier


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
            return cache.get(key)

        # Determine which counts are needed (erp_activity re-uses individual counts)
        needs_users_active = "users_active" in widget_set or "erp_activity" in widget_set
        needs_customers_total = "customers_total" in widget_set or "erp_activity" in widget_set
        needs_suppliers_active = "suppliers_active" in widget_set or "erp_activity" in widget_set

        if needs_users_active:
            get_cached("users_active")
        if needs_customers_total:
            get_cached("customers_total")
        if needs_suppliers_active:
            get_cached("suppliers_active")

        # ── Construir métricas ──

        metrics = []

        list_widgets = {
            "roles_distribution", "sales_monthly", "purchases_monthly",
            "needs_attention", "top_selling_products", "latest_sales",
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
                value = cache["customers_total"] if "customers_total" in cache else get_cached("customers_total")
            elif code == "customers_recent":
                value = get_cached("customers_recent")
            elif code == "suppliers_active":
                value = cache["suppliers_active"] if "suppliers_active" in cache else get_cached("suppliers_active")
            elif code == "erp_activity":
                value = [
                    {"label": "Usuarios activos", "value": cache["users_active"], "icon": "fas fa-user-check", "color": "success"},
                    {"label": "Clientes", "value": cache["customers_total"], "icon": "fas fa-user-tie", "color": "info"},
                    {"label": "Proveedores", "value": cache["suppliers_active"], "icon": "fas fa-truck", "color": "secondary"},
                ]
            else:
                if code in list_widgets:
                    value = []
                else:
                    value = 0

            metrics.append({"code": code, "value": value})

        return metrics
