"""Production Django settings -- security hardened.

All secrets loaded from environment variables. DEBUG is always False.
Connection pooling, secure cookies, HSTS, and ALLOWED_HOSTS enforced.
"""

from __future__ import annotations

from .base import *  # noqa: F401, F403
from .base import env

DEBUG = False

# ---------------------------------------------------------------------------
# Secrets -- MUST be set in the environment; no defaults in production
# ---------------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

# ---------------------------------------------------------------------------
# Database -- connection pooling via CONN_MAX_AGE
# ---------------------------------------------------------------------------
DATABASES["default"]["CONN_MAX_AGE"] = env.int(  # type: ignore[index]  # noqa: F405
    "DJANGO_CONN_MAX_AGE", default=600
)

# ---------------------------------------------------------------------------
# HTTPS / security headers
# ---------------------------------------------------------------------------
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"

# ---------------------------------------------------------------------------
# Session -- Redis for production session storage (if available)
# ---------------------------------------------------------------------------
REDIS_URL = env("REDIS_URL", default="")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"
    SESSION_CACHE_ALIAS = "default"

# ---------------------------------------------------------------------------
# Static files -- collected via collectstatic
# ---------------------------------------------------------------------------
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

# ---------------------------------------------------------------------------
# Logging -- JSON formatter for structured production logs
# ---------------------------------------------------------------------------
LOGGING["handlers"]["console"]["formatter"] = "json"  # type: ignore[index]  # noqa: F405
