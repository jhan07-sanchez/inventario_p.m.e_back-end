"""
inventario-pme Navigation Builder
============================

Construye el árbol jerárquico de navegación (sidebar) filtrado
según los permisos efectivos del usuario.

Responsabilidad única: transformar el catálogo plano del
``SecurityRegistry`` en una estructura de árbol lista para
que el frontend renderice directamente.

Estructura de salida::

    [
        {
            "id": "dashboard",
            "title": "Dashboard",
            "icon": "fas fa-home",
            "route": "index.php",
            "permission": "dashboard.view",
            "order": 0
        },
        {
            "id": "security",
            "title": "Seguridad",
            "icon": "fas fa-lock",
            "order": 1,
            "children": [
                {
                    "id": "users",
                    "title": "Usuarios",
                    "icon": "fas fa-users",
                    "route": "views/pages/usuarios/index.php",
                    "permission": "users.view",
                    "order": 1
                },
                ...
            ]
        }
    ]
"""

from __future__ import annotations

from apps.core.security.registry import SecurityRegistry


class NavigationBuilder:
    """
    Builder que construye la navegación jerárquica filtrada
    por los permisos efectivos del usuario.
    """

    @staticmethod
    def build(effective_permissions: dict[str, bool]) -> list[dict]:
        """
        Construye el árbol de navegación completo.

        Lógica:
            1. Recolectar módulos raíz (sin parent) que el usuario
               pueda ver.
            2. Recolectar grupos que contengan al menos un módulo
               hijo visible para el usuario.
            3. Ensamblar el árbol ordenado.

        Args:
            effective_permissions:
                Diccionario ``{código: bool}`` con los permisos
                efectivos del usuario.

        Returns:
            Lista de nodos de navegación con children anidados.
        """

        navigation: list[dict] = []

        # ── Módulos raíz (sin parent) ─────────────────────────
        root_modules = SecurityRegistry.get_modules_by_parent(None)

        for module in root_modules:
            if NavigationBuilder._user_can_access_module(
                module.permissions,
                effective_permissions,
            ):
                navigation.append(NavigationBuilder._build_module_node(module))

        # ── Grupos con hijos ──────────────────────────────────
        for group in SecurityRegistry.get_all_groups():
            children = NavigationBuilder._build_group_children(
                group.group_id,
                effective_permissions,
            )

            # Solo incluir el grupo si tiene al menos un hijo visible.
            if children:
                navigation.append(
                    {
                        "id": group.group_id,
                        "title": group.label,
                        "icon": group.icon,
                        "order": group.order,
                        "children": children,
                    }
                )

        # Ordenar todo el árbol raíz por order.
        navigation.sort(key=lambda item: item.get("order", 0))

        return navigation

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    @staticmethod
    def _build_module_node(module) -> dict:
        """Construye el nodo de navegación de un módulo."""

        # El permiso de vista es el que controla la visibilidad
        # en la navegación. Convención: ``module_id.view``.
        view_permission = f"{module.module_id}.view"

        node: dict = {
            "id": module.module_id,
            "title": module.label,
            "icon": module.icon,
            "route": module.route,
            "permission": view_permission,
            "order": module.order,
            "children": [],
        }

        return node

    @staticmethod
    def _build_group_children(
        group_id: str,
        effective_permissions: dict[str, bool],
    ) -> list[dict]:
        """
        Construye la lista de hijos de un grupo, filtrada por
        permisos.
        """

        children: list[dict] = []
        group_modules = SecurityRegistry.get_modules_by_parent(group_id)

        for module in group_modules:
            if NavigationBuilder._user_can_access_module(
                module.permissions,
                effective_permissions,
            ):
                children.append(NavigationBuilder._build_module_node(module))

        return children

    @staticmethod
    def _user_can_access_module(
        module_permissions: dict[str, str],
        effective_permissions: dict[str, bool],
    ) -> bool:
        """
        Un usuario puede acceder a un módulo si tiene al menos
        un permiso activo de ese módulo.
        """

        return any(
            effective_permissions.get(perm_code, False)
            for perm_code in module_permissions
        )
