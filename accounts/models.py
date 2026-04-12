"""
Custom user model for the CardDemo application.

Translated from CSUSR01Y.cpy (SEC-USER-DATA record) and COCOM01Y.cpy
(CDEMO-USER-TYPE field).

The COBOL USRSEC file stored user credentials in a flat VSAM KSDS with
plaintext passwords.  This Django model replaces that with:
- Argon2 password hashing (configured in settings)
- Database-backed sessions (replaces CICS COMMAREA)
- User type field mapping SEC-USR-TYPE ('A' = admin, 'U' = regular)
"""
from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models


class CardDemoUser(AbstractUser):
    """Custom user extending Django's AbstractUser.

    Maps from COBOL SEC-USER-DATA record (CSUSR01Y.cpy):
    - SEC-USR-ID       -> username (inherited from AbstractUser)
    - SEC-USR-FNAME    -> first_name (inherited from AbstractUser)
    - SEC-USR-LNAME    -> last_name (inherited from AbstractUser)
    - SEC-USR-PWD      -> password (hashed, inherited from AbstractUser)
    - SEC-USR-TYPE     -> user_type field below

    COBOL CDEMO-USER-TYPE values (COCOM01Y.cpy):
    - 'A' (CDEMO-USRTYP-ADMIN) -> 'admin'
    - 'U' (CDEMO-USRTYP-USER)  -> 'regular'
    """

    class UserType(models.TextChoices):
        """User type choices mapping from COBOL SEC-USR-TYPE."""

        ADMIN = "admin", "Admin"
        REGULAR = "regular", "Regular"

    user_type = models.CharField(
        max_length=10,
        choices=UserType.choices,
        default=UserType.REGULAR,
        help_text="Maps from COBOL SEC-USR-TYPE: 'A' = admin, 'U' = regular",
    )

    # Business rule from COSGN00C.cbl: first-time login detection
    # Original COBOL had no explicit flag; we add one for password reset flow.
    password_reset_required = models.BooleanField(
        default=False,
        help_text="When True, user must change password on next login (SEC-USR-PWD-RESET)",
    )

    class Meta:
        db_table = "carddemo_user"
        verbose_name = "CardDemo User"
        verbose_name_plural = "CardDemo Users"

    def __str__(self) -> str:
        return f"{self.username} ({self.get_user_type_display()})"

    @property
    def is_admin_user(self) -> bool:
        """Check if user has admin type.

        Translated from COCOM01Y.cpy: 88 CDEMO-USRTYP-ADMIN VALUE 'A'.
        """
        return self.user_type == self.UserType.ADMIN

    @property
    def is_regular_user(self) -> bool:
        """Check if user has regular type.

        Translated from COCOM01Y.cpy: 88 CDEMO-USRTYP-USER VALUE 'U'.
        """
        return self.user_type == self.UserType.REGULAR
