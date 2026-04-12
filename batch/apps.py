"""Batch app configuration."""

from __future__ import annotations

from django.apps import AppConfig


class BatchConfig(AppConfig):
    """Configuration for the batch processing app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "batch"
    verbose_name = "Batch Processing"
