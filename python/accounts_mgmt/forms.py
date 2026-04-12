"""
Django forms with field-level validation for account management.

Translated from COACTUPC.cbl paragraphs:
- 1200-EDIT-MAP-INPUTS   — orchestration of all field edits
- 1210-EDIT-ACCOUNT       — account ID validation
- 1220-EDIT-YESNO         — Y/N status validation
- 1225-EDIT-ALPHA-REQD    — required alpha-only fields
- 1235-EDIT-ALPHA-OPT     — optional alpha-only fields
- 1245-EDIT-NUM-REQD      — required numeric fields
- 1250-EDIT-SIGNED-9V2    — signed decimal validation
- 1260-EDIT-US-PHONE-NUM  — NPA-NXX-XXXX phone validation
- 1265-EDIT-US-SSN        — SSN format validation (XXX-XX-XXXX)
- 1270-EDIT-US-STATE-CD   — state code validation
- 1275-EDIT-FICO-SCORE    — FICO range validation
- 1280-EDIT-US-STATE-ZIP  — state+zip combo validation

Reuses existing Phase 0 utilities — does NOT duplicate validation logic.
"""

from __future__ import annotations

import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from django import forms

# ---------------------------------------------------------------------------
# Make Phase 0 utilities importable
# ---------------------------------------------------------------------------
_python_root = Path(__file__).resolve().parent.parent
if str(_python_root) not in sys.path:
    sys.path.insert(0, str(_python_root))

from utils.date_validation import validate_date_ccyymmdd, validate_date_of_birth
from utils.lookup_codes import (
    is_valid_phone_area_code,
    is_valid_us_state_code,
    is_valid_us_state_zip_combo,
)


# ---------------------------------------------------------------------------
# Validation helpers (small, pure functions — max 20 lines each)
# ---------------------------------------------------------------------------


def _validate_yes_no(value: str, field_name: str) -> str | None:
    """Validate Y/N flag field.

    Translated from 1220-EDIT-YESNO in COACTUPC.cbl.

    Returns:
        Error message string, or ``None`` if valid.
    """
    if value.upper() not in ("Y", "N"):
        return f"{field_name} must be Y or N."
    return None


def _validate_signed_decimal(value: str, field_name: str) -> str | None:
    """Validate a signed decimal monetary field.

    Translated from 1250-EDIT-SIGNED-9V2 in COACTUPC.cbl.
    Checks that the value is a parseable decimal number.

    Returns:
        Error message string, or ``None`` if valid.
    """
    if not value or not value.strip():
        return f"{field_name} must be supplied."
    cleaned = value.strip().replace(",", "").replace("$", "")
    try:
        Decimal(cleaned)
    except InvalidOperation:
        return f"{field_name} is not valid."
    return None


def _validate_alpha_required(value: str, field_name: str) -> str | None:
    """Validate a required alphabetic-only field.

    Translated from 1225-EDIT-ALPHA-REQD in COACTUPC.cbl.

    Returns:
        Error message string, or ``None`` if valid.
    """
    if not value or not value.strip():
        return f"{field_name} must be supplied."
    if not re.match(r"^[A-Za-z ]+$", value):
        return f"{field_name} can have alphabets only."
    return None


def _validate_ssn(ssn_str: str) -> str | None:
    """Validate US Social Security Number format.

    Translated from 1265-EDIT-US-SSN in COACTUPC.cbl.
    Format: 9 digits (no dashes in storage).
    Part 1 (first 3): must not be 000, 666, or 900-999.
    Part 2 (next 2): must be 01-99.
    Part 3 (last 4): must be 0001-9999.

    Returns:
        Error message string, or ``None`` if valid.
    """
    digits = ssn_str.replace("-", "").strip()
    if not digits or len(digits) != 9 or not digits.isdigit():
        return "SSN must be 9 digits."
    part1 = digits[:3]
    part2 = digits[3:5]
    part3 = digits[5:9]
    # COBOL: Part1 should not be 000, 666, or between 900 and 999
    if part1 == "000" or part1 == "666" or 900 <= int(part1) <= 999:
        return (
            "SSN: First 3 chars should not be 000, 666, "
            "or between 900 and 999."
        )
    if int(part2) == 0:
        return "SSN 4th & 5th chars must not be zero."
    if int(part3) == 0:
        return "SSN Last 4 chars must not be zero."
    return None


