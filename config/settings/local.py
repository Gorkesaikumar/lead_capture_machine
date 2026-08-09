"""
Local development settings for Photo Studio CRM.
"""
from .base import *  # noqa: F403

DEBUG = True

# Relaxed CORS & Hosts for local DX
ALLOWED_HOSTS = ["localhost", "127.0.0.1", ".ngrok-free.app", ".ngrok-free.dev", ".ngrok.app", ".ngrok.io"] + ALLOWED_HOSTS

CORS_ALLOWED_ORIGIN_REGEXES += [
    r"^https://[a-zA-Z0-9-]+\.ngrok-free\.app$",
    r"^https://[a-zA-Z0-9-]+\.ngrok-free\.dev$",
    r"^https://[a-zA-Z0-9-]+\.ngrok\.app$",
    r"^https://[a-zA-Z0-9-]+\.ngrok\.io$",
]

CSRF_TRUSTED_ORIGINS += [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://*.ngrok-free.app",
    "https://*.ngrok-free.dev",
    "https://*.ngrok.app",
    "https://*.ngrok.io",
]

# Disable strict password requirements in local dev if needed
AUTH_PASSWORD_VALIDATORS = []

# Celery local debugging support - Default to True to fix delay issues when Redis is not running
import os
CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "True").lower() in ("true", "1", "yes")

# Override cache to LocMemCache to prevent 5s delay per request when Redis is not running
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
