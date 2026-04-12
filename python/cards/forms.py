"""
Django forms for Credit Card Management.

Translated from COBOL BMS map definitions:
- COCRDLI (card list filter screen)
- COCRDSL (card detail screen)
- COCRDUP (card update screen)
"""

from __future__ import annotations

from django import forms


class CardFilterForm(forms.Form):
    """Filter form for the card list view.

    Translated from COCRDLIC.cbl — 2000-RECEIVE-MAP.
    Corresponds to CCRDLIA BMS map input fields.
    """

    acct_id = forms.CharField(
        max_length=11,
        required=False,
        label="Account ID",
        widget=forms.TextInput(
            attrs={"placeholder": "11-digit Account ID"}
        ),
    )
    card_num = forms.CharField(
        max_length=16,
        required=False,
        label="Card Number",
        widget=forms.TextInput(
            attrs={"placeholder": "Card number prefix"}
        ),
    )


class CardUpdateForm(forms.Form):
    """Form for updating credit card details.

    Translated from COCRDUPC.cbl — 2000-PROCESS-INPUTS.
    Corresponds to CCRDUPA BMS map input fields.

    Validation rules from COBOL:
    - Name: alphabetic + spaces only (PIC X(50))
    - Status: Y or N (PIC X(01))
    - Expiry month: 1-12 (88 VALID-MONTH)
    - Expiry year: 1950-2099 (88 VALID-YEAR)
    """

    card_name = forms.CharField(
        max_length=50,
        label="Name on Card",
        help_text="Alphabetic characters and spaces only",
    )
    card_status = forms.ChoiceField(
        choices=[("Y", "Active"), ("N", "Inactive")],
        label="Card Status",
    )
    expiry_month = forms.CharField(
        max_length=2,
        label="Expiry Month",
        help_text="1-12",
    )
    expiry_year = forms.CharField(
        max_length=4,
        label="Expiry Year",
        help_text="1950-2099",
    )

    def clean_card_name(self) -> str:
        """Validate card name contains only alphabets and spaces.

        Translated from COCRDUPC.cbl — INSPECT/REPLACING logic.
        """
        name = self.cleaned_data["card_name"]
        if not all(c.isalpha() or c.isspace() for c in name):
            raise forms.ValidationError(
                "Card name can only contain alphabets and spaces"
            )
        return name

    def clean_expiry_month(self) -> str:
        """Validate expiry month is 1-12.

        Translated from COCRDUPC.cbl — 88 VALID-MONTH.
        """
        month = self.cleaned_data["expiry_month"]
        try:
            month_val = int(month)
            if not (1 <= month_val <= 12):
                raise ValueError
        except (ValueError, TypeError):
            raise forms.ValidationError(
                "Card expiry month must be between 1 and 12"
            )
        return month

    def clean_expiry_year(self) -> str:
        """Validate expiry year is 1950-2099.

        Translated from COCRDUPC.cbl — 88 VALID-YEAR.
        """
        year = self.cleaned_data["expiry_year"]
        try:
            year_val = int(year)
            # COBOL: 88 VALID-YEAR VALUES 1950 THRU 2099
            if not (1950 <= year_val <= 2099):
                raise ValueError
        except (ValueError, TypeError):
            raise forms.ValidationError(
                "Invalid card expiry year"
            )
        return year
