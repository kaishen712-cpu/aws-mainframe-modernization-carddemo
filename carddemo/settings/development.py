"""Development-specific Django settings.

DEBUG=True, verbose logging, local PostgreSQL.
"""

from __future__ import annotations

from .base import *  # noqa: F401, F403
from .base import LOGGING

DEBUG = True

# ---------------------------------------------------------------------------
# Verbose SQL logging for development debugging
# ---------------------------------------------------------------------------
LOGGING["loggers"]["django.db.backends"] = {  # type: ignore[index]
    "handlers": ["console"],
    "level": "DEBUG",
    "propagate": False,
}

LOGGING["loggers"]["batch"]["level"] = "DEBUG"  # type: ignore[index]
