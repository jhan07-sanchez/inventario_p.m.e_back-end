from decouple import Csv, config
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

# ======================================
# En Producción DEBUG es estrictamente False
# ======================================
DEBUG = False

# ======================================
# Validación de SECRET_KEY para Producción
# ======================================
SECRET_KEY = config("SECRET_KEY", default="")
if not SECRET_KEY or SECRET_KEY.startswith("django-insecure"):
    raise ImproperlyConfigured(
        "SECRET_KEY no es válida o falta para el entorno de producción. "
        "Debe configurar una clave criptográficamente segura en el panel de variables de Render."
    )

# ======================================
# Validación de Base de Datos para Producción
# ======================================
_db_default = DATABASES.get("default", {})  # noqa: F405
if not _db_default.get("NAME") or not _db_default.get("HOST"):
    raise ImproperlyConfigured(
        "Configuración de base de datos incompleta para producción. "
        "Defina DATABASE_URL o las variables DB_NAME, DB_USER, DB_PASSWORD, DB_HOST y DB_PORT."
    )

# ======================================
# Hosts permitidos y Orígenes Autorizados
# ======================================
# Incluye comodín de Render (.onrender.com) y dominio de la API
ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default=".onrender.com,api.inventario-pme.com",
    cast=Csv(),
)

# CORS estrictamente restringido al dominio del frontend
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="https://inventario-pme.com",
    cast=Csv(),
)

# CSRF Trusted Origins para llamadas seguras autenticadas
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="https://inventario-pme.com,https://*.onrender.com",
    cast=Csv(),
)

# ======================================
# Configuración HTTPS y Proxy de Render
# ======================================
# Render termina SSL en su proxy reverso e inyecta HTTP_X_FORWARDED_PROTO: https
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True, cast=bool
)
SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=False, cast=bool)
SILENCED_SYSTEM_CHECKS = ["security.W021"]

SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=True, cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=True, cast=bool)

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # Permite al frontend SPA leer token CSRF si se usa cookie

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

TRUST_X_FORWARDED_FOR = config("TRUST_X_FORWARDED_FOR", default=True, cast=bool)

# ======================================
# Almacenamiento Estático de Alto Rendimiento (WhiteNoise)
# ======================================
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
