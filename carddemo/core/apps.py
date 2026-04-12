"""Core app configuration."""
from __future__ import annotations

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Configuration for the core (navigation/menus) Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "CardDemo Navigation"
