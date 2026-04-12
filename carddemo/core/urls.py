"""
URL configuration for the core (navigation) app.

Maps to COBOL transaction IDs:
- CM00 (COMEN01C main menu) -> /menu/
- CA00 (COADM01C admin menu) -> /admin-menu/

Placeholder URLs for future phases redirect to "Coming Soon" pages.
"""
from __future__ import annotations

from django.urls import path

from core import views

app_name = "core"

urlpatterns = [
    # Main navigation (Phase 2)
    path("menu/", views.main_menu_view, name="main_menu"),
    path("admin-menu/", views.admin_menu_view, name="admin_menu"),

    # Placeholder URLs for Phase 3 — Account Management
    path("account-view/", views.placeholder_view, name="account_view"),
    path("account-update/", views.placeholder_view, name="account_update"),

    # Placeholder URLs for Phase 4 — Credit Card Management
    path("credit-card-list/", views.placeholder_view, name="credit_card_list"),
    path("credit-card-view/", views.placeholder_view, name="credit_card_view"),
    path("credit-card-update/", views.placeholder_view, name="credit_card_update"),

    # Placeholder URLs for Phase 5 — Transaction Management
    path("transaction-list/", views.placeholder_view, name="transaction_list"),
    path("transaction-view/", views.placeholder_view, name="transaction_view"),
    path("transaction-add/", views.placeholder_view, name="transaction_add"),
    path("transaction-reports/", views.placeholder_view, name="transaction_reports"),
    path("bill-payment/", views.placeholder_view, name="bill_payment"),
    path("pending-auth/", views.placeholder_view, name="pending_auth"),

    # Placeholder URLs for Phase 6 — User Administration
    path("user-list/", views.placeholder_view, name="user_list"),
    path("user-add/", views.placeholder_view, name="user_add"),
    path("user-update/", views.placeholder_view, name="user_update"),
    path("user-delete/", views.placeholder_view, name="user_delete"),
    path("tran-type-list/", views.placeholder_view, name="tran_type_list"),
    path("tran-type-maint/", views.placeholder_view, name="tran_type_maint"),
]
