"""
Django forms for User Administration.

Translated from COBOL BMS map definitions:
- COUSR0A (user list filter)
- COUSR1A (user add)
- COUSR2A (user update)
- COUSR3A (user delete confirmation)
"""

from __future__ import annotations

from django import forms


class UserFilterForm(forms.Form):
    """Filter form for the user list view.

    Translated from COUSR00C.cbl — 2000-RECEIVE-MAP.
    """

    search = forms.CharField(
        max_length=50,
        required=False,
        label="Search",
        widget=forms.TextInput(
            attrs={"placeholder": "Search by username or name"}
        ),
    )


class UserCreateForm(forms.Form):
    """Form for creating a new user.

    Translated from COUSR01C.cbl — user add screen fields.

    Validation rules from COBOL:
    - Username: required, max 8 chars (PIC X(08))
    - Password: required, max 8 chars (PIC X(08))
    - First name: required, max 20 chars (PIC X(20))
    - Last name: required, max 20 chars (PIC X(20))
    - User type: A (Admin) or U (User) (PIC X(01))
    """

    username = forms.CharField(
        max_length=8,
        label="User ID",
        help_text="Max 8 characters",
    )
    password = forms.CharField(
        max_length=8,
        label="Password",
        widget=forms.PasswordInput,
        help_text="Max 8 characters",
    )
    first_name = forms.CharField(
        max_length=20,
        label="First Name",
    )
    last_name = forms.CharField(
        max_length=20,
        label="Last Name",
    )
    user_type = forms.ChoiceField(
        choices=[("U", "Regular User"), ("A", "Admin")],
        label="User Type",
    )


class UserUpdateForm(forms.Form):
    """Form for updating a user.

    Translated from COUSR02C.cbl — user update screen fields.
    Username is read-only (cannot change primary key).
    Password field optional (blank = no change).
    """

    first_name = forms.CharField(
        max_length=20,
        label="First Name",
    )
    last_name = forms.CharField(
        max_length=20,
        label="Last Name",
    )
    user_type = forms.ChoiceField(
        choices=[("U", "Regular User"), ("A", "Admin")],
        label="User Type",
    )
    new_password = forms.CharField(
        max_length=8,
        required=False,
        label="New Password",
        widget=forms.PasswordInput,
        help_text="Leave blank to keep current password",
    )
