"""
Servicio de dominio para construir el catalogo
dinamico de permisos y acciones de inventario-pme.
"""
from __future__ import annotations

from apps.core.security.registry import SecurityRegistry




class PermissionCatalogService:
    """
    Servicio para consultar el catálogo dinámico de seguridad.
    """

    @staticmethod
    def get_catalog() -> list[dict[str, object]]:
        """
        Obtiene el catálogo registrado en SecurityRegistry.
        """

        return SecurityRegistry.get_permission_catalog()
