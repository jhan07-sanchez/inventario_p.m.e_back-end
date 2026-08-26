"""
inventario-pme Action Builder
=======================

Agrupa las acciones efectivas del usuario por módulo para
facilitar su consumo desde el frontend.
"""

from __future__ import annotations

from apps.core.security.registry import SecurityRegistry


class ActionBuilder:
    """
    Builder que construye la estructura de acciones agrupadas
    por módulo para controlar funcionalidades granulares en el frontend
    (como botones de Exportar, Aprobar, Imprimir, etc).
    """

    @staticmethod
    def build(effective_permissions: dict[str, bool]) -> dict[str, dict[str, bool]]:
        """
        Agrupa las acciones efectivas por módulo.

        Args:
            effective_permissions:
                Diccionario plano con todos los códigos de seguridad
                evaluados (ej. {"users.view": True, "users.export": False}).

        Returns:
            Diccionario anidado de acciones:
            {
                "users": {
                    "export": True,
                    "import": False
                }
            }
        """

        grouped_actions: dict[str, dict[str, bool]] = {}

        # Obtenemos solo los códigos registrados como acciones,
        # ignorando los permisos CRUD normales.
        valid_action_codes = set(SecurityRegistry.get_all_action_codes())

        for code, has_access in effective_permissions.items():
            if code in valid_action_codes:
                try:
                    module_name, action_name = code.split(".", 1)
                except ValueError:
                    # Ignorar si no sigue el formato modulo.accion
                    continue

                if module_name not in grouped_actions:
                    grouped_actions[module_name] = {}

                grouped_actions[module_name][action_name] = has_access

        return grouped_actions
