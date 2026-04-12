"""
Development environment settings for the CardDemo application.

Enables debug mode, uses local PostgreSQL, and relaxes security constraints
for local development workflows.
"""
from __future__ import annotations

from .base import *  # noqa: F401, F403

# ---------------------------------------------------------------------------
# Debug
# ---------------------------------------------------------------------------

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]  # noqa: S104

# ---------------------------------------------------------------------------
# Database — local PostgreSQL (fallback to SQLite for quick dev)
# ---------------------------------------------------------------------------

DATABASES = {
    "default": env.db(  # noqa: F405
        "DATABASE_URL",
        default="sqlite:///" + str(BASE_DIR / "db.sqlite3"),  # noqa: F405
    ),
}

# ---------------------------------------------------------------------------
# Email — console backend for dev
# ---------------------------------------------------------------------------

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
