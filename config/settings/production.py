"""
Production settings for Photo Studio CRM.
"""
import os
from django.core.exceptions import ImproperlyConfigured
from .base import *  # noqa: F403

DEBUG = False

# Strict host headers
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "").split(",") if h.strip()]

# Security hardening
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "True").lower() in ("true", "1", "yes")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REDIRECT_EXEMPT = [r"^health/"]
X_FRAME_OPTIONS = "DENY"
SECURE_BROWSER_XSS_FILTER = True

# Disable browsable API in production
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
]

# Strict validation of required environment variables
required_vars = [
    "ALLOWED_HOSTS",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_HOST",
    "REDIS_URL",
    "CELERY_BROKER_URL",
    "FRONTEND_URL",
    "CORS_ALLOWED_ORIGINS",
    "CSRF_TRUSTED_ORIGINS",
    "META_GRAPH_API_VERSION",
    "META_APP_ID",
    "META_APP_SECRET",
    "META_VERIFY_TOKEN",
]

import sys
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars and not any(cmd in sys.argv for cmd in ["check_config", "check"]):
    raise ImproperlyConfigured(f"Missing required environment variables in production: {', '.join(missing_vars)}")

# Enable connection pooling since psycopg_pool is now available in requirements/production.txt
# We set pool=True to maintain robust connections for web and celery workers.
if "default" in DATABASES:
    DATABASES["default"]["CONN_MAX_AGE"] = 0  # Django pooling is incompatible with persistent connections
    DATABASES["default"].setdefault("OPTIONS", {})
    DATABASES["default"]["OPTIONS"]["pool"] = True
