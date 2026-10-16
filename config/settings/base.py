import sys
from datetime import timedelta
from pathlib import Path

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent.parent


SECRET_KEY = config("SECRET_KEY")

DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="", cast=Csv())


DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "rest_framework_simplejwt.token_blacklist",
]

LOCAL_APPS = [
    "apps.core.apps.CoreConfig",
    "apps.users.apps.UsersConfig",
    "apps.customers.apps.CustomersConfig",
    "apps.suppliers.apps.SuppliersConfig",
    "apps.categories.apps.CategoriesConfig",
    "apps.products.apps.ProductsConfig",
    "apps.inventory.apps.InventoryConfig",
    "apps.purchases.apps.PurchasesConfig",
    "apps.invoices.apps.InvoicesConfig",
    "apps.sales.apps.SalesConfig",
    "apps.company_info.apps.CompanyInfoConfig",
    "apps.cash.apps.CashConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middlewares.audit_middleware.AuditMiddleware",
]


ROOT_URLCONF = "config.urls"


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


WSGI_APPLICATION = "config.wsgi.application"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST"),
        "PORT": config("DB_PORT"),
        "CONN_MAX_AGE": config(
            "CONN_MAX_AGE",
            default=60,
            cast=int,
        ),
        "CONN_HEALTH_CHECKS": config(
            "CONN_HEALTH_CHECKS",
            default=True,
            cast=bool,
        ),
        "OPTIONS": {
            "connect_timeout": 10,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        },
    }
}

if any(cmd in sys.argv for cmd in ["test", "pytest"]):
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
    PASSWORD_HASHERS = [
        "django.contrib.auth.hashers.MD5PasswordHasher",
    ]


LANGUAGE_CODE = "es-co"

TIME_ZONE = "America/Bogota"

USE_I18N = True

USE_TZ = True


# ======================================
# Configuración de Archivos Multimedia (Media)
# ======================================

STATIC_URL = "static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# ======================================
# Configuración de Archivos de Medios
# ======================================

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# ======================================
# Caché Configuration (LocMemCache)
# ======================================
# IMPORTANTE: LocMemCache es per-process (cada worker de Gunicorn
# tiene su propia instancia de caché). Esto significa:
# - La invalidación de caché solo afecta al worker que la ejecuta.
# - El caché NO se comparte entre workers ni entre procesos.
# - En producción con múltiples workers, considerar migrar a un
#   backend compartido (ej. Redis) cuando el proyecto lo requiera.
#
# Para migrar a Redis en el futuro, solo cambiar BACKEND y LOCATION:
#   "BACKEND": "django.core.cache.backends.redis.RedisCache",
#   "LOCATION": "redis://127.0.0.1:6379/1",
# ======================================

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "inventario-pme-cache",
        "TIMEOUT": 300,  # 5 minutos por defecto
        "OPTIONS": {
            "MAX_ENTRIES": 1000,
        },
    },
}

# Timeouts centralizados para caché (en segundos).
# Usar estas constantes en servicios y selectors para mantener
# consistencia y facilitar ajustes globales.
CACHE_TIMEOUTS = {
    "dashboard_metrics": 300,  # 5 min — métricas del dashboard
    "permissions": 600,  # 10 min — permisos de usuario
    "products_list": 180,  # 3 min — listado de productos
    "inventory_status": 120,  # 2 min — estado de inventario
    "sales_summary": 300,  # 5 min — resumen de ventas
    "company_info": 3600,  # 1 hora — info de la empresa (rara vez cambia)
}


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


from .spectacular import *  # noqa: F403

# =======================================
# Simple jwt
# =======================================

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "USER_ID_FIELD": "id_user",
    "USER_ID_CLAIM": "user_id",
}


AUTH_USER_MODEL = "users.User"
