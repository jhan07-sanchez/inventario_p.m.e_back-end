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
    "apps.categories.apps.CategoriesConfig"
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
        "CONN_MAX_AGE": config("CONN_MAX_AGE", default=60, cast=int),
    }
}


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


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ======================================
# Django REST Framework
# ======================================

REST_FRAMEWORK = {
    # Autenticación por defecto
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    # Permisos por defecto
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    # Paginación
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.custom_pagination.CustomPagination",
    "PAGE_SIZE": 10,
    # Esquema OpenAPI
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Renderizamos únicamente JSON
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "EXCEPTION_HANDLER": "apps.core.exceptions.exception_handler.custom_exception_handler",
    # Throttling
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "auth_login": "5/minute",
        "auth_refresh": "10/minute",
    },
}


# ======================================
# DRF Spectacular
# ======================================

SPECTACULAR_SETTINGS = {
    "TITLE": "inventario-pme API",
    "DESCRIPTION": (
        "API REST empresarial del sistema inventario-pme.\\n\\n"
        "Esta API proporciona acceso completo a los módulos, "
        "de inventario-pme ERP.\\n\\n"
        "**Características Principales:**\\n"
        "- Respuestas estandarizadas en formato JSON.\\n"
        "- Autenticación segura mediante tokens JWT.\\n"
        "- Paginación unificada y filtros avanzados."
    ),
    "TOS": "https://www.inventario-pme.com/terms/",
    "CONTACT": {
        "name": "Soporte inventario-pme",
        "url": "",
        "email": "jhansancheza@gmail.com",
    },
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    # Habilita el preprocesamiento de enums para componentes limpios
    "ENUM_NAME_OVERRIDES": {},
    # Configuramos los esquemas globales y componentes de seguridad
    "COMPONENTS": {
        "securitySchemes": {
            "jwtAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Autenticación mediante JWT. Colocar el token de acceso obtenido en el login.",
            }
        }
    },
    "SECURITY": [{"jwtAuth": []}],
    # Agrupación y metadata extendida de ReDoc
    "EXTENSIONS_INFO": {},
    "TAGS": [
        {
            "name": "Authentication",
            "description": "Manejo del ciclo de vida de sesiones de usuario y tokens JWT.",
        },
        {
            "name": "Users",
            "description": "Gestión del directorio de usuarios del sistema.",
        },
        {
            "name": "Roles",
            "description": "Gestión de roles y niveles de acceso.",
        },
        {
            "name": "User Roles",
            "description": "Asignación y manejo de roles para los usuarios.",
        },
        {
            "name": "Security Dashboard",
            "description": "Consultas del estado de seguridad y panel principal de navegación.",
        },
    ],
    "EXTENSIONS_ROOT": {
        "x-tagGroups": [
            {
                "name": "Seguridad y Accesos",
                "tags": [
                    "Authentication",
                    "Users",
                    "Roles",
                    "User Roles",
                    "Security Dashboard",
                ],
            }
        ]
    },
    # Removemos inline serializers anónimos por defecto en Spectacular (si es posible a nivel de prefijos)
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]",
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
    ],
}

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
