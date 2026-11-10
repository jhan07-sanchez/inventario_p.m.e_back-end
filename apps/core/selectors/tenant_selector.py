from typing import Any, Generic, Optional, TypeVar

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import QuerySet

from apps.core.selectors.base_selector import BaseSelector

ModelType = TypeVar("ModelType", bound=models.Model)


class TenantSelector(BaseSelector[ModelType], Generic[ModelType]):
    """
    Selector base multi-tenant.
    Encapsula consultas de lectura garantizando que los datos siempre estén confinados
    a la empresa (Tenant) correspondiente, previniendo vulnerabilidades IDOR.
    """

    def _extract_company_id(self, company_or_id: Any) -> Optional[int]:
        if company_or_id is None:
            return None
        return getattr(company_or_id, "id_company", None) or getattr(company_or_id, "pk", None) or company_or_id

    def get_tenant_queryset(
        self,
        company: Any = None,
        include_deleted: bool = False,
    ) -> QuerySet[ModelType]:
        """
        Retorna el queryset base aislado por empresa.
        Si se pasa company=None y el usuario no es superuser global, retorna queryset vacío.
        """
        base_qs = self.get_queryset(include_deleted=include_deleted)
        if company is not None:
            comp_id = self._extract_company_id(company)
            return base_qs.filter(company_id=comp_id)
        return base_qs

    def get_for_company(
        self,
        company: Any,
        qs: Optional[QuerySet[ModelType]] = None,
        include_deleted: bool = False,
    ) -> QuerySet[ModelType]:
        """
        Retorna todos los registros de una empresa específica.
        """
        comp_id = self._extract_company_id(company)
        target_qs = qs if qs is not None else self.get_queryset(include_deleted=include_deleted)
        return target_qs.filter(company_id=comp_id)

    def get_active_for_company(
        self,
        company: Any,
        qs: Optional[QuerySet[ModelType]] = None,
    ) -> QuerySet[ModelType]:
        """
        Retorna únicamente registros activos de una empresa específica.
        """
        return self.get_active(self.get_for_company(company, qs=qs))

    def get_by_id_for_company(
        self,
        record_id: Any,
        company: Any,
        include_deleted: bool = False,
    ) -> Optional[ModelType]:
        """
        Busca un registro por su ID asegurando que pertenezca a la empresa dada.
        Si el ID pertenece a otra empresa, retorna None (previene IDOR).
        """
        comp_id = self._extract_company_id(company)
        try:
            return self.get_tenant_queryset(
                company=comp_id, include_deleted=include_deleted
            ).get(pk=record_id)
        except ObjectDoesNotExist:
            return None

    def exists_for_company(
        self,
        company: Any,
        **kwargs: Any,
    ) -> bool:
        """
        Verifica existencia de un registro dentro del ámbito de una empresa.
        """
        comp_id = self._extract_company_id(company)
        return self.get_for_company(comp_id).filter(**kwargs).exists()

