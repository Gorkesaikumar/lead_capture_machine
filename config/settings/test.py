"""
Test settings for Photo Studio CRM.
"""
from .base import *  # noqa: F403

DEBUG = False
SECRET_KEY = "test-secret-key-not-for-production-use"

# Fast password hashing for unit tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Run Celery tasks synchronously in tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# In-memory cache for test isolation
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-v4-studio-cache",
    }
}

# In-memory channel layer for test isolation
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

