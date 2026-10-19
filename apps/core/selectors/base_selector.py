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

    def get_queryset(self, include_deleted: bool = False) -> QuerySet[ModelType]:
        """
        Origen de toda consulta.
        Ideal para inyectar filtros globales (ej. multi-tenant).
        Si include_deleted=True y el modelo posee all_objects, consulta all_objects.
        """
        if include_deleted and hasattr(self.model, "all_objects"):
            return self.model.all_objects.all()
        return self.model.objects.all()

    def get_all(
        self,
        qs: Optional[QuerySet[ModelType]] = None,
        include_deleted: bool = False,
    ) -> QuerySet[ModelType]:
        return qs if qs is not None else self.get_queryset(include_deleted=include_deleted)

    def get_active(
        self, qs: Optional[QuerySet[ModelType]] = None
    ) -> QuerySet[ModelType]:
        base_qs = self.get_all(qs)
        # Duck typing para validar si el modelo usa is_active
        if hasattr(self.model, "is_active") or hasattr(self.model(), "is_active"):
            return base_qs.filter(is_active=True)
        return base_qs

    def get_inactive(
        self, qs: Optional[QuerySet[ModelType]] = None
    ) -> QuerySet[ModelType]:
        base_qs = self.get_all(qs, include_deleted=True)
        if hasattr(self.model, "is_active") or hasattr(self.model(), "is_active"):
            return base_qs.filter(is_active=False)
        return base_qs

    def get_by_id(
        self,
        record_id: Any,
        qs: Optional[QuerySet[ModelType]] = None,
        include_deleted: bool = False,
    ) -> Optional[ModelType]:
        try:
            return self.get_all(qs, include_deleted=include_deleted).get(pk=record_id)
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
