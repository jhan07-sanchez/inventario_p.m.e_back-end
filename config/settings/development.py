from decouple import Csv, config

from .base import *  # noqa: F403

DEBUG = config("DEBUG", default=True, cast=bool)

# Clave de desarrollo local segura para pruebas sin bloquear el inicio local
SECRET_KEY = config(
    "SECRET_KEY",
    default="django-insecure-dev-only-secret-key-inventario-pme-local-test-12345",
)

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="127.0.0.1,localhost,0.0.0.0,::1",
    cast=Csv(),
)

# Configuración de CORS y CSRF para desarrollo con frontend local (Next.js, Vite, etc.)
CORS_ALLOW_ALL_ORIGINS = config("CORS_ALLOW_ALL_ORIGINS", default=True, cast=bool)
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
    cast=Csv(),
)

CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
    cast=Csv(),
)

# Desactivar redirecciones HTTPS y cookies estrictas en desarrollo local
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
