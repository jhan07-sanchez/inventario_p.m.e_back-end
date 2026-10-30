from django.core.cache import cache
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from apps.configuration.models import GlobalParameter
from apps.core.selectors.base_selector import BaseSelector


class GlobalParameterSelector(BaseSelector[GlobalParameter]):
    """
    Selector encargado de las consultas relacionadas
    con los parámetros globales.

    Los selectors contienen exclusivamente lógica de lectura.
    """

    def __init__(self):
        super().__init__(GlobalParameter)

    def get_queryset(self, include_deleted: bool = False) -> QuerySet[GlobalParameter]:
        """
        Retorna el queryset base de parámetros.
        """
        return super().get_queryset(include_deleted=include_deleted).order_by("key")

    @staticmethod
    def get_parameters(include_deleted: bool = False) -> QuerySet[GlobalParameter]:
        """
        Retorna los parámetros globales (activos por defecto).
        """
        if include_deleted:
            return GlobalParameterSelector().get_all(include_deleted=True)
        return GlobalParameterSelector().get_active()

    @staticmethod
    def get_parameter_by_id(
        param_id: int, include_deleted: bool = False
    ) -> GlobalParameter:
        """
        Obtiene un parámetro por su identificador.
        """
        return get_object_or_404(
            GlobalParameterSelector().get_queryset(include_deleted=include_deleted),
            pk=param_id,
        )

    @staticmethod
    def get_by_key(key: str) -> GlobalParameter | None:
        """
        Obtiene un parámetro por su clave (key).
        Normaliza la clave y utiliza caché para máximo rendimiento.
        """
        if not key:
            return None

        norm_key = key.strip().upper()
        cache_key = f"global_param_{norm_key}"
        cached_val = cache.get(cache_key)

        if cached_val is not None:
            return cached_val

        val = GlobalParameter.objects.filter(key=norm_key, is_active=True).first()

        if val:
            cache.set(cache_key, val, timeout=3600)  # 1 hora

        return val
