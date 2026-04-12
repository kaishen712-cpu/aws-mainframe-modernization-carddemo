"""Admin registration for the accounts app."""
from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import CardDemoUser


@admin.register(CardDemoUser)
class CardDemoUserAdmin(UserAdmin):
    """Admin interface for the CardDemoUser model."""

    list_display = ("username", "first_name", "last_name", "user_type", "is_active")
    list_filter = ("user_type", "is_active", "is_staff")
    fieldsets = UserAdmin.fieldsets + (  # type: ignore[operator]
        ("CardDemo Fields", {"fields": ("user_type", "password_reset_required")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (  # type: ignore[operator]
        ("CardDemo Fields", {"fields": ("user_type",)}),
    )
