from collections.abc import Sequence
from typing import Any, Generic, Optional, TypeVar

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Q, QuerySet

ModelType = TypeVar("ModelType", bound=models.Model)


class BaseSelector(Generic[ModelType]):
    """
    Selector base genérico para encapsular y reutilizar todas las lógicas
    de consultas de lectura (Queries) hacia la Base de Datos.
    """

    def __init__(self, model: type[ModelType]):
        self.model = model

    def _apply_company_filter(
        self, qs: QuerySet[ModelType], company_id: Any = None
    ) -> QuerySet[ModelType]:
        """Aplica filtro tenant al queryset si el modelo posee relación directa o indirecta."""
        if company_id is None:
            return qs

        comp_id = (
            getattr(company_id, "id_company", None)
            or getattr(company_id, "pk", None)
            or company_id
        )
        try:
            comp_id = int(comp_id)
        except (ValueError, TypeError):
            return qs

        fields = [f.name for f in self.model._meta.fields]

        if "company" in fields or "company_id" in fields or hasattr(self.model, "company"):
            return qs.filter(company_id=comp_id)

        if self.model._meta.app_label == "inventory" and self.model.__name__ == "Inventory":
            return qs.filter(product__company_id=comp_id)

        if self.model._meta.app_label == "inventory" and self.model.__name__ == "InventoryMovement":
            return qs.filter(inventory__product__company_id=comp_id)

        if self.model._meta.app_label == "sales" and self.model.__name__ == "SaleDetail":
            return qs.filter(sale__company_id=comp_id)

        if self.model._meta.app_label == "purchases" and self.model.__name__ == "PurchaseDetail":
            return qs.filter(purchase__company_id=comp_id)

        if self.model._meta.app_label == "invoices" and self.model.__name__ == "InvoiceItem":
            return qs.filter(invoice__company_id=comp_id)

        if self.model._meta.app_label == "cash" and self.model.__name__ in ("CashMovement", "Payment"):
            return qs.filter(cash_session__company_id=comp_id)

        if self.model._meta.app_label == "finance":
            if self.model.__name__ in ("FinancialMovement", "FinancialReconciliation"):
                return qs.filter(account__company_id=comp_id)
            if self.model.__name__ == "FinancialTransfer":
                return qs.filter(source_account__company_id=comp_id)

        if self.model._meta.app_label == "users" and self.model.__name__ == "User":
            return qs.filter(memberships__company_id=comp_id, memberships__is_active=True).distinct()

        return qs

    def get_queryset(
        self, include_deleted: bool = False, company_id: Any = None
    ) -> QuerySet[ModelType]:
        """
        Origen de toda consulta.
        Si include_deleted=True y el modelo posee all_objects, consulta all_objects.
        Si company_id es provisto, confina la consulta al tenant correspondiente.
        """
        if include_deleted and hasattr(self.model, "all_objects"):
            qs = self.model.all_objects.all()
        else:
            qs = self.model.objects.all()
        return self._apply_company_filter(qs, company_id=company_id)

    def get_all(
        self,
        qs: Optional[QuerySet[ModelType]] = None,
        include_deleted: bool = False,
        company_id: Any = None,
    ) -> QuerySet[ModelType]:
        base_qs = qs if qs is not None else self.get_queryset(include_deleted=include_deleted)
        return self._apply_company_filter(base_qs, company_id=company_id)

    def get_active(
        self, qs: Optional[QuerySet[ModelType]] = None, company_id: Any = None
    ) -> QuerySet[ModelType]:
        base_qs = self.get_all(qs, company_id=company_id)
        # Duck typing para validar si el modelo usa is_active
        if hasattr(self.model, "is_active") or hasattr(self.model(), "is_active"):
            return base_qs.filter(is_active=True)
        return base_qs

    def get_inactive(
        self, qs: Optional[QuerySet[ModelType]] = None, company_id: Any = None
    ) -> QuerySet[ModelType]:
        base_qs = self.get_all(qs, include_deleted=True, company_id=company_id)
        if hasattr(self.model, "is_active") or hasattr(self.model(), "is_active"):
            return base_qs.filter(is_active=False)
        return base_qs

    def get_by_id(
        self,
        record_id: Any,
        qs: Optional[QuerySet[ModelType]] = None,
        include_deleted: bool = False,
        company_id: Any = None,
    ) -> Optional[ModelType]:
        try:
            base_qs = self.get_all(qs, include_deleted=include_deleted, company_id=company_id)
            return base_qs.get(pk=record_id)
        except ObjectDoesNotExist:
            return None

    def exists(self, qs: Optional[QuerySet[ModelType]] = None, **kwargs: Any) -> bool:
        return self.get_all(qs).filter(**kwargs).exists()

    def count(self, qs: Optional[QuerySet[ModelType]] = None, **kwargs: Any) -> int:
        base_qs = self.get_all(qs)
        if kwargs:
            return base_qs.filter(**kwargs).count()
        return base_qs.count()

    def filter(
        self, qs: Optional[QuerySet[ModelType]] = None, **kwargs: Any
    ) -> QuerySet[ModelType]:
        return self.get_all(qs).filter(**kwargs)

    def search(
        self,
        search_fields: Sequence[str],
        query: str,
        qs: Optional[QuerySet[ModelType]] = None,
    ) -> QuerySet[ModelType]:
        """
        Búsqueda dinámica tipo LIKE (icontains) basada en los campos provistos.
        """
        base_qs = self.get_all(qs)
        if not query or not search_fields:
            return base_qs

        q_objects = Q()
        for field in search_fields:
            q_objects |= Q(**{f"{field}__icontains": query})

        return base_qs.filter(q_objects)

    def order_by(
        self, *fields: str, qs: Optional[QuerySet[ModelType]] = None
    ) -> QuerySet[ModelType]:
        return self.get_all(qs).order_by(*fields)

    def apply_optimizations(
        self,
        select_related: Optional[Sequence[str]] = None,
        prefetch_related: Optional[Sequence[str]] = None,
        qs: Optional[QuerySet[ModelType]] = None,
    ) -> QuerySet[ModelType]:
        """
        Aplica optimizaciones para evitar N+1 Queries.
        - select_related: para FKs y OneToOne.
        - prefetch_related: para ManyToMany y Reverse FKs.
        """
        base_qs = self.get_all(qs)

        if select_related:
            base_qs = base_qs.select_related(*select_related)

        if prefetch_related:
            base_qs = base_qs.prefetch_related(*prefetch_related)

        return base_qs
