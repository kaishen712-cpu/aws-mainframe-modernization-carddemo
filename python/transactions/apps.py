"""Transactions app configuration."""

from __future__ import annotations

from django.apps import AppConfig


class TransactionsConfig(AppConfig):
    """Configuration for the transactions Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "python.transactions"
    verbose_name = "Transaction Management"
