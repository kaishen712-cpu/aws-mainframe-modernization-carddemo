"""Django admin registration for Account Management models."""

from __future__ import annotations

from django.contrib import admin

from accounts_mgmt.models import Account, CardXref, Customer

admin.site.register(Account)
admin.site.register(Customer)
admin.site.register(CardXref)