def _validate_phone_number(
    area_code: str, prefix: str, line_num: str, field_name: str,
) -> str | None:
    """Validate a US phone number in NPA-NXX-XXXX parts.

    Translated from 1260-EDIT-US-PHONE-NUM in COACTUPC.cbl.
    All three parts optional together, but if any supplied all must be.

    Returns:
        Error message string, or ``None`` if valid.
    """
    all_blank = (
        (not area_code or not area_code.strip())
        and (not prefix or not prefix.strip())
        and (not line_num or not line_num.strip())
    )
    if all_blank:
        return None  # Phone is optional per COBOL

    # Area code checks (EDIT-AREA-CODE)
    if not area_code or not area_code.strip():
        return f"{field_name}: Area code must be supplied."
    if not area_code.strip().isdigit() or len(area_code.strip()) != 3:
        return f"{field_name}: Area code must be a 3 digit number."
    if int(area_code.strip()) == 0:
        return f"{field_name}: Area code cannot be zero."
    if not is_valid_phone_area_code(area_code.strip()):
        return (
            f"{field_name}: Not valid North America "
            "general purpose area code."
        )

    # Prefix checks (EDIT-US-PHONE-PREFIX)
    if not prefix or not prefix.strip():
        return f"{field_name}: Prefix code must be supplied."
    if not prefix.strip().isdigit() or len(prefix.strip()) != 3:
        return f"{field_name}: Prefix code must be a 3 digit number."
    if int(prefix.strip()) == 0:
        return f"{field_name}: Prefix code cannot be zero."

    # Line number checks (EDIT-US-PHONE-LINENUM)
    if not line_num or not line_num.strip():
        return f"{field_name}: Line number code must be supplied."
    if not line_num.strip().isdigit() or len(line_num.strip()) != 4:
        return (
            f"{field_name}: Line number code must be a 4 digit number."
        )
    if int(line_num.strip()) == 0:
        return f"{field_name}: Line number code cannot be zero."

    return None


def _validate_fico_score(score_str: str) -> str | None:
    """Validate FICO credit score range.

    Translated from 1275-EDIT-FICO-SCORE in COACTUPC.cbl.
    # HARDCODED THRESHOLD: FICO range 300-850 — flag for human review.

    Returns:
        Error message string, or ``None`` if valid.
    """
    if not score_str or not score_str.strip():
        return "FICO Score must be supplied."
    if not score_str.strip().isdigit():
        return "FICO Score must be all numeric."
    score = int(score_str.strip())
    if score == 0:
        return "FICO Score must not be zero."
    # HARDCODED THRESHOLD — flag for human review before migration
    if score < 300 or score > 850:
        return "FICO Score: should be between 300 and 850."
    return None


def _validate_date_field(
    date_str: str, field_name: str, is_dob: bool = False,
) -> str | None:
    """Validate a CCYYMMDD date field using Phase 0 utilities.

    Translated from EDIT-DATE-CCYYMMDD in COACTUPC.cbl.
    Reuses ``python/utils/date_validation.py``.

    Returns:
        Error message string, or ``None`` if valid.
    """
    if not date_str or not date_str.strip():
        return None  # Dates may be blank in the COBOL flow
    cleaned = date_str.strip().replace("-", "")
    if is_dob:
        result = validate_date_of_birth(cleaned, field_name)
    else:
        result = validate_date_ccyymmdd(cleaned, field_name)
    if not result.is_valid:
        return result.error_message
    return None


def _validate_state_and_zip(
    state_cd: str, zip_code: str,
) -> str | None:
    """Validate US state code and state+zip combination.

    Translated from 1270-EDIT-US-STATE-CD + 1280-EDIT-US-STATE-ZIP-CD
    in COACTUPC.cbl. Reuses ``python/utils/lookup_codes.py``.

    Returns:
        Error message string, or ``None`` if valid.
    """
    if not state_cd or not state_cd.strip():
        return None
    state_upper = state_cd.strip().upper()
    if not is_valid_us_state_code(state_upper):
        return "State: is not a valid state code."

    if zip_code and len(zip_code.strip()) >= 2:
        zip_first_two = zip_code.strip()[:2]
        if not is_valid_us_state_zip_combo(state_upper, zip_first_two):
            return "Invalid zip code for state."
    return None


