# Arquitectura Técnica del Backend - Inventario P.M.E.

## 1. Visión General
**Inventario P.M.E.** es un sistema ERP SaaS empresarial multiempresa basado en:
- **Python 3.13 / Django 6.0.7**
- **Django REST Framework 3.17.1**
- **PostgreSQL en Supabase** con PgBouncer en pool transaccional.
- **Arquitectura Multi-Tenant:** Shared Database + Shared Schema con particionamiento lógico estricto por `company_id`.

---

## 2. Principios de Diseño y Capas (Clean Architecture)

El sistema implementa una arquitectura modular desacoplada:

```
[ HTTP Request (JWT + X-Company-ID) ]
               │
               ▼
   [ TenantContextMiddleware ] ──> Inyecta company_id en request & contextvars
               │
               ▼
        [ BaseViewSet ] ────────> Aislamiento Fail-Closed en isolate_queryset()
               │
         ┌─────┴───────────────┐
         ▼                     ▼
   [ Selector ]            [ Service ]
(Lecturas puras ORM)   (Transacciones atómicas, locks, mutaciones)
         │                     │
         └─────────┬───────────┘
                   ▼
             [ Model / DB ]
```

### Reglas de Capas:
1. **Modelos (`apps/*/models/`):**
   - Todos los modelos de datos de empresa heredan de `TenantModel` (que a su vez extiende `ActiveModel`).
   - `TenantModel` implementa inmutabilidad de `company_id` en memoria mediante `from_db()` sin sobrecosto de consultas N+1.
2. **Selectores (`apps/*/selectors/`):**
   - Responsables exclusivos de consultas de lectura.
   - Aplican `select_related` y `prefetch_related` para prevenir N+1.
   - Todo selector acepta `company_id` y confina las consultas al inquilino activo.
3. **Servicios (`apps/*/services/`):**
   - Encapsulan toda la lógica de negocio y mutaciones de estado.
   - Decorados con `@transaction.atomic`.
   - Utilizan concurrencia pesimista (`select_for_update()`) para operaciones críticas de inventario, caja, pagos y suscripciones.
4. **Vistas / ViewSets (`apps/*/views/`):**
   - Heredan de `BaseViewSet` o `BaseReadOnlyViewSet` (`apps.core.views.base_viewset`).
   - El método `isolate_queryset()` aplica una política **Fail-Closed**: si un usuario con múltiples empresas activas no envía `X-Company-ID`, la petición es denegada (`PermissionDenied 403`), evitando cualquier mezcla accidental de datos.

---

## 3. Caché y Concurrencia Multi-Worker

Para despliegues en producción con Gunicorn multi-worker (`config/settings/production.py`):
- **Soporte Redis:** Configurable vía variable de entorno `REDIS_URL`.
- **Soporte DatabaseCache:** Configurable vía `USE_DATABASE_CACHE=True` (tabla `cache_table`).
- **LocMemCache:** Utilizado exclusivamente como fallback para desarrollo local y ejecución de pruebas.
- **Versionado de Caché:** Implementado en `FinanceCacheService` y `DashboardMetricsService` para invalidaciones atómicas en $O(1)$.
- **Aislamiento Multi-Tenant de Caché:** Claves prefijadas por inquilino (`company_info_{id}`, `finance_dash_{cid}_v{ver}_...`).

---

## 4. Auditoría y Trazabilidad

- **`AuditMiddleware`:** Captura peticiones mutantes (`POST`, `PUT`, `PATCH`, `DELETE`), enmascara campos confidenciales (`password`, `token`, `secret`) y despacha la persistencia a un pool asíncrono `ThreadPoolExecutor(max_workers=5)` sin bloquear la respuesta HTTP.
- **`django-simple-history`:** Auditoría a nivel de fila (`HistoricalRecords`) en modelos críticos del ERP.
