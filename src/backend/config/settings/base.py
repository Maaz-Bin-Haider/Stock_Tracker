import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "insecure-dev-only-key-change-in-prod")

DEBUG = False

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,backend").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    "apps.core",
    "apps.accounts",
    "apps.masterdata",
    "apps.products",
    "apps.purchases",
    "apps.shipments",
    "apps.sales",
    "apps.inventory",
    "apps.reports",
    "apps.audits",
    "apps.attachments",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.audits.middleware.AuditRequestMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
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
        "NAME": os.environ.get("POSTGRES_DB", "stock_tracker"),
        "USER": os.environ.get("POSTGRES_USER", "stock_tracker"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "stock_tracker"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"

# All timestamps are stored in UTC; every "today"/day-boundary calculation must
# use BUSINESS_TZ via the core time helpers (SYSTEM_SPEC §28, FR-128).
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
BUSINESS_TZ = "Asia/Dubai"

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Generated report exports live OUTSIDE MEDIA_ROOT on purpose: nginx serves
# /media publicly, but exports (incl. admin-only valuation, FR-116) must only
# be reachable through the authenticated download endpoint.
EXPORTS_ROOT = BASE_DIR / "exports"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "SwissTech Stock Tracker API",
    "DESCRIPTION": "Inventory management API. The stock ledger is the source of truth.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Shared cache. Single-use workspace-handoff nonces must be visible to every
# gunicorn worker, so production needs a real Redis cache; the in-memory
# fallback is per-process and only safe for a single-process dev server.
# Django namespaces its keys, so sharing Redis with Celery is safe.
_CACHE_URL = os.environ.get("DJANGO_CACHE_URL", "") or os.environ.get("REDIS_URL", "")
CACHES = {
    "default": (
        {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _CACHE_URL,
        }
        if _CACHE_URL
        else {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "stock-tracker-local",
        }
    )
}

# Workspace handoff from the Accounting ERP (apps/accounts/handoff.py).
# Empty = the feature is off and the endpoint is inert. To enable it, set the
# SAME value here and in the ERP's environment, and nowhere else. Generate one
# with: python -c "import secrets; print(secrets.token_urlsafe(48))"
WORKSPACE_HANDOFF_SECRET = os.environ.get("WORKSPACE_HANDOFF_SECRET", "")
# Seconds a handoff token stays valid. It only has to cover one redirect, so
# keep it short; the token is single-use regardless.
WORKSPACE_HANDOFF_MAX_AGE_SECONDS = int(
    os.environ.get("WORKSPACE_HANDOFF_MAX_AGE_SECONDS", "30")
)
