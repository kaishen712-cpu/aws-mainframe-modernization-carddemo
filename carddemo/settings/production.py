"""
Production environment settings for the CardDemo application.

Enforces secure defaults: DEBUG off, HTTPS cookies, HSTS, and PostgreSQL.
"""
from __future__ import annotations

from .base import *  # noqa: F401, F403
from .base import env

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

DEBUG = False
SECRET_KEY = env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

# HTTPS enforcement
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookie security
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True

# Clickjacking protection
X_FRAME_OPTIONS = "DENY"
