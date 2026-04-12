"""
Base Django settings for the CardDemo application.

Shared settings across all environments (development, production, testing).
Environment-specific overrides live in sibling modules.

Architecture mapping: CICS session management -> Django sessions (database-backed).
"""
from __future__ import annotations

import os
from pathlib import Path

import environ

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent.parent
env = environ.Env()

# Read .env file if it exists (12-factor config)
env_file = BASE_DIR / ".env"
if env_file.exists():
    env.read_env(str(env_file))

# ---------------------------------------------------------------------------
# Core settings
# ---------------------------------------------------------------------------

SECRET_KEY = env("DJANGO_SECRET_KEY", default="change-me-in-production")

DEBUG = env.bool("DJANGO_DEBUG", default=False)

ALLOWED_HOSTS: list[str] = env.list("DJANGO_ALLOWED_HOSTS", default=[])

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # CardDemo apps
    "accounts",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "carddemo.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "core" / "templates"],
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

WSGI_APPLICATION = "carddemo.wsgi.application"

# ---------------------------------------------------------------------------
# Database — PostgreSQL (replaces VSAM KSDS files)
# ---------------------------------------------------------------------------

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://carddemo:carddemo@localhost:5432/carddemo",
    ),
}

# ---------------------------------------------------------------------------
# Custom user model (maps COBOL USRSEC record -> Django auth)
# ---------------------------------------------------------------------------

AUTH_USER_MODEL = "accounts.CardDemoUser"

# ---------------------------------------------------------------------------
# Password hashing — Argon2 primary (CPS 234 compliant)
# ---------------------------------------------------------------------------

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Sessions — database-backed (replaces CICS COMMAREA)
# ---------------------------------------------------------------------------

SESSION_ENGINE = "django.contrib.sessions.backends.db"

# ---------------------------------------------------------------------------
# Authentication URLs
# ---------------------------------------------------------------------------

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/menu/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# ---------------------------------------------------------------------------
# Default primary key field type
# ---------------------------------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Login throttling settings (brute-force prevention)
# Translated from COSGN00C.cbl — the original COBOL had no throttling;
# this is an improvement for the Python version.
# FLAG FOR HUMAN REVIEW: hardcoded threshold values below
# ---------------------------------------------------------------------------

LOGIN_MAX_ATTEMPTS = int(os.environ.get("LOGIN_MAX_ATTEMPTS", "5"))
LOGIN_LOCKOUT_DURATION_SECONDS = int(
    os.environ.get("LOGIN_LOCKOUT_DURATION_SECONDS", "300")
)
