# Política y Directrices de Seguridad - Inventario P.M.E.

## 1. Aislamiento Multi-Tenant (Protección Anti-IDOR y Fuga de Datos)

1. **Principio Fail-Closed:**
   - Si una petición no define de forma inequívoca el inquilino activo (`X-Company-ID`), y el usuario pertenece a más de una empresa, el sistema deniega el acceso con `PermissionDenied` (HTTP 403).
   - Queda estrictamente prohibido el uso de fallbacks como `company_id__in` que mezclen datos de diferentes organizaciones en una sola respuesta.
   - Eliminación total de cualquier bypass condicional histórico basado en `company_id == 1`.

2. **Inmutabilidad del Inquilino:**
   - La propiedad `company_id` de cualquier entidad `TenantModel` no puede ser modificada tras su creación. Cualquier intento de alteración en `TenantModel.save()` genera una excepción inmutable `ValidationError`.

3. **Validación Cruzada de Relaciones Tenant:**
   - Al relacionar entidades (e.g. Compras con Proveedores, Ventas con Clientes), los servicios de negocio validan explícitamente que la entidad foránea pertenezca al mismo `company_id`.

---

## 2. Autenticación y Mitigación de Enumeración de Usuarios

1. **Protección Anti-Enumeración en Login (`AuthService.login`):**
   - La autenticación de credenciales (`authenticate()`) se ejecuta con tiempo constante antes de exponer si una cuenta está bloqueada temporalmente por intentos fallidos.
   - Peticiones con credenciales inválidas retornan invariablemente `InvalidCredentialsException` (HTTP 401), imposibilitando determinar si el correo existe o su estado de bloqueo.
   - El bloqueo por fuerza bruta (`AccountLockedException`) solo es visible cuando el usuario legítimo suministra la contraseña correcta durante el período de penalización.

2. **Carga Segura de Archivos (Anti-XSS y Anti-Malware):**
   - En `CompanyInfoService.validate_logo_file`:
     - Se excluyen formatos basados en XML/texto como SVG (`image/svg+xml`) para mitigar ataques de Stored XSS y XXE.
     - Se valida la integridad binaria del archivo mediante `Pillow` (`Image.open(f).verify()`), comprobando cabeceras mágicas y checksums de chunks reales.
     - Límite estricto de tamaño de 2MB.

3. **Rate Limiting y Throttling:**
   - Configurado en `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`:
     - `auth_login`: 5 peticiones por minuto.
     - `auth_refresh`: 10 peticiones por minuto.
     - `saas_impersonate`: 10 peticiones por minuto.
     - `saas_action`: 20 peticiones por minuto.
