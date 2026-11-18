from django.core.cache import cache
from django.db.models import QuerySet

from apps.company_info.models import CompanyInfo
from apps.core.selectors.base_selector import BaseSelector


class CompanyInfoSelector(BaseSelector[CompanyInfo]):
    """
    Selector encargado de realizar consultas de lectura relacionadas
    con la información de la empresa.

    La clase no modifica información y no contiene lógica de
    persistencia.
    """

    def __init__(self):
        super().__init__(CompanyInfo)

    def get_queryset(self, include_deleted: bool = False) -> QuerySet[CompanyInfo]:
        """
        Retorna el queryset base de empresas ordenadas por ID.
        """
        return (
            super().get_queryset(include_deleted=include_deleted).order_by("id_company")
        )

    @staticmethod
    def get_current(company_id: int | None = None) -> CompanyInfo | None:
        """
        Obtiene la información de la empresa activa del contexto.
        Soporta contexto Multi-Tenant por company_id o contextvars thread-safe.
        """
        if not company_id:
            from apps.core.context import get_current_company_id

            company_id = get_current_company_id()

        if company_id:
            cache_key = f"company_info_{company_id}"
            cached_val = cache.get(cache_key)
            if cached_val is not None:
                return cached_val

            val = CompanyInfoSelector().get_active().filter(pk=company_id).first()
            if val:
                cache.set(cache_key, val, timeout=3600)  # 1 hora
            return val

        cache_key = "company_info_current"
        cached_val = cache.get(cache_key)

        if cached_val is not None:
            return cached_val

        val = CompanyInfoSelector().get_active().first()

        if val:
            cache.set(cache_key, val, timeout=3600)  # 1 hora
        return val

    @staticmethod
    def get_by_id(company_id: int) -> CompanyInfo | None:
        """
        Obtiene la información de empresa por su identificador.
        """
        return CompanyInfoSelector().get_active().filter(pk=company_id).first()

    @staticmethod
    def get_all(
        qs=None,
        include_deleted: bool = False,
        company_id=None,
        **kwargs,
    ) -> QuerySet[CompanyInfo]:
        """
        Obtiene todos los registros de empresa activos.
        """
        if qs is not None:
            return qs.filter(is_active=True) if not include_deleted else qs
        return (
            CompanyInfoSelector().get_queryset(include_deleted=include_deleted)
            if include_deleted
            else CompanyInfoSelector().get_queryset().filter(is_active=True)
        )

    @staticmethod
    def exists() -> bool:
        """
        Verifica si existe al menos una empresa configurada.
        """
        return CompanyInfoSelector().get_active().exists()
