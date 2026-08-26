"""
inventario-pme Dashboard Builder
===========================

Genera la configuración dinámica del dashboard según los
permisos efectivos del usuario.

Responsabilidad única: determinar qué widgets del dashboard
debe ver cada usuario basándose en sus permisos.

Estructura de salida::

    {
        "widgets": [
            "sales_summary",
            "inventory_alerts",
            "customers_recent"
        ]
    }

Cada módulo registra opcionalmente una lista de ``widgets``
en el ``SecurityRegistry``. Este builder los filtra según
los permisos del usuario.
"""

from __future__ import annotations

from apps.core.security.registry import SecurityRegistry
from apps.core.security.services.dashboard_metrics_service import (
    DashboardMetricsService,
)


class DashboardBuilder:
    """
    Builder que construye la configuración del dashboard
    filtrada por permisos efectivos.
    """

    @staticmethod
    def build(effective_permissions: dict[str, bool]) -> dict:
        """
        Construye la configuración del dashboard.

        Lógica:
            Para cada módulo registrado, si el usuario tiene al
            menos un permiso activo en ese módulo, se incluyen
            los widgets del módulo en el dashboard.

        Args:
            effective_permissions:
                Diccionario ``{código: bool}`` con los permisos
                efectivos del usuario.

        Returns:
            Diccionario con la clave ``"widgets"`` conteniendo
            la lista de IDs de widgets visibles.
        """

        visible_widgets: list[str] = []

        for module in SecurityRegistry.get_all_modules():
            # Solo incluir widgets si el usuario tiene acceso
            # al módulo (al menos un permiso activo).
            if not module.widgets:
                continue

            has_access = any(
                effective_permissions.get(perm_code, False)
                for perm_code in module.permissions
            )

            if has_access:
                visible_widgets.extend(module.widgets)

        widgets_data = DashboardMetricsService.get_metrics(visible_widgets)

        return {"widgets": widgets_data}
