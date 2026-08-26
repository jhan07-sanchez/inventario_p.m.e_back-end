"""
inventario-pme Permission Builder
===========================

Agrupa los permisos efectivos del usuario por módulo para
facilitar su consumo desde el frontend.
"""

from __future__ import annotations

from apps.core.security.registry import SecurityRegistry


class PermissionBuilder:
    """
    Builder que construye la estructura de permisos agrupados
    por módulo para entregar al frontend.
    """

    @staticmethod
    def build(effective_permissions: dict[str, bool]) -> dict[str, dict[str, bool]]:
        """
        Agrupa los permisos efectivos (excluyendo acciones) por módulo.

        Args:
            effective_permissions:
                Diccionario plano con todos los códigos de seguridad
                evaluados (ej. {"users.view": True, "users.export": False}).

        Returns:
            Diccionario anidado de permisos:
            {
                "users": {
                    "view": True,
                    "create": False
                }
            }
        """

        grouped_permissions: dict[str, dict[str, bool]] = {}

        # Obtenemos solo los códigos registrados como permisos (CRUD),
        # ignorando las acciones granulares.
        valid_permission_codes = set(SecurityRegistry.get_all_permission_codes())

        for code, has_access in effective_permissions.items():
            if code in valid_permission_codes:
                try:
                    module_name, perm_name = code.split(".", 1)
                except ValueError:
                    # Ignorar si no sigue el formato modulo.permiso
                    continue

                if module_name not in grouped_permissions:
                    grouped_permissions[module_name] = {}

                grouped_permissions[module_name][perm_name] = has_access

        return grouped_permissions
