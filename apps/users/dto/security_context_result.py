from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SecurityContextResult:
    """
    DTO del contexto de seguridad del usuario autenticado.

    Agrupa roles, permisos efectivos, acciones, navegación
    y dashboard. Cada endpoint de seguridad expone únicamente
    la porción que le corresponde.
    """

    roles: list[str] = field(default_factory=list)
    permissions: dict[str, dict[str, bool]] = field(default_factory=dict)
    actions: dict[str, dict[str, bool]] = field(default_factory=dict)
    navigation: list[dict] = field(default_factory=list)
    dashboard: dict = field(default_factory=dict)
    companies: list[dict] = field(default_factory=list)
    active_company: dict | None = None
