"""
Root URL configuration for the CardDemo Django project.

Routes account management views under ``/accounts/``.
"""

from __future__ import annotations

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts_mgmt.urls")),
]
