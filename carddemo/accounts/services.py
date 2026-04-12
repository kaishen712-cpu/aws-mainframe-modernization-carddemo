"""
Authentication service layer for the CardDemo application.

Handles business logic for login throttling and user type routing.
Follows SRP: views handle HTTP, services handle business logic.

Translated from COSGN00C.cbl — the original COBOL had no throttling;
this is an improvement for the Python version to prevent brute-force attacks.
"""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    from django.http import HttpRequest

logger = logging.getLogger(__name__)

# In-memory store for login attempts.
# Key: IP address, Value: list of Unix timestamps of failed attempts.
# In production, use Redis/Memcached for distributed deployments.
_login_attempts: dict[str, list[float]] = {}


def get_client_ip(request: HttpRequest) -> str:
    """Extract client IP from request.

    Uses ``REMOTE_ADDR`` by default, which is set by the WSGI server and
    cannot be spoofed by the client.  ``X-Forwarded-For`` is only used
    when ``NUM_PROXIES`` is configured in Django settings, and in that
    case the Nth IP **from the right** is taken (where N = NUM_PROXIES).
    This prevents attackers from rotating the header to bypass throttling.

    Args:
        request: The Django HTTP request.

    Returns:
        Client IP address string.
    """
    num_proxies: int = getattr(settings, "NUM_PROXIES", 0)
    if num_proxies > 0:
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if x_forwarded_for:
            addrs = [a.strip() for a in x_forwarded_for.split(",")]
            # Take the Nth address from the right (proxy-appended)
            if len(addrs) >= num_proxies:
                return addrs[-num_proxies]
    return request.META.get("REMOTE_ADDR", "unknown")


def is_login_throttled(request: HttpRequest) -> bool:
    """Check if login attempts from this IP are throttled.

    Business rule improvement over COSGN00C.cbl: the original COBOL
    program had no brute-force protection. This adds IP-based throttling.

    FLAG FOR HUMAN REVIEW: hardcoded thresholds — LOGIN_MAX_ATTEMPTS
    and LOGIN_LOCKOUT_DURATION_SECONDS configured in settings.

    Args:
        request: The Django HTTP request.

    Returns:
        True if the IP is currently locked out.
    """
    client_ip = get_client_ip(request)
    attempts = _login_attempts.get(client_ip, [])

    max_attempts: int = settings.LOGIN_MAX_ATTEMPTS
    lockout_duration: int = settings.LOGIN_LOCKOUT_DURATION_SECONDS

    now = time.time()
    # Filter to only recent attempts within the lockout window
    recent = [ts for ts in attempts if now - ts < lockout_duration]
    _login_attempts[client_ip] = recent

    return len(recent) >= max_attempts


def record_failed_attempt(request: HttpRequest) -> None:
    """Record a failed login attempt for throttling.

    Args:
        request: The Django HTTP request.
    """
    client_ip = get_client_ip(request)
    _login_attempts.setdefault(client_ip, []).append(time.time())
    logger.warning("Failed login attempt from IP: %s", client_ip)


def clear_failed_attempts(request: HttpRequest) -> None:
    """Clear failed login attempts after successful login.

    Args:
        request: The Django HTTP request.
    """
    client_ip = get_client_ip(request)
    _login_attempts.pop(client_ip, None)


def get_menu_redirect_url(user_type: str) -> str:
    """Determine menu redirect URL based on user type.

    Translated from COSGN00C.cbl READ-USER-SEC-FILE paragraph:
    - CDEMO-USRTYP-ADMIN -> XCTL to COADM01C (admin menu)
    - Otherwise           -> XCTL to COMEN01C (main menu)

    Args:
        user_type: The user's type string ('admin' or 'regular').

    Returns:
        URL path to redirect to.
    """
    if user_type == "admin":
        return "/admin-menu/"
    return "/menu/"


def reset_throttle_store() -> None:
    """Reset the throttle store. Used in tests only."""
    _login_attempts.clear()
