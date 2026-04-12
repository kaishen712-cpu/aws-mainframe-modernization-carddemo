"""
Shared test fixtures for the CardDemo test suite.

Provides factory functions for creating test users and common test data.
All test data is synthetic — never uses real customer data.
"""
from __future__ import annotations

import pytest

from accounts.models import CardDemoUser


@pytest.fixture()
def regular_user(db: None) -> CardDemoUser:
    """Create a regular (non-admin) test user.

    Maps to COBOL SEC-USR-TYPE = 'U' (CDEMO-USRTYP-USER).
    """
    user = CardDemoUser.objects.create_user(
        username="testuser",
        password="TestPass123!",
        first_name="John",
        last_name="Doe",
        user_type=CardDemoUser.UserType.REGULAR,
    )
    return user


@pytest.fixture()
def admin_user(db: None) -> CardDemoUser:
    """Create an admin test user.

    Maps to COBOL SEC-USR-TYPE = 'A' (CDEMO-USRTYP-ADMIN).
    """
    user = CardDemoUser.objects.create_user(
        username="adminuser",
        password="AdminPass123!",
        first_name="Jane",
        last_name="Admin",
        user_type=CardDemoUser.UserType.ADMIN,
    )
    return user


@pytest.fixture()
def password_reset_user(db: None) -> CardDemoUser:
    """Create a user that requires password reset on first login.

    Maps to COBOL SEC-USR-PWD-RESET flag.
    """
    user = CardDemoUser.objects.create_user(
        username="newuser",
        password="TempPass123!",
        first_name="New",
        last_name="User",
        user_type=CardDemoUser.UserType.REGULAR,
        password_reset_required=True,
    )
    return user
