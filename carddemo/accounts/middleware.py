"""
Middleware for enforcing password reset on first-time login.

Business rule from COBOL SEC-USR-PWD-RESET flag:
Users with password_reset_required=True MUST change their password before
accessing any other part of the application. This middleware enforces that
by intercepting every request and redirecting to the password change page.

Without this middleware, a user could bypass the password change redirect
by navigating directly to a protected URL after login.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from django.shortcuts import redirect
from django.urls import reverse

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.http import HttpRequest, HttpResponse

# URLs that users with password_reset_required can still access
_ALLOWED_URL_NAMES = frozenset({"accounts:password_change", "accounts:logout"})


class PasswordResetMiddleware:
    """Enforce mandatory password change for first-time logins.

    Business rule: SEC-USR-PWD-RESET flag triggers mandatory password change.
    The user cannot access any view other than password-change and logout
    until the flag is cleared.

    Must be placed AFTER AuthenticationMiddleware in MIDDLEWARE.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        """Store the next middleware/view in the chain."""
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Check password_reset_required flag on every request."""
        if not _requires_password_reset(request):
            return self.get_response(request)

        # Allow access to password change and logout URLs
        if _is_allowed_url(request.path):
            return self.get_response(request)

        return redirect("accounts:password_change")


def _requires_password_reset(request: HttpRequest) -> bool:
    """Check if the current user must change their password."""
    if not request.user.is_authenticated:
        return False
    return getattr(request.user, "password_reset_required", False)


def _is_allowed_url(path: str) -> bool:
    """Check if the URL is in the allowed list for password reset users."""
    allowed_paths = {reverse(name) for name in _ALLOWED_URL_NAMES}
    return path in allowed_paths
