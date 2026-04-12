"""User admin app configuration."""

from __future__ import annotations

from django.apps import AppConfig


class UserAdminConfig(AppConfig):
    """Configuration for the user_admin Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "python.user_admin"
    verbose_name = "User Administration"
