"""Django app configuration for accounts_mgmt."""

from __future__ import annotations

from django.apps import AppConfig


class AccountsMgmtConfig(AppConfig):
    """Configuration for the Account Management application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts_mgmt"
    verbose_name = "Account Management"
