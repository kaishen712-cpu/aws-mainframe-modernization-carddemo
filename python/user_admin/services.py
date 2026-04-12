"""
Business logic services for User Administration.

Translated from COBOL programs:
- COUSR00C.cbl — User list
- COUSR01C.cbl — User add
- COUSR02C.cbl — User update
- COUSR03C.cbl — User delete

Follows SRP: views handle HTTP, services handle business logic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from django.contrib.auth.models import User
from django.db.models import QuerySet

from python.user_admin.models import UserProfile

logger = logging.getLogger(__name__)


@dataclass
class UserOperationResult:
    """Outcome of a user administration operation."""

    success: bool = False
    message: str = ""


def is_admin_user(user: User) -> bool:
    """Check if a user has admin privileges.

    Translated from COBOL SEC-USR-TYPE = 'A' check.
    Used with @user_passes_test decorator.

    Args:
        user: Django User instance.

    Returns:
        True if user is staff or has admin profile type.
    """
    if user.is_staff or user.is_superuser:
        return True
    try:
        profile = user.carddemo_profile
        return profile.is_admin
    except UserProfile.DoesNotExist:
        return False


def get_user_list(search_query: str = "") -> QuerySet[User]:
    """Return filtered user queryset.

    Translated from COUSR00C.cbl — 9000-READ-DATA.

    Business rules:
    - Admin sees all users.
    - Optional search by username or name.
    - Results ordered by username.

    Args:
        search_query: Optional search string for username/name.

    Returns:
        Filtered queryset of User objects.
    """
    queryset = User.objects.all()

    if search_query:
        queryset = queryset.filter(
            username__icontains=search_query,
        ) | queryset.filter(
            first_name__icontains=search_query,
        ) | queryset.filter(
            last_name__icontains=search_query,
        )

    return queryset.order_by("username")


def create_user(
    username: str,
    password: str,
    first_name: str,
    last_name: str,
    user_type: str,
) -> UserOperationResult:
    """Create a new user with profile.

    Translated from COUSR01C.cbl — ADD-USER.

    Business rules:
    - Username must be unique (DUPKEY check in COBOL).
    - Password required (SEC-USR-PWD NOT = SPACES).
    - First and last names required.
    - User type must be A or U.

    Args:
        username: Unique username (SEC-USR-ID).
        password: User password.
        first_name: First name (SEC-USR-FNAME).
        last_name: Last name (SEC-USR-LNAME).
        user_type: User type A=Admin, U=User (SEC-USR-TYPE).

    Returns:
        UserOperationResult with outcome.
    """
    if not username.strip():
        return UserOperationResult(
            success=False, message="User ID must be entered...",
        )

    if not password.strip():
        return UserOperationResult(
            success=False, message="Password must be entered...",
        )

    if not first_name.strip():
        return UserOperationResult(
            success=False, message="First Name must be entered...",
        )

    if not last_name.strip():
        return UserOperationResult(
            success=False, message="Last Name must be entered...",
        )

    if user_type.upper() not in ("A", "U"):
        return UserOperationResult(
            success=False,
            message="User Type must be A or U...",
        )

    if User.objects.filter(username=username.strip()).exists():
        return UserOperationResult(
            success=False,
            message="User ID already exists...",
        )

    user = User.objects.create_user(
        username=username.strip(),
        password=password,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        is_staff=(user_type.upper() == "A"),
    )

    UserProfile.objects.create(
        user=user,
        user_type=user_type.upper(),
    )

    logger.info("User created successfully: %s", username)
    return UserOperationResult(
        success=True, message="User created successfully.",
    )


def update_user(
    user_id: int,
    first_name: str,
    last_name: str,
    user_type: str,
    new_password: str = "",
) -> UserOperationResult:
    """Update an existing user.

    Translated from COUSR02C.cbl — UPDATE-USER.

    Business rules:
    - User must exist (NOTFND check).
    - First and last names required.
    - User type must be A or U.
    - Password updated only if non-empty.

    Args:
        user_id: Django User primary key.
        first_name: Updated first name.
        last_name: Updated last name.
        user_type: Updated user type.
        new_password: New password (blank = no change).

    Returns:
        UserOperationResult with outcome.
    """
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return UserOperationResult(
            success=False, message="User not found...",
        )

    if not first_name.strip():
        return UserOperationResult(
            success=False, message="First Name must be entered...",
        )

    if not last_name.strip():
        return UserOperationResult(
            success=False, message="Last Name must be entered...",
        )

    if user_type.upper() not in ("A", "U"):
        return UserOperationResult(
            success=False,
            message="User Type must be A or U...",
        )

    user.first_name = first_name.strip()
    user.last_name = last_name.strip()
    user.is_staff = (user_type.upper() == "A")

    if new_password.strip():
        user.set_password(new_password)

    user.save()

    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.user_type = user_type.upper()
    profile.save()

    logger.info("User updated successfully: %s", user.username)
    return UserOperationResult(
        success=True, message="User updated successfully.",
    )


def delete_user(user_id: int) -> UserOperationResult:
    """Delete a user.

    Translated from COUSR03C.cbl — DELETE-USER.

    Business rules:
    - User must exist (NOTFND check).
    - Confirmation required before delete (handled in view).
    - Cascades to delete UserProfile.

    Args:
        user_id: Django User primary key.

    Returns:
        UserOperationResult with outcome.
    """
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return UserOperationResult(
            success=False, message="User not found...",
        )

    username = user.username
    user.delete()

    logger.info("User deleted successfully: %s", username)
    return UserOperationResult(
        success=True, message="User deleted successfully.",
    )
