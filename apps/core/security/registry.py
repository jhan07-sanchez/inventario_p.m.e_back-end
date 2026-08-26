"""
inventario-pme Security Registry v1
==============================

Registro centralizado en memoria de todos los módulos, permisos,
navegación jerárquica, acciones y widgets del sistema.

Cada aplicación del ERP registra aquí sus definiciones al momento
de importación (normalmente en ``AppConfig.ready()``).

Diseñado como Singleton de clase — no se instancia.

Conceptos clave:
    - **Grupo**: Sección contenedora del sidebar que agrupa módulos
      relacionados (ej. "Seguridad" agrupa Users + Roles).
    - **Módulo**: Entidad funcional del ERP con permisos, ruta,
      acciones y widgets propios.
    - **Acción**: Operación granular sobre un módulo que va más allá
      del CRUD básico (export, import, approve, print, etc.).
    - **Widget**: Componente visual del dashboard asociado a un módulo.

Principios:
    - Open/Closed: agregar un módulo nuevo NO requiere modificar
      este archivo.
    - Single Responsibility: solo administra el catálogo.

Ejemplo de uso::

    SecurityRegistry.register_group(
        group_id="security",
        label="Seguridad",
        icon="fas fa-lock",
        order=1,
    )

    SecurityRegistry.register_module(
        module_id="users",
        label="Usuarios",
        icon="fas fa-users",
        route="/views/users/index.php",
        parent="security",
        permissions={
            "users.view": "Ver usuarios",
            "users.create": "Crear usuarios",
        },
        actions={
            "users.export": "Exportar usuarios",
            "users.import": "Importar usuarios",
        },
        widgets=["users_total", "users_active"],
        order=1,
    )
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class GroupDefinition:
    """
    Representa una sección contenedora del sidebar.

    Los grupos no tienen ruta propia ni permisos directos;
    sirven para agrupar módulos relacionados visualmente.

    Attributes:
        group_id:
            Identificador único del grupo (ej. ``"security"``).
        label:
            Nombre legible para el sidebar.
        icon:
            Clase CSS del ícono.
        order:
            Posición de aparición en la navegación.
    """

    group_id: str
    label: str
    icon: str
    order: int = 0


@dataclass(frozen=True, slots=True)
class ModuleDefinition:
    """
    Representa la definición inmutable de un módulo registrado
    en el sistema de seguridad.

    Attributes:
        module_id:
            Identificador único del módulo (ej. ``"users"``).
        label:
            Nombre legible para mostrar en el sidebar.
        icon:
            Clase de ícono (FontAwesome, Tabler, etc.).
        route:
            Ruta del frontend para este módulo.
        parent:
            ID del grupo padre (``None`` si es raíz).
        permissions:
            Diccionario ``{código_permiso: descripción}`` para CRUD.
        actions:
            Diccionario ``{código_acción: descripción}`` para
            operaciones granulares (export, import, approve, etc.).
        widgets:
            Lista de IDs de widgets que este módulo aporta
            al dashboard.
        order:
            Orden de aparición dentro de su grupo o en raíz.
    """

    module_id: str
    label: str
    icon: str
    route: str = ""
    parent: str | None = None
    permissions: dict[str, str] = field(default_factory=dict)
    actions: dict[str, str] = field(default_factory=dict)
    widgets: list[str] = field(default_factory=list)
    order: int = 0


class SecurityRegistry:
    """
    Registro global (Singleton de clase) que almacena los módulos,
    grupos, permisos, acciones y widgets disponibles en el ERP.

    Thread-safe gracias a ``threading.Lock``.
    """

    _groups: ClassVar[dict[str, GroupDefinition]] = {}
    _modules: ClassVar[dict[str, ModuleDefinition]] = {}
    _all_permissions: ClassVar[dict[str, str]] = {}
    _all_actions: ClassVar[dict[str, str]] = {}
    _lock: ClassVar[threading.Lock] = threading.Lock()

    # ------------------------------------------------------------------
    # Registro de grupos
    # ------------------------------------------------------------------

    @classmethod
    def register_group(
        cls,
        *,
        group_id: str,
        label: str,
        icon: str = "",
        order: int = 0,
    ) -> None:
        """
        Registra una sección contenedora para la navegación.

        Args:
            group_id:
                Identificador único del grupo (ej. ``"security"``).
            label:
                Nombre legible para el sidebar.
            icon:
                Clase CSS del ícono.
            order:
                Posición de aparición (menor = primero).

        Raises:
            ValueError:
                Si ``group_id`` ya fue registrado.
        """

        with cls._lock:
            if group_id in cls._groups:
                raise ValueError(
                    f"El grupo '{group_id}' ya se encuentra registrado "
                    f"en SecurityRegistry."
                )

            cls._groups[group_id] = GroupDefinition(
                group_id=group_id,
                label=label,
                icon=icon,
                order=order,
            )

    # ------------------------------------------------------------------
    # Registro de módulos
    # ------------------------------------------------------------------

    @classmethod
    def register_module(
        cls,
        *,
        module_id: str,
        label: str,
        icon: str = "",
        route: str = "",
        parent: str | None = None,
        permissions: dict[str, str] | None = None,
        actions: dict[str, str] | None = None,
        widgets: list[str] | None = None,
        order: int = 0,
    ) -> None:
        """
        Registra un nuevo módulo con todos sus metadatos.

        Args:
            module_id:
                Identificador único del módulo.
            label:
                Nombre legible para el sidebar.
            icon:
                Clase CSS del ícono.
            route:
                Ruta del frontend (ej. ``"/views/users/index.php"``).
            parent:
                ID del grupo padre para jerarquía del sidebar.
                ``None`` si el módulo es raíz.
            permissions:
                ``{código: descripción}`` para permisos CRUD.
            actions:
                ``{código: descripción}`` para acciones granulares.
            widgets:
                Lista de IDs de widgets del dashboard.
            order:
                Posición de aparición dentro de su grupo.

        Raises:
            ValueError:
                Si ``module_id`` ya fue registrado.
        """

        perms = permissions or {}
        acts = actions or {}
        wgts = widgets or []

        with cls._lock:
            if module_id in cls._modules:
                raise ValueError(
                    f"El módulo '{module_id}' ya se encuentra registrado "
                    f"en SecurityRegistry."
                )

            cls._modules[module_id] = ModuleDefinition(
                module_id=module_id,
                label=label,
                icon=icon,
                route=route,
                parent=parent,
                permissions=perms,
                actions=acts,
                widgets=wgts,
                order=order,
            )

            cls._all_permissions.update(perms)
            cls._all_actions.update(acts)

    # ------------------------------------------------------------------
    # Consultas — Permisos
    # ------------------------------------------------------------------

    @classmethod
    def get_all_permission_codes(cls) -> list[str]:
        """Devuelve todos los códigos de permisos registrados."""

        with cls._lock:
            return list(cls._all_permissions.keys())

    @classmethod
    def get_all_action_codes(cls) -> list[str]:
        """Devuelve todos los códigos de acciones registrados."""

        with cls._lock:
            return list(cls._all_actions.keys())

    @classmethod
    def get_all_security_codes(cls) -> list[str]:
        """
        Devuelve todos los códigos (permisos + acciones).

        Estos son todos los códigos que se almacenan en el
        JSONField ``permissions`` del modelo ``Role``.
        """

        with cls._lock:
            return list(cls._all_permissions.keys()) + list(cls._all_actions.keys())

    @classmethod
    def is_valid_permission(cls, permission_code: str) -> bool:
        """Verifica si un código está registrado."""

        with cls._lock:
            return (
                permission_code in cls._all_permissions
                or permission_code in cls._all_actions
            )

    # ------------------------------------------------------------------
    # Consultas — Módulos y grupos
    # ------------------------------------------------------------------

    @classmethod
    def get_all_modules(cls) -> list[ModuleDefinition]:
        """Devuelve todos los módulos ordenados por ``order``."""

        with cls._lock:
            return sorted(
                cls._modules.values(),
                key=lambda m: m.order,
            )

    @classmethod
    def get_all_groups(cls) -> list[GroupDefinition]:
        """Devuelve todos los grupos ordenados por ``order``."""

        with cls._lock:
            return sorted(
                cls._groups.values(),
                key=lambda g: g.order,
            )

    @classmethod
    def get_module(cls, module_id: str) -> ModuleDefinition | None:
        """Devuelve un módulo por su ID o ``None``."""

        with cls._lock:
            return cls._modules.get(module_id)

    @classmethod
    def get_group(cls, group_id: str) -> GroupDefinition | None:
        """Devuelve un grupo por su ID o ``None``."""

        with cls._lock:
            return cls._groups.get(group_id)

    @classmethod
    def get_modules_by_parent(
        cls,
        parent: str | None,
    ) -> list[ModuleDefinition]:
        """
        Devuelve los módulos que pertenecen a un grupo padre
        específico, ordenados por ``order``.
        """

        with cls._lock:
            return sorted(
                [m for m in cls._modules.values() if m.parent == parent],
                key=lambda m: m.order,
            )

    # ------------------------------------------------------------------
    # Utilidades (testing / reset)
    # ------------------------------------------------------------------

    @classmethod
    def _reset(cls) -> None:
        """Limpia todo el registro. **Solo para tests.**"""

        with cls._lock:
            cls._groups.clear()
            cls._modules.clear()
            cls._all_permissions.clear()
            cls._all_actions.clear()

    @classmethod
    def get_permission_catalog(
        cls,
    ) -> list[dict[str, object]]:
        """
        Devuelve el catálogo de permisos y acciones registrados
        actualmente en SecurityRegistry.
        """

        with cls._lock:
            modules = sorted(
                cls._modules.values(),
                key=lambda module: module.order,
            )

            catalog = []

            for module in modules:
                catalog.append(
                    {
                        "module_id": module.module_id,
                        "label": module.label,
                        "icon": module.icon,
                        "parent": module.parent,
                        "permissions": [
                            {
                                "code": code,
                                "description": description,
                            }
                            for code, description
                            in module.permissions.items()
                        ],
                        "actions": [
                            {
                                "code": code,
                                "description": description,
                            }
                            for code, description
                            in module.actions.items()
                        ],
                    }
                )

            return catalog
