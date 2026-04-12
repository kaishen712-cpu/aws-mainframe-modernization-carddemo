"""
Root URL configuration for the CardDemo Django project.

Wires together the accounts (authentication) and core (navigation/menus)
apps.  Future phases will add accounts_mgmt, cards, transactions, etc.
"""
from __future__ import annotations

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("core.urls")),
]
