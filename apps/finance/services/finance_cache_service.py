import logging
from datetime import date
from typing import Any, Optional, Union

from django.core.cache import cache

logger = logging.getLogger(__name__)


class FinanceCacheService:
    """
    Servicio de gestión y optimización de caché para el módulo de Finanzas y Tesorería.

    Utiliza el backend de caché configurado en Django (LocMemCache en desarrollo/producción
    según la infraestructura actual, sin requerir Redis).

    Estrategia de Invalidación:
    - Implementa 'Cache Versioning' por empresa. Al modificarse movimientos, transferencias,
      cuentas o arqueos, se incrementa la versión de la empresa en O(1), invalidando de forma
      instantánea y atómica todas las consultas agregadas cacheadas de cualquier período,
      evitando lecturas obsoletas.
    - Las operaciones de escritura y cálculo de saldos NUNCA leen de la caché; consultan
      directamente la base de datos con bloqueo atómico (select_for_update).
    """

    CACHE_TIMEOUT = 300  # 5 minutos

    @classmethod
    def _get_version_key(cls, company_id: Optional[int] = None) -> str:
        cid = str(company_id) if company_id is not None else "global"
        return f"finance_version_{cid}"

    @classmethod
    def get_version(cls, company_id: Optional[int] = None) -> int:
        key = cls._get_version_key(company_id)
        version = cache.get(key)
        if version is None:
            version = 1
            cache.set(key, version, timeout=86400 * 30)  # 30 días
        return version

    @classmethod
    def build_dashboard_key(
        cls,
        company_id: Optional[int] = None,
        period: Optional[str] = None,
        start_date: Optional[Union[date, str]] = None,
        end_date: Optional[Union[date, str]] = None,
    ) -> str:
        cid = str(company_id) if company_id is not None else "global"
        p = str(period or "default")
        sd = str(start_date or "none")
        ed = str(end_date or "none")
        version = cls.get_version(company_id)
        return f"finance_dash_{cid}_v{version}_{p}_{sd}_{ed}"

    @classmethod
    def get_dashboard_cache(
        cls,
        company_id: Optional[int] = None,
        period: Optional[str] = None,
        start_date: Optional[Union[date, str]] = None,
        end_date: Optional[Union[date, str]] = None,
    ) -> Optional[dict[str, Any]]:
        """
        Obtiene el resumen consolidado del dashboard financiero desde la caché.
        Retorna None en caso de cache-miss.
        """
        key = cls.build_dashboard_key(
            company_id=company_id,
            period=period,
            start_date=start_date,
            end_date=end_date,
        )
        try:
            cached_data = cache.get(key)
            if cached_data is not None:
                logger.debug(f"[FINANCE CACHE] Cache HIT para {key}")
                return cached_data
            logger.debug(f"[FINANCE CACHE] Cache MISS para {key}")
        except Exception as e:
            logger.warning(f"[FINANCE CACHE] Error al consultar caché: {e}")
        return None

    @classmethod
    def set_dashboard_cache(
        cls,
        data: dict[str, Any],
        company_id: Optional[int] = None,
        period: Optional[str] = None,
        start_date: Optional[Union[date, str]] = None,
        end_date: Optional[Union[date, str]] = None,
        timeout: Optional[int] = None,
    ) -> None:
        """
        Almacena el resumen consolidado en la caché con TTL configurable.
        """
        key = cls.build_dashboard_key(
            company_id=company_id,
            period=period,
            start_date=start_date,
            end_date=end_date,
        )
        ttl = timeout or cls.CACHE_TIMEOUT
        try:
            cache.set(key, data, timeout=ttl)
            logger.debug(f"[FINANCE CACHE] Guardado en caché {key} (TTL: {ttl}s)")
        except Exception as e:
            logger.warning(f"[FINANCE CACHE] Error al escribir en caché: {e}")

    @classmethod
    def invalidate_dashboard_cache(cls, company_id: Optional[int] = None) -> None:
        """
        Invalida de forma atómica e inmediata la caché del dashboard.
        Incrementa la versión de la empresa correspondiente y la versión global.
        """
        try:
            # 1. Invalidar versión de la empresa
            key = cls._get_version_key(company_id)
            current_ver = cls.get_version(company_id)
            cache.set(key, current_ver + 1, timeout=86400 * 30)

            # 2. Si es empresa específica, invalidar también la versión global
            if company_id is not None:
                global_key = cls._get_version_key(None)
                global_ver = cls.get_version(None)
                cache.set(global_key, global_ver + 1, timeout=86400 * 30)

            logger.info(
                f"[FINANCE CACHE] Caché de dashboard invalidada exitosamente para empresa: {company_id or 'global'} (Nueva versión: {current_ver + 1})"
            )
        except Exception as e:
            logger.warning(f"[FINANCE CACHE] Error al invalidar caché: {e}")

