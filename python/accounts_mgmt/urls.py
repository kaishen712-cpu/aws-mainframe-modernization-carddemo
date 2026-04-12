"""
URL configuration for the accounts_mgmt app.

Routes:
- /accounts/          — account search
- /accounts/<id>/     — read-only account detail (COACTVWC)
- /accounts/<id>/update/ — account update form (COACTUPC)
"""

from __future__ import annotations

from django.urls import path

from accounts_mgmt import views

app_name = "accounts_mgmt"

urlpatterns = [
    path("", views.account_search, name="account_search"),
    path("<str:acct_id>/", views.account_detail, name="account_detail"),
    path(
        "<str:acct_id>/update/",
        views.account_update,
        name="account_update",
    ),
]
