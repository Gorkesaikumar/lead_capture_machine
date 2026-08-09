"""
Base Django settings for Photo Studio Lead Capture, CRM & Booking Platform.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env file
load_dotenv(BASE_DIR / ".env", override=True)

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY environment variable is missing.")

DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "").split(",") if h.strip()]

# Application definition
DJANGO_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
]

THIRD_PARTY_APPS = [
    "channels",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "django_filters",
    "django_celery_beat",
    "django_celery_results",
]

LOCAL_APPS = [
    "apps.core.apps.CoreConfig",
    "apps.accounts.apps.AccountsConfig",
    "apps.customers.apps.CustomersConfig",
    "apps.leads.apps.LeadsConfig",
    "apps.conversations.apps.ConversationsConfig",
    "apps.integrations.apps.IntegrationsConfig",
    "apps.services.apps.ServicesConfig",
    "apps.scheduling.apps.SchedulingConfig",
    "apps.bookings.apps.BookingsConfig",
    "apps.notifications.apps.NotificationsConfig",
    "apps.analytics.apps.AnalyticsConfig",
    "apps.audit.apps.AuditConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "apps.core.middleware.CorrelationIdMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.StructuredLoggingMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Custom User Model
AUTH_USER_MODEL = "accounts.User"

# Database Configuration (PostgreSQL)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", ""),
        "USER": os.getenv("POSTGRES_USER", ""),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
        "HOST": os.getenv("POSTGRES_HOST", ""),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": int(os.getenv("CONN_MAX_AGE", "60")),
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "connect_timeout": 10,
        },
    }
}

# Cache Configuration (Redis)
REDIS_URL = os.getenv("REDIS_URL", "")
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
        },
        "KEY_PREFIX": "v4_studio",
    }
}

# Session engine with cache fallback
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("TIME_ZONE", "Asia/Kolkata")
USE_I18N = True
USE_TZ = True

# Static & Media files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        "auth_login": "5/minute",
    },
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%S%z",
}

# Django Channels / Redis Channel Layer
REDIS_URL = os.getenv("REDIS_URL", "")
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
            "capacity": 1500,
            "expiry": 10,
        },
    },
}

# Celery Configuration
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "django-db")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = False
CELERY_TASK_TRACK_STARTED = True

# Worker Reliability Settings
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_REJECT_ON_WORKER_LOST = True

# Timeouts
CELERY_TASK_SOFT_TIME_LIMIT = 5 * 60
CELERY_TASK_TIME_LIMIT = 6 * 60

CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# CORS & CSRF
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

CORS_ALLOWED_ORIGIN_REGEXES = []

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

# Studio Specific Configuration
STUDIO_NAME = os.getenv("STUDIO_NAME", "Studio V4 Photography")
FRONTEND_URL = os.getenv("FRONTEND_URL", "").rstrip("/")

# Meta Platform Credentials (Masked from direct logs)
META_APP_SECRET = os.getenv("META_APP_SECRET", "")
META_VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_BOOKING_TEMPLATE_NAME = os.getenv("WHATSAPP_BOOKING_TEMPLATE_NAME", "studio_booking_invitation")
WHATSAPP_DEFAULT_LANGUAGE = os.getenv("WHATSAPP_DEFAULT_LANGUAGE", "en")

# Structured Logging Configuration
# - JSON formatter: one JSON object per line — ideal for Docker log drivers,
#   Elasticsearch, Datadog, Papertrail, and Grafana Loki.
# - Plain-text formatter: human-readable for local development.
# - LOG_FORMAT env var: set to "json" (default) or "plain".
_LOG_FORMAT = os.getenv("LOG_FORMAT", "json" if not DEBUG else "plain")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "apps.core.logging.JsonFormatter",
        },
        "plain": {
            "()": "apps.core.logging.PlainTextFormatter",
        },
    },
    "filters": {
        "correlation_id": {
            "()": "apps.core.logging.CorrelationIdFilter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            # Stream to stdout — Docker captures this via the container's log driver
            "stream": "ext://sys.stdout",
            "formatter": _LOG_FORMAT,
            "filters": ["correlation_id"],
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        # Suppress noisy SQL query logs unless explicitly requested
        "django.db.backends": {
            "handlers": ["console"],
            "level": os.getenv("DB_LOG_LEVEL", "WARNING"),
            "propagate": False,
        },
        # All application code
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        # Integration pipeline — can be promoted to DEBUG independently
        "apps.integrations": {
            "handlers": ["console"],
            "level": os.getenv("INTEGRATIONS_LOG_LEVEL", "DEBUG" if DEBUG else "INFO"),
            "propagate": False,
        },
        # Celery task logs
        "celery": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "celery.task": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

