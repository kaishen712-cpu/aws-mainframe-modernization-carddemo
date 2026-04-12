"""
Testing environment settings for the CardDemo application.

Optimised for fast test execution: in-memory SQLite, fast password hasher,
synchronous middleware.
"""
from __future__ import annotations

from .base import *  # noqa: F401, F403

# ---------------------------------------------------------------------------
# Debug (enabled so Django gives useful error pages in test client)
# ---------------------------------------------------------------------------

DEBUG = True

ALLOWED_HOSTS = ["*"]  # noqa: S104

# ---------------------------------------------------------------------------
# Database — in-memory SQLite for speed
# ---------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

# ---------------------------------------------------------------------------
# Password hashing — fast MD5 for test speed (NOT for production)
# ---------------------------------------------------------------------------

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# ---------------------------------------------------------------------------
# Throttling — tighter for faster test cycles
# ---------------------------------------------------------------------------

LOGIN_MAX_ATTEMPTS = 3
LOGIN_LOCKOUT_DURATION_SECONDS = 60
