"""
Root URL configuration for CardDemo.

Maps Django apps to URL prefixes mirroring the original CICS
transaction IDs (CCLI, CCDL, CT00, CU00, etc.).
"""

from __future__ import annotations

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("cards/", include("python.cards.urls", namespace="cards")),
    path(
        "transactions/",
        include("python.transactions.urls", namespace="transactions"),
    ),
    path("reports/", include("python.reports.urls", namespace="reports")),
    path(
        "users/",
        include("python.user_admin.urls", namespace="user_admin"),
    ),
]
