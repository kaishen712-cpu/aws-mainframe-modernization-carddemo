"""Cards app configuration."""

from __future__ import annotations

from django.apps import AppConfig


class CardsConfig(AppConfig):
    """Configuration for the cards Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "python.cards"
    verbose_name = "Credit Card Management"
