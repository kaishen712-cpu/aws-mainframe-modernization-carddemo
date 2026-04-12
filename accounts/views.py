"""
Authentication views for the CardDemo application.

Translated from COSGN00C.cbl (261 lines) — Sign-on screen for CardDemo.

COBOL program flow:
1. MAIN-PARA: Display sign-on screen or process key press
2. PROCESS-ENTER-KEY: Validate user ID and password fields are not empty
3. READ-USER-SEC-FILE: Look up user in USRSEC VSAM file, verify password,
   route to admin menu (COADM01C) or main menu (COMEN01C) based on user type

Django equivalent:
- LoginView: Handles GET (display form) and POST (authenticate + redirect)
- LogoutView: Clears session and redirects to login
- PasswordResetView: Handles first-time login password change
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.shortcuts import redirect, render

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse

from accounts.forms import LoginForm, PasswordChangeForm
from accounts.services import (
    clear_failed_attempts,
    get_menu_redirect_url,
    is_login_throttled,
    record_failed_attempt,
)

logger = logging.getLogger(__name__)


def login_view(request: HttpRequest) -> HttpResponse:
    """Handle user sign-on.

    Translated from COSGN00C.cbl MAIN-PARA and PROCESS-ENTER-KEY paragraphs.

    GET: Display the sign-on screen (SEND-SIGNON-SCREEN).
    POST: Validate credentials and route to appropriate menu.

    Business rules preserved from COBOL:
    - Empty user ID -> error "Please enter User ID ..."
    - Empty password -> error "Please enter Password ..."
    - User not found -> error "User not found. Try again ..."
    - Wrong password -> error "Wrong Password. Try again ..."
    - Admin user (SEC-USR-TYPE='A') -> redirect to admin menu (COADM01C)
    - Regular user -> redirect to main menu (COMEN01C)
    - First-time login (password_reset_required) -> redirect to password change

    New improvement: login attempt throttling (not in original COBOL).
    """
    if request.user.is_authenticated:
        return _redirect_authenticated_user(request)

    if request.method == "POST":
        return _process_login(request)

    form = LoginForm()
    return render(request, "accounts/login.html", {"form": form})


def _redirect_authenticated_user(request: HttpRequest) -> HttpResponse:
    """Redirect an already-authenticated user to the appropriate menu.

    Translated from COSGN00C.cbl READ-USER-SEC-FILE: user type routing.
    """
    redirect_url = get_menu_redirect_url(request.user.user_type)  # type: ignore[union-attr]
    return redirect(redirect_url)


def _process_login(request: HttpRequest) -> HttpResponse:
    """Process the login form submission.

    Translated from COSGN00C.cbl PROCESS-ENTER-KEY and READ-USER-SEC-FILE.
    """
    form = LoginForm(request.POST)

    if not form.is_valid():
        return render(request, "accounts/login.html", {"form": form})

    # Business rule: throttle after too many failed attempts
    if is_login_throttled(request):
        messages.error(
            request,
            "Too many failed login attempts. Please try again later.",
        )
        return render(request, "accounts/login.html", {"form": form})

    username = form.cleaned_data["username"]
    password = form.cleaned_data["password"]

    return _authenticate_user(request, form, username, password)


def _authenticate_user(
    request: HttpRequest,
    form: LoginForm,
    username: str,
    password: str,
) -> HttpResponse:
    """Authenticate the user and handle routing.

    Translated from COSGN00C.cbl READ-USER-SEC-FILE paragraph.
    COBOL: EXEC CICS READ DATASET(WS-USRSEC-FILE) INTO(SEC-USER-DATA)
    Django: authenticate() checks username + hashed password in DB.

    COBOL response codes:
    - WS-RESP-CD = 0 and password match -> success
    - WS-RESP-CD = 0 and password mismatch -> "Wrong Password. Try again ..."
    - WS-RESP-CD = 13 (NOTFND) -> "User not found. Try again ..."
    - WS-RESP-CD = other -> "Unable to verify the User ..."
    """
    user = authenticate(request, username=username, password=password)

    if user is None:
        record_failed_attempt(request)
        # Translated from COSGN00C.cbl: combined error for security
        # (don't reveal whether username or password was wrong)
        messages.error(request, "Invalid credentials. Try again ...")
        return render(request, "accounts/login.html", {"form": form})

    clear_failed_attempts(request)
    login(request, user)

    # Business rule: first-time login detection (SEC-USR-PWD-RESET)
    if user.password_reset_required:  # type: ignore[union-attr]
        return redirect("accounts:password_change")

    # Translated from COSGN00C.cbl READ-USER-SEC-FILE:
    # IF CDEMO-USRTYP-ADMIN -> XCTL PROGRAM('COADM01C')
    # ELSE -> XCTL PROGRAM('COMEN01C')
    redirect_url = get_menu_redirect_url(user.user_type)  # type: ignore[union-attr]
    return redirect(redirect_url)


def logout_view(request: HttpRequest) -> HttpResponse:
    """Handle user sign-off.

    Translated from COSGN00C.cbl SEND-PLAIN-TEXT paragraph:
    COBOL: Displays CCDA-MSG-THANK-YOU and returns (EXEC CICS RETURN).
    Django: Clears session and redirects to login page.

    Requires POST to prevent cross-site logout via GET (Django 5.0+ best practice).
    """
    if request.method != "POST":
        return redirect("accounts:login")
    logout(request)
    messages.info(request, "Thank you for using CardDemo application...")
    return redirect("accounts:login")


def password_change_view(request: HttpRequest) -> HttpResponse:
    """Handle first-time login password change.

    Business rule: SEC-USR-PWD-RESET flag triggers mandatory password change.
    After successful change, the flag is cleared and user is routed to menu.
    """
    if not request.user.is_authenticated:
        return redirect("accounts:login")

    if request.method == "POST":
        return _process_password_change(request)

    form = PasswordChangeForm(user=request.user)
    return render(request, "accounts/password_change.html", {"form": form})


def _process_password_change(request: HttpRequest) -> HttpResponse:
    """Process the password change form submission."""
    form = PasswordChangeForm(data=request.POST, user=request.user)
    if not form.is_valid():
        return render(request, "accounts/password_change.html", {"form": form})

    user = request.user
    user.set_password(form.cleaned_data["new_password"])  # type: ignore[union-attr]
    user.password_reset_required = False  # type: ignore[union-attr]
    user.save()  # type: ignore[union-attr]

    # Keep user logged in after password change (patch session auth hash in-place)
    update_session_auth_hash(request, user)

    redirect_url = get_menu_redirect_url(user.user_type)  # type: ignore[union-attr]
    messages.success(request, "Password changed successfully.")
    return redirect(redirect_url)
