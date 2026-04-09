"""
COACTUPC - Account Update Program (Python Translation)

Translated from the COBOL program COACTUPC.CBL (4,236 lines) in the AWS
CardDemo mainframe modernization project.  This is the largest program in
the codebase and implements full account CRUD with complex field-level
validation.

Original: CICS COBOL program using BMS maps and VSAM files.
This translation separates the pure business logic (validation, change
detection, update operations) from the CICS presentation layer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from coactvwc import (
    AccountRecord,
    AccountRepository,
    CardXrefRepository,
    CustomerRepository,
    InMemoryAccountRepository,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROGRAM_NAME = "COACTUPC"
TRANSACTION_ID = "CAUP"

TITLE_01 = "      AWS Mainframe Modernization       "
TITLE_02 = "              CardDemo                  "

# Valid account active status values
VALID_ACTIVE_STATUSES = {"Y", "N"}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """Outcome of a validation step."""
    is_valid: bool = True
    error_message: str = ""
    error_field: str = ""


@dataclass
class AccountUpdateInput:
    """
    All user-supplied fields from the Account Update screen (CACTUPAI).

    Corresponds to the screen input fields plus the old-values snapshot
    stored in the COMMAREA (WS-THIS-PROGCOMMAREA).
    """
    acct_id: str = ""
    active_status: str = ""
    curr_bal: str = ""
    credit_limit: str = ""
    cash_credit_limit: str = ""
    open_date: str = ""
    expiration_date: str = ""
    reissue_date: str = ""
    curr_cyc_credit: str = ""
    curr_cyc_debit: str = ""
    group_id: str = ""
    # Customer fields (read-only display, but included for change detection)
    cust_first_name: str = ""
    cust_middle_name: str = ""
    cust_last_name: str = ""
    cust_addr_line_1: str = ""
    cust_addr_line_2: str = ""
    cust_addr_line_3: str = ""
    cust_addr_state_cd: str = ""
    cust_addr_country_cd: str = ""
    cust_addr_zip: str = ""
    cust_phone_num_1: str = ""
    cust_phone_num_2: str = ""
    cust_govt_issued_id: str = ""
    cust_eft_account_id: str = ""
    cust_pri_card_holder_ind: str = ""
    # Confirmation flag
    confirm: str = ""


@dataclass
class AccountUpdateResult:
    """Outcome of an update-account operation."""
    success: bool = False
    message: str = ""
    info_message: str = ""
    changes_detected: bool = False
    needs_confirmation: bool = False


# ---------------------------------------------------------------------------
# Validation functions
# ---------------------------------------------------------------------------

def validate_account_id(acct_id_input: str) -> ValidationResult:
    """
    Validate the account ID for the update screen.

    Business rules (from 2210-EDIT-ACCOUNT):
    1. Must be supplied.
    2. Must be numeric.
    3. Must not be all zeros.
    """
    raw = acct_id_input.strip()

    if raw == "" or raw == "*":
        return ValidationResult(
            is_valid=False,
            error_message="Account number not provided",
            error_field="acct_id",
        )

    if not raw.isdigit():
        return ValidationResult(
            is_valid=False,
            error_message=(
                "Account number must be a non zero 11 digit number"
            ),
            error_field="acct_id",
        )

    if int(raw) == 0:
        return ValidationResult(
            is_valid=False,
            error_message=(
                "Account number must be a non zero 11 digit number"
            ),
            error_field="acct_id",
        )

    return ValidationResult(is_valid=True)


def validate_active_status(status: str) -> ValidationResult:
    """
    Validate the account active status field.

    Business rules: Must be 'Y' or 'N'.
    """
    s = status.strip().upper()
    if s not in VALID_ACTIVE_STATUSES:
        return ValidationResult(
            is_valid=False,
            error_message="Account Active Status must be Y or N",
            error_field="active_status",
        )
    return ValidationResult(is_valid=True)


def validate_currency_field(
    value: str,
    field_name: str,
    display_name: str,
) -> ValidationResult:
    """
    Validate a currency / numeric amount field.

    Business rules:
    - Must be supplied (not blank).
    - Must be a valid number.
    """
    raw = value.strip()
    if raw == "":
        return ValidationResult(
            is_valid=False,
            error_message=f"{display_name} must be supplied",
            error_field=field_name,
        )

    # Strip commas and leading +/- for parsing
    cleaned = raw.replace(",", "").replace("+", "").lstrip()
    try:
        float(cleaned)
    except ValueError:
        return ValidationResult(
            is_valid=False,
            error_message=f"{display_name} is not valid",
            error_field=field_name,
        )

    return ValidationResult(is_valid=True)


def validate_date_field(
    value: str,
    field_name: str,
    display_name: str,
) -> ValidationResult:
    """
    Validate a date field in YYYY-MM-DD format.

    Business rules:
    - Must be supplied.
    - Must be a valid calendar date.
    - Month must be 1-12.
    - Year must be reasonable (>= 1000).
    """
    raw = value.strip()
    if raw == "":
        return ValidationResult(
            is_valid=False,
            error_message=f"{display_name} must be supplied",
            error_field=field_name,
        )

    # Try parsing as YYYY-MM-DD
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return ValidationResult(
            is_valid=False,
            error_message=f"Invalid {display_name} format (expected YYYY-MM-DD)",
            error_field=field_name,
        )

    try:
        dt = datetime.strptime(raw, "%Y-%m-%d")
        month = dt.month
        year = dt.year
    except ValueError:
        return ValidationResult(
            is_valid=False,
            error_message=f"Invalid {display_name}",
            error_field=field_name,
        )

    if month < 1 or month > 12:
        return ValidationResult(
            is_valid=False,
            error_message="Card expiry month must be between 1 and 12",
            error_field=field_name,
        )

    if year < 1000:
        return ValidationResult(
            is_valid=False,
            error_message="Invalid card expiry year",
            error_field=field_name,
        )

    return ValidationResult(is_valid=True)


def validate_account_fields(update_input: AccountUpdateInput) -> ValidationResult:
    """
    Validate all updatable account fields.

    Runs field-level validations in sequence, returning the first error
    encountered (matching COBOL's early-exit pattern).
    """
    # Active status
    v = validate_active_status(update_input.active_status)
    if not v.is_valid:
        return v

    # Credit Limit
    v = validate_currency_field(
        update_input.credit_limit, "credit_limit", "Credit Limit",
    )
    if not v.is_valid:
        return v

    # Cash Credit Limit
    v = validate_currency_field(
        update_input.cash_credit_limit, "cash_credit_limit",
        "Cash Credit Limit",
    )
    if not v.is_valid:
        return v

    # Expiration Date
    if update_input.expiration_date.strip():
        v = validate_date_field(
            update_input.expiration_date, "expiration_date",
            "expiration date",
        )
        if not v.is_valid:
            return v

    # Reissue Date
    if update_input.reissue_date.strip():
        v = validate_date_field(
            update_input.reissue_date, "reissue_date",
            "reissue date",
        )
        if not v.is_valid:
            return v

    return ValidationResult(is_valid=True)


def validate_customer_name(name: str, field_name: str) -> ValidationResult:
    """
    Validate a customer name field (alpha + spaces only).

    Business rules: Name can only contain alphabets and spaces.
    """
    raw = name.strip()
    if raw == "":
        return ValidationResult(
            is_valid=False,
            error_message=f"{field_name} not provided",
            error_field=field_name,
        )

    if not all(c.isalpha() or c.isspace() for c in raw):
        return ValidationResult(
            is_valid=False,
            error_message="Name can only contain alphabets and spaces",
            error_field=field_name,
        )

    return ValidationResult(is_valid=True)


# ---------------------------------------------------------------------------
# Change detection
# ---------------------------------------------------------------------------

def detect_account_changes(
    old_account: AccountRecord,
    update_input: AccountUpdateInput,
) -> dict[str, tuple[str, str]]:
    """
    Compare current account values with submitted input.

    Returns a dict of field_name -> (old_value, new_value) for each
    field that has changed.  This corresponds to the COBOL program's
    comparison of ACUP-OLD-xxx with ACUP-NEW-xxx fields.
    """
    changes: dict[str, tuple[str, str]] = {}

    field_pairs = [
        ("active_status", old_account.active_status,
         update_input.active_status.strip().upper()),
        ("credit_limit", _format_amount(old_account.credit_limit),
         update_input.credit_limit.strip()),
        ("cash_credit_limit", _format_amount(old_account.cash_credit_limit),
         update_input.cash_credit_limit.strip()),
        ("expiration_date", old_account.expiration_date,
         update_input.expiration_date.strip()),
        ("reissue_date", old_account.reissue_date,
         update_input.reissue_date.strip()),
        ("group_id", old_account.group_id.strip(),
         update_input.group_id.strip()),
    ]

    for field_name, old_val, new_val in field_pairs:
        if old_val != new_val and new_val != "":
            changes[field_name] = (old_val, new_val)

    return changes


# ---------------------------------------------------------------------------
# Core update logic
# ---------------------------------------------------------------------------

def lookup_account_for_update(
    acct_id_input: str,
    acct_repo: AccountRepository,
    xref_repo: CardXrefRepository,
    cust_repo: CustomerRepository,
) -> AccountUpdateResult:
    """
    Validate account ID and fetch account + customer data for editing.

    Corresponds to the initial fetch flow in COACTUPC when the user
    first enters an account ID.
    """
    val = validate_account_id(acct_id_input)
    if not val.is_valid:
        return AccountUpdateResult(success=False, message=val.error_message)

    normalised = acct_id_input.strip().zfill(11)

    xref = xref_repo.lookup_by_account(normalised)
    if xref is None:
        return AccountUpdateResult(
            success=False,
            message="Did not find this account in account card xref file",
        )

    account = acct_repo.get_account(normalised)
    if account is None:
        return AccountUpdateResult(
            success=False,
            message="Did not find this account in account master file",
        )

    customer = cust_repo.get_customer(xref.cust_id)
    if customer is None:
        return AccountUpdateResult(
            success=False,
            message="Did not find associated customer in master file",
        )

    return AccountUpdateResult(
        success=True,
        message="Details of selected account shown above",
        info_message="Details of selected account shown above",
    )


def update_account(
    acct_id: str,
    update_input: AccountUpdateInput,
    old_account: AccountRecord,
    acct_repo: AccountRepository,
    confirmed: bool = False,
) -> AccountUpdateResult:
    """
    Full account-update workflow: validate, detect changes, apply.

    Parameters
    ----------
    acct_id : str
        The 11-digit account ID.
    update_input : AccountUpdateInput
        The user's submitted field values.
    old_account : AccountRecord
        The original account record fetched before editing.
    acct_repo : AccountRepository
        Data access for account records (must support update).
    confirmed : bool
        Whether the user has confirmed the changes (PF5).

    Returns
    -------
    AccountUpdateResult
        Indicates success, validation errors, or need for confirmation.
    """
    # Step 1: Validate all fields
    val = validate_account_fields(update_input)
    if not val.is_valid:
        return AccountUpdateResult(
            success=False,
            message=val.error_message,
        )

    # Step 2: Detect changes
    changes = detect_account_changes(old_account, update_input)
    if not changes:
        return AccountUpdateResult(
            success=False,
            message="No change detected with respect to values fetched.",
            changes_detected=False,
        )

    # Step 3: If not confirmed, prompt
    if not confirmed:
        return AccountUpdateResult(
            success=False,
            message="",
            info_message="Changes validated.Press F5 to save",
            changes_detected=True,
            needs_confirmation=True,
        )

    # Step 4: Apply the update
    normalised = acct_id.strip().zfill(11)
    updated = _apply_changes(old_account, update_input)

    if isinstance(acct_repo, InMemoryAccountRepository):
        acct_repo.accounts[normalised] = updated
        return AccountUpdateResult(
            success=True,
            message="",
            info_message="Changes committed to database",
            changes_detected=True,
        )

    return AccountUpdateResult(
        success=False,
        message="Update of record failed",
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _apply_changes(
    old_account: AccountRecord,
    update_input: AccountUpdateInput,
) -> AccountRecord:
    """Build a new AccountRecord with applied changes."""
    return AccountRecord(
        acct_id=old_account.acct_id,
        active_status=(
            update_input.active_status.strip().upper()
            if update_input.active_status.strip()
            else old_account.active_status
        ),
        curr_bal=old_account.curr_bal,
        credit_limit=(
            _parse_amount(update_input.credit_limit)
            if update_input.credit_limit.strip()
            else old_account.credit_limit
        ),
        cash_credit_limit=(
            _parse_amount(update_input.cash_credit_limit)
            if update_input.cash_credit_limit.strip()
            else old_account.cash_credit_limit
        ),
        open_date=old_account.open_date,
        expiration_date=(
            update_input.expiration_date.strip()
            if update_input.expiration_date.strip()
            else old_account.expiration_date
        ),
        reissue_date=(
            update_input.reissue_date.strip()
            if update_input.reissue_date.strip()
            else old_account.reissue_date
        ),
        curr_cyc_credit=old_account.curr_cyc_credit,
        curr_cyc_debit=old_account.curr_cyc_debit,
        addr_zip=old_account.addr_zip,
        group_id=(
            update_input.group_id.strip()
            if update_input.group_id.strip()
            else old_account.group_id
        ),
    )


def _parse_amount(value: str) -> float:
    """Parse a currency string to a float value."""
    cleaned = value.strip().replace(",", "").replace("+", "").replace("$", "")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _format_amount(value: float) -> str:
    """Format a float to a currency display string."""
    return f"{value:.2f}"


def get_header_info() -> dict[str, str]:
    """Return screen header information for the Account Update screen."""
    now = datetime.now()
    return {
        "title01": TITLE_01,
        "title02": TITLE_02,
        "program_name": PROGRAM_NAME,
        "transaction_id": TRANSACTION_ID,
        "current_date": now.strftime("%m/%d/%y"),
        "current_time": now.strftime("%H:%M:%S"),
    }
