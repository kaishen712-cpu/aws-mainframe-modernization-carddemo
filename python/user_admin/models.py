"""
Django ORM models for User Administration.

Translated from COBOL copybook COUSR0 (USRSEC VSAM file).

The original COBOL user security record contains user ID, password,
first name, last name, and user type. In Django, we extend the
built-in auth.User model with a profile for COBOL-specific fields.
"""

from __future__ import annotations

from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    """Extended user profile for CardDemo-specific fields.

    Translated from COUSR0 copybook (USRSEC VSAM file).
    Links to Django's built-in User model for authentication.

    The original COBOL record contains:
    - SEC-USR-ID PIC X(08) → User.username
    - SEC-USR-PWD PIC X(08) → User.password (hashed by Django)
    - SEC-USR-FNAME PIC X(20) → User.first_name
    - SEC-USR-LNAME PIC X(20) → User.last_name
    - SEC-USR-TYPE PIC X(01) → user_type field
    """

    USER_TYPE_CHOICES = [
        ("A", "Admin"),
        ("U", "Regular User"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="carddemo_profile",
    )
    user_type = models.CharField(
        max_length=1,
        choices=USER_TYPE_CHOICES,
        default="U",
        help_text="SEC-USR-TYPE PIC X(01) — A=Admin, U=User",
    )

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self) -> str:
        """Return username and type."""
        return f"{self.user.username} ({self.get_user_type_display()})"

    @property
    def is_admin(self) -> bool:
        """Check if user has admin type."""
        return self.user_type == "A"
