"""Reports app configuration."""

from __future__ import annotations

from django.apps import AppConfig


class ReportsConfig(AppConfig):
    """Configuration for the reports Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "python.reports"
    verbose_name = "Report Management"
