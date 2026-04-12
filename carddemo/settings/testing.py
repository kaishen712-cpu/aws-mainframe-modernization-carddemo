"""Testing-specific Django settings -- fast in-memory SQLite.

Optimised for fast test runs: in-memory database, weak password
hasher, and minimal logging.
"""

from __future__ import annotations

from .base import *  # noqa: F401, F403

DEBUG = False
SECRET_KEY = "test-secret-key-not-for-production"  # noqa: S105

# ---------------------------------------------------------------------------
# Database -- in-memory SQLite for speed
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# ---------------------------------------------------------------------------
# Password hashing -- fast hasher for tests only
# ---------------------------------------------------------------------------
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# ---------------------------------------------------------------------------
# Email -- in-memory backend
# ---------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# ---------------------------------------------------------------------------
# Logging -- minimal output during tests
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
        "level": "CRITICAL",
    },
}
