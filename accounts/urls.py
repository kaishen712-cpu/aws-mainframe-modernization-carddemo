"""
URL configuration for the accounts (authentication) app.

Maps to COBOL transaction IDs:
- CC00 (COSGN00C sign-on) -> /accounts/login/
- Sign-off               -> /accounts/logout/
"""
from __future__ import annotations

from django.urls import path

from accounts import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("password-change/", views.password_change_view, name="password_change"),
]
