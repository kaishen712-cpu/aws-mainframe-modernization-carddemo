"""Root conftest for pytest-django configuration."""

from __future__ import annotations

import os

import django


def pytest_configure() -> None:
    """Configure Django settings for test execution."""
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE", "python.carddemo.settings",
    )
    os.environ["DJANGO_DEBUG"] = "False"
    django.setup()