# ---------------------------------------------------------------------------
# Account search form (used by COACTVWC — account view search)
# ---------------------------------------------------------------------------


class AccountSearchForm(forms.Form):
    """Search form for account lookup by account ID.

    Translated from 2210-EDIT-ACCOUNT in COACTVWC.cbl.
    """

    acct_id = forms.CharField(
        label="Account ID",
        max_length=11,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "11-digit account number"}),
    )

    def clean_acct_id(self) -> str:
        """Validate account ID is an 11-digit non-zero number.

        Translated from 2210-EDIT-ACCOUNT in COACTVWC.cbl:
        'Account Filter must be a non-zero 11 digit number'.
        """
        value = self.cleaned_data["acct_id"].strip()
        if not value.isdigit() or len(value) != 11:
            raise forms.ValidationError(
                "Account ID must be an 11-digit number."
            )
        if int(value) == 0:
            raise forms.ValidationError(
                "Account ID must be a non-zero 11 digit number."
            )
        return value


# ---------------------------------------------------------------------------
# Account update form (the big one — decomposed from COACTUPC.cbl)
# ---------------------------------------------------------------------------


class AccountUpdateForm(forms.Form):
    """Update form for account and customer data.

    Translated from COACTUPC.cbl 1200-EDIT-MAP-INPUTS and sub-paragraphs.
    Each field's validation is delegated to small helper functions above.
    All monetary fields use ``str`` input and are converted to ``Decimal``
    in the service layer — never float.
    """

    # --- Account fields ---
    acct_active_status = forms.CharField(
        label="Active Status (Y/N)", max_length=1, required=True,
    )
    acct_credit_limit = forms.CharField(
        label="Credit Limit", max_length=15, required=True,
    )
    acct_cash_credit_limit = forms.CharField(
        label="Cash Credit Limit", max_length=15, required=True,
    )
    acct_curr_bal = forms.CharField(
        label="Current Balance", max_length=15, required=True,
    )
    acct_curr_cyc_credit = forms.CharField(
        label="Current Cycle Credit", max_length=15, required=True,
    )
    acct_curr_cyc_debit = forms.CharField(
        label="Current Cycle Debit", max_length=15, required=True,
    )
    acct_open_date = forms.CharField(
        label="Open Date (YYYY-MM-DD)", max_length=10, required=False,
    )
    acct_expiration_date = forms.CharField(
        label="Expiry Date (YYYY-MM-DD)", max_length=10, required=False,
    )
    acct_reissue_date = forms.CharField(
        label="Reissue Date (YYYY-MM-DD)", max_length=10, required=False,
    )
    acct_group_id = forms.CharField(
        label="Group ID", max_length=10, required=False,
    )

    # --- Customer fields ---
    cust_first_name = forms.CharField(
        label="First Name", max_length=25, required=True,
    )
    cust_middle_name = forms.CharField(
        label="Middle Name", max_length=25, required=False,
    )
    cust_last_name = forms.CharField(
        label="Last Name", max_length=25, required=True,
    )
    cust_addr_line_1 = forms.CharField(
        label="Address Line 1", max_length=50, required=True,
    )
    cust_addr_line_2 = forms.CharField(
        label="Address Line 2", max_length=50, required=False,
    )
    cust_addr_line_3 = forms.CharField(
        label="City", max_length=50, required=False,
    )
    cust_addr_state_cd = forms.CharField(
        label="State", max_length=2, required=True,
    )
    cust_addr_country_cd = forms.CharField(
        label="Country", max_length=3, required=False,
    )
    cust_addr_zip = forms.CharField(
        label="ZIP Code", max_length=10, required=False,
    )
    cust_phone_num_1_area = forms.CharField(
        label="Phone 1 Area Code", max_length=3, required=False,
    )
    cust_phone_num_1_prefix = forms.CharField(
        label="Phone 1 Prefix", max_length=3, required=False,
    )
    cust_phone_num_1_line = forms.CharField(
        label="Phone 1 Line", max_length=4, required=False,
    )
    cust_phone_num_2_area = forms.CharField(
        label="Phone 2 Area Code", max_length=3, required=False,
    )
    cust_phone_num_2_prefix = forms.CharField(
        label="Phone 2 Prefix", max_length=3, required=False,
    )
    cust_phone_num_2_line = forms.CharField(
        label="Phone 2 Line", max_length=4, required=False,
    )
    cust_ssn = forms.CharField(
        label="SSN", max_length=11, required=True,
    )
    cust_govt_issued_id = forms.CharField(
        label="Government ID", max_length=20, required=False,
    )
    cust_dob = forms.CharField(
        label="Date of Birth (YYYY-MM-DD)", max_length=10, required=False,
    )
    cust_eft_account_id = forms.CharField(
        label="EFT Account ID", max_length=10, required=False,
    )
    cust_pri_card_holder_ind = forms.CharField(
        label="Primary Card Holder (Y/N)", max_length=1, required=False,
    )
    cust_fico_credit_score = forms.CharField(
        label="FICO Score", max_length=3, required=True,
    )

    def clean_acct_active_status(self) -> str:
        """Validate account active status.

        Translated from 1220-EDIT-YESNO in COACTUPC.cbl.
        """
        value = self.cleaned_data["acct_active_status"]
        err = _validate_yes_no(value, "Account Active Status")
        if err:
            raise forms.ValidationError(err)
        return value.upper()

    def clean_acct_credit_limit(self) -> str:
        """Validate credit limit.

        Translated from 1250-EDIT-SIGNED-9V2 in COACTUPC.cbl.
        """
        value = self.cleaned_data["acct_credit_limit"]
        err = _validate_signed_decimal(value, "Credit Limit")
        if err:
            raise forms.ValidationError(err)
        return value.strip()

    def clean_acct_cash_credit_limit(self) -> str:
        """Validate cash credit limit.

        Translated from 1250-EDIT-SIGNED-9V2 in COACTUPC.cbl.
        """
        value = self.cleaned_data["acct_cash_credit_limit"]
        err = _validate_signed_decimal(value, "Cash Credit Limit")
        if err:
            raise forms.ValidationError(err)
        return value.strip()

    def clean_acct_curr_bal(self) -> str:
        """Validate current balance.

        Translated from 1250-EDIT-SIGNED-9V2 in COACTUPC.cbl.
        """
        value = self.cleaned_data["acct_curr_bal"]
        err = _validate_signed_decimal(value, "Current Balance")
        if err:
            raise forms.ValidationError(err)
        return value.strip()

    def clean_acct_curr_cyc_credit(self) -> str:
        """Validate current cycle credit.

        Translated from 1250-EDIT-SIGNED-9V2 in COACTUPC.cbl.
        """
        value = self.cleaned_data["acct_curr_cyc_credit"]
        err = _validate_signed_decimal(value, "Current Cycle Credit")
        if err:
            raise forms.ValidationError(err)
        return value.strip()

    def clean_acct_curr_cyc_debit(self) -> str:
        """Validate current cycle debit.

        Translated from 1250-EDIT-SIGNED-9V2 in COACTUPC.cbl.
        """
        value = self.cleaned_data["acct_curr_cyc_debit"]
        err = _validate_signed_decimal(value, "Current Cycle Debit")
        if err:
            raise forms.ValidationError(err)
        return value.strip()

    def clean_acct_open_date(self) -> str:
        """Validate open date.

        Translated from EDIT-DATE-CCYYMMDD in COACTUPC.cbl.
        """
        value = self.cleaned_data.get("acct_open_date", "")
        err = _validate_date_field(value, "Open Date")
        if err:
            raise forms.ValidationError(err)
        return value.strip() if value else ""

    def clean_acct_expiration_date(self) -> str:
        """Validate expiration date.

        Translated from EDIT-DATE-CCYYMMDD in COACTUPC.cbl.
        """
        value = self.cleaned_data.get("acct_expiration_date", "")
        err = _validate_date_field(value, "Expiry Date")
        if err:
            raise forms.ValidationError(err)
        return value.strip() if value else ""

    def clean_acct_reissue_date(self) -> str:
        """Validate reissue date.

        Translated from EDIT-DATE-CCYYMMDD in COACTUPC.cbl.
        """
        value = self.cleaned_data.get("acct_reissue_date", "")
        err = _validate_date_field(value, "Reissue Date")
        if err:
            raise forms.ValidationError(err)
        return value.strip() if value else ""

    def clean_cust_first_name(self) -> str:
        """Validate first name — required, alpha only.

        Translated from 1225-EDIT-ALPHA-REQD in COACTUPC.cbl.
        """
        value = self.cleaned_data["cust_first_name"]
        err = _validate_alpha_required(value, "First Name")
        if err:
            raise forms.ValidationError(err)
        return value.strip()

    def clean_cust_middle_name(self) -> str:
        """Validate middle name — optional, alpha only if supplied.

        Translated from 1235-EDIT-ALPHA-OPT in COACTUPC.cbl.
        """
        value = self.cleaned_data.get("cust_middle_name", "")
        if value and value.strip():
            if not re.match(r"^[A-Za-z ]+$", value.strip()):
                raise forms.ValidationError(
                    "Middle Name can have alphabets only."
                )
        return value.strip() if value else ""

    def clean_cust_last_name(self) -> str:
        """Validate last name — required, alpha only.

        Translated from 1225-EDIT-ALPHA-REQD in COACTUPC.cbl.
        """
        value = self.cleaned_data["cust_last_name"]
        err = _validate_alpha_required(value, "Last Name")
        if err:
            raise forms.ValidationError(err)
        return value.strip()

    def clean_cust_addr_line_1(self) -> str:
        """Validate address line 1 — mandatory.

        Translated from 1215-EDIT-MANDATORY in COACTUPC.cbl.
        """
        value = self.cleaned_data["cust_addr_line_1"]
        if not value or not value.strip():
            raise forms.ValidationError("Address Line 1 must be supplied.")
        return value.strip()

    def clean_cust_ssn(self) -> str:
        """Validate SSN.

        Translated from 1265-EDIT-US-SSN in COACTUPC.cbl.
        """
        value = self.cleaned_data["cust_ssn"]
        err = _validate_ssn(value)
        if err:
            raise forms.ValidationError(err)
        return value.replace("-", "").strip()

    def clean_cust_dob(self) -> str:
        """Validate date of birth.

        Translated from EDIT-DATE-CCYYMMDD + EDIT-DATE-OF-BIRTH
        in COACTUPC.cbl. Uses ``validate_date_of_birth`` to ensure
        the date is in the past.
        """
        value = self.cleaned_data.get("cust_dob", "")
        err = _validate_date_field(value, "Date of Birth", is_dob=True)
        if err:
            raise forms.ValidationError(err)
        return value.strip() if value else ""

    def clean_cust_fico_credit_score(self) -> str:
        """Validate FICO score.

        Translated from 1275-EDIT-FICO-SCORE in COACTUPC.cbl.
        """
        value = self.cleaned_data["cust_fico_credit_score"]
        err = _validate_fico_score(value)
        if err:
            raise forms.ValidationError(err)
        return value.strip()

    def clean_cust_pri_card_holder_ind(self) -> str:
        """Validate primary card holder indicator.

        Translated from 1220-EDIT-YESNO in COACTUPC.cbl.
        """
        value = self.cleaned_data.get("cust_pri_card_holder_ind", "")
        if value and value.strip():
            err = _validate_yes_no(value, "Primary Card Holder")
            if err:
                raise forms.ValidationError(err)
            return value.upper()
        return value

    def clean(self) -> dict[str, Any]:
        """Cross-field validation.

        Translated from 1200-EDIT-MAP-INPUTS in COACTUPC.cbl.
        Validates phone numbers and state+zip combinations.
        """
        cleaned = super().clean()

        # Phone 1 validation
        phone1_err = _validate_phone_number(
            cleaned.get("cust_phone_num_1_area", ""),
            cleaned.get("cust_phone_num_1_prefix", ""),
            cleaned.get("cust_phone_num_1_line", ""),
            "Phone 1",
        )
        if phone1_err:
            self.add_error(None, phone1_err)

        # Phone 2 validation
        phone2_err = _validate_phone_number(
            cleaned.get("cust_phone_num_2_area", ""),
            cleaned.get("cust_phone_num_2_prefix", ""),
            cleaned.get("cust_phone_num_2_line", ""),
            "Phone 2",
        )
        if phone2_err:
            self.add_error(None, phone2_err)

        # State + ZIP cross-validation
        state_zip_err = _validate_state_and_zip(
            cleaned.get("cust_addr_state_cd", ""),
            cleaned.get("cust_addr_zip", ""),
        )
        if state_zip_err:
            self.add_error(None, state_zip_err)

        return cleaned
