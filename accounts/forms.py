"""
Authentication forms for the CardDemo application.

Translated from COSGN00C.cbl sign-on screen fields:
- USERIDI OF COSGN0AI -> username field
- PASSWDI OF COSGN0AI -> password field
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from django import forms

if TYPE_CHECKING:
    from accounts.models import CardDemoUser


class LoginForm(forms.Form):
    """Login form for CardDemo sign-on.

    Translated from COSGN00C.cbl SEND-SIGNON-SCREEN paragraph.
    Maps BMS map COSGN0A fields to Django form fields.
    """

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "User ID",
                "autofocus": True,
                "id": "username",
            }
        ),
        label="User ID",
        help_text="Maps from COBOL USERIDI OF COSGN0AI",
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Password",
                "id": "password",
            }
        ),
        label="Password",
        help_text="Maps from COBOL PASSWDI OF COSGN0AI",
    )


class PasswordChangeForm(forms.Form):
    """Password change form for first-time login / forced reset.

    Business rule: SEC-USR-PWD-RESET flag triggers this form.
    Accepts an optional ``user`` kwarg so that
    ``UserAttributeSimilarityValidator`` can check the new password
    against the user's attributes (username, email, name).
    """

    new_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "New Password"}
        ),
        label="New Password",
        min_length=8,
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Confirm Password"}
        ),
        label="Confirm Password",
        min_length=8,
    )

    def __init__(
        self,
        *args: object,
        user: CardDemoUser | None = None,
        **kwargs: object,
    ) -> None:
        """Store the user for password-similarity validation."""
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self) -> dict[str, str]:
        """Validate that new and confirm passwords match and meet strength rules."""
        cleaned_data = super().clean()
        new_pwd = cleaned_data.get("new_password", "")
        confirm_pwd = cleaned_data.get("confirm_password", "")
        if new_pwd and confirm_pwd and new_pwd != confirm_pwd:
            raise forms.ValidationError("Passwords do not match.")
        # Run AUTH_PASSWORD_VALIDATORS (MinimumLength, CommonPassword, etc.)
        # Pass user so UserAttributeSimilarityValidator works correctly.
        if new_pwd:
            from django.contrib.auth.password_validation import validate_password

            validate_password(new_pwd, user=self.user)
        return cleaned_data
