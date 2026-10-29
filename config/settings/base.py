import sys
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from decouple import Csv, config

from .spectacular import *  # noqa: F403

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("SECRET_KEY", default="")

DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="", cast=Csv())

TESTING = any(cmd in sys.argv for cmd in ["test", "pytest"])

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_filters",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "rest_framework_simplejwt.token_blacklist",
    "simple_history",
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
    "apps.configuration.apps.ConfigurationConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middlewares.audit_middleware.AuditMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
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


def get_database_config():
    """
    Configura el diccionario de base de datos soportando:
    1. DATABASE_URL (formato postgres://user:password@host:port/dbname) estándar en Render y Supabase.
    2. Variables individuales DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT.
    3. Fallback a SQLite en memoria durante ejecución de pruebas automáticas.
    """
    if TESTING:
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }

    database_url = config("DATABASE_URL", default="").strip()
    if database_url:
        parsed = urlparse(database_url)
        db_name = parsed.path.lstrip("/")
        db_user = unquote(parsed.username) if parsed.username else ""
        db_password = unquote(parsed.password) if parsed.password else ""
        db_host = parsed.hostname or "localhost"
        db_port = parsed.port or 5432

        query_params = parse_qs(parsed.query)
        sslmode = query_params.get("sslmode", [config("DB_SSLMODE", default="")])[0]

        options = {
            "connect_timeout": config("DB_CONNECT_TIMEOUT", default=10, cast=int),
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        }
        if sslmode:
            options["sslmode"] = sslmode

        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": db_name,
            "USER": db_user,
            "PASSWORD": db_password,
            "HOST": db_host,
            "PORT": db_port,
            "CONN_MAX_AGE": config("CONN_MAX_AGE", default=60, cast=int),
            "CONN_HEALTH_CHECKS": config("CONN_HEALTH_CHECKS", default=True, cast=bool),
            "DISABLE_SERVER_SIDE_CURSORS": config("DISABLE_SERVER_SIDE_CURSORS", default=True, cast=bool),
            "OPTIONS": options,
        }

    # Fallback con variables individuales
    options = {
        "connect_timeout": config("DB_CONNECT_TIMEOUT", default=10, cast=int),
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    }
    db_sslmode = config("DB_SSLMODE", default="")
    if db_sslmode:
        options["sslmode"] = db_sslmode

    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default=""),
        "USER": config("DB_USER", default=""),
        "PASSWORD": config("DB_PASSWORD", default=""),
        "HOST": config("DB_HOST", default=""),
        "PORT": config("DB_PORT", default=""),
        "CONN_MAX_AGE": config("CONN_MAX_AGE", default=60, cast=int),
        "CONN_HEALTH_CHECKS": config("CONN_HEALTH_CHECKS", default=True, cast=bool),
        "DISABLE_SERVER_SIDE_CURSORS": config("DISABLE_SERVER_SIDE_CURSORS", default=True, cast=bool),
        "OPTIONS": options,
    }


DATABASES = {
    "default": get_database_config(),
}

if TESTING:
    PASSWORD_HASHERS = [
        "django.contrib.auth.hashers.MD5PasswordHasher",
    ]


LANGUAGE_CODE = "es-co"

TIME_ZONE = "America/Bogota"

USE_I18N = True

USE_TZ = True


# ======================================
# Archivos Estáticos y Multimedia
# ======================================

STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "staticfiles"
STATIC_ROOT.mkdir(parents=True, exist_ok=True)

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# ======================================
# Caché Configuration (LocMemCache)
# ======================================
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "inventario-pme-cache",
        "TIMEOUT": 300,
        "OPTIONS": {
            "MAX_ENTRIES": 1000,
        },
    },
}

CACHE_TIMEOUTS = {
    "dashboard_metrics": 300,
    "permissions": 600,
    "products_list": 180,
    "inventory_status": 120,
    "sales_summary": 300,
    "company_info": 3600,
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# =======================================
# Simple JWT
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


# =======================================
# Logging Centralizado (Render compatible)
# =======================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} - {message}",
            "style": "{",
        },
        "simple": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}


AUTH_PASSWORD_VALIDATORS= [
    {
        "NAME": "apps.users.validators.DynamicPasswordLengthValidator"
    },
]
