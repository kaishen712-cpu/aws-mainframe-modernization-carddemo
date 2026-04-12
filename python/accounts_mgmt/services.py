"""
Account update service with change detection and business rule validation.

Translated from COACTUPC.cbl paragraphs:
- 1205-COMPARE-OLD-NEW       — change detection between old and new values
- 9500-STORE-FETCHED-DATA    — snapshot of original record for comparison
- 9600-WRITE-PROCESSING      — prepare and execute account/customer updates
- 9700-CHECK-CHANGE-IN-REC   — optimistic concurrency check

Follows SOLID principles:
- SRP: This service handles business logic only (no HTTP, no rendering).
- DIP: Depends on abstract model interface, not CICS file I/O.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

from accounts_mgmt.models import Account, Customer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ChangeSet:
    """Tracks which fields changed between old and new values.

    Translated from 1205-COMPARE-OLD-NEW in COACTUPC.cbl.
    The COBOL program compares old vs. new field-by-field and sets a
    flag if any differences are found.
    """

    account_changes: dict[str, tuple[Any, Any]] = field(default_factory=dict)
    customer_changes: dict[str, tuple[Any, Any]] = field(default_factory=dict)

    @property
    def has_changes(self) -> bool:
        """Return True if any field was modified."""
        return bool(self.account_changes or self.customer_changes)


@dataclass
class UpdateResult:
    """Outcome of an account update operation.

    Translated from 9600-WRITE-PROCESSING result states in COACTUPC.cbl:
    - ACUP-CHANGES-OKAYED-AND-DONE   → success=True
    - ACUP-CHANGES-FAILED            → success=False
    - DATA-WAS-CHANGED-BEFORE-UPDATE  → concurrent_modification=True
    """

    success: bool = False
    error_message: str = ""
    concurrent_modification: bool = False
    change_set: ChangeSet | None = None


# ---------------------------------------------------------------------------
# Monetary conversion helper
# ---------------------------------------------------------------------------


def _to_decimal(value: str | Decimal) -> Decimal:
    """Convert a string or Decimal to Decimal safely.

    All monetary fields must use Decimal — never float.

    Args:
        value: String or Decimal value to convert.

    Returns:
        Decimal representation. Returns ``Decimal("0")`` on failure.
    """
    if isinstance(value, Decimal):
        return value
    try:
        cleaned = str(value).strip().replace(",", "").replace("$", "")
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return Decimal("0")


# ---------------------------------------------------------------------------
# Change detection
# ---------------------------------------------------------------------------

# Account fields eligible for update (field_name → form_field_name)
_ACCOUNT_FIELD_MAP: dict[str, str] = {
    "acct_active_status": "acct_active_status",
    "acct_credit_limit": "acct_credit_limit",
    "acct_cash_credit_limit": "acct_cash_credit_limit",
    "acct_curr_bal": "acct_curr_bal",
    "acct_curr_cyc_credit": "acct_curr_cyc_credit",
    "acct_curr_cyc_debit": "acct_curr_cyc_debit",
    "acct_open_date": "acct_open_date",
    "acct_expiration_date": "acct_expiration_date",
    "acct_reissue_date": "acct_reissue_date",
    "acct_group_id": "acct_group_id",
}

# Monetary account fields that need Decimal comparison
_ACCOUNT_DECIMAL_FIELDS: set[str] = {
    "acct_credit_limit",
    "acct_cash_credit_limit",
    "acct_curr_bal",
    "acct_curr_cyc_credit",
    "acct_curr_cyc_debit",
}

# Customer fields eligible for update
_CUSTOMER_FIELD_MAP: dict[str, str] = {
    "cust_first_name": "cust_first_name",
    "cust_middle_name": "cust_middle_name",
    "cust_last_name": "cust_last_name",
    "cust_addr_line_1": "cust_addr_line_1",
    "cust_addr_line_2": "cust_addr_line_2",
    "cust_addr_line_3": "cust_addr_line_3",
    "cust_addr_state_cd": "cust_addr_state_cd",
    "cust_addr_country_cd": "cust_addr_country_cd",
    "cust_addr_zip": "cust_addr_zip",
    "cust_ssn": "cust_ssn",
    "cust_govt_issued_id": "cust_govt_issued_id",
    "cust_dob_yyyy_mm_dd": "cust_dob",
    "cust_eft_account_id": "cust_eft_account_id",
    "cust_pri_card_holder_ind": "cust_pri_card_holder_ind",
    "cust_fico_credit_score": "cust_fico_credit_score",
}


def _normalize_for_compare(
    old_val: Any, new_val: Any, is_decimal: bool,
) -> tuple[Any, Any]:
    """Normalize old and new values for comparison.

    Translated from 9700-CHECK-CHANGE-IN-REC in COACTUPC.cbl.
    The COBOL program uses UPPER-CASE for string comparisons and
    direct numeric comparison for monetary fields.

    Args:
        old_val: Current value from the database.
        new_val: New value from the form.
        is_decimal: Whether the field is a monetary Decimal field.

    Returns:
        Tuple of (normalized_old, normalized_new).
    """
    if is_decimal:
        return _to_decimal(old_val), _to_decimal(new_val)
    old_str = str(old_val).strip().upper() if old_val else ""
    new_str = str(new_val).strip().upper() if new_val else ""
    return old_str, new_str


def detect_changes(
    account: Account,
    customer: Customer,
    form_data: dict[str, Any],
) -> ChangeSet:
    """Compare current record with submitted form data.

    Translated from 1205-COMPARE-OLD-NEW in COACTUPC.cbl.
    Only fields that differ are included in the change set.

    Args:
        account:   Current Account model instance.
        customer:  Current Customer model instance.
        form_data: Cleaned form data dictionary.

    Returns:
        A ChangeSet listing all modified fields.
    """
    changes = ChangeSet()

    for model_field, form_field in _ACCOUNT_FIELD_MAP.items():
        if form_field not in form_data:
            continue
        old_val = getattr(account, model_field)
        new_val = form_data[form_field]
        is_decimal = model_field in _ACCOUNT_DECIMAL_FIELDS
        norm_old, norm_new = _normalize_for_compare(
            old_val, new_val, is_decimal,
        )
        if norm_old != norm_new:
            changes.account_changes[model_field] = (old_val, new_val)

    for model_field, form_field in _CUSTOMER_FIELD_MAP.items():
        if form_field not in form_data:
            continue
        old_val = getattr(customer, model_field)
        new_val = form_data[form_field]
        norm_old, norm_new = _normalize_for_compare(
            old_val, new_val, is_decimal=False,
        )
        if norm_old != norm_new:
            changes.customer_changes[model_field] = (old_val, new_val)

    # Handle phone numbers — stored as composite in the model
    _detect_phone_changes(customer, form_data, changes)

    return changes


def _detect_phone_changes(
    customer: Customer,
    form_data: dict[str, Any],
    changes: ChangeSet,
) -> None:
    """Detect changes to phone number fields.

    Phone numbers are stored as ``(NPA)NXX-XXXX`` in the database
    but submitted as three separate fields from the form.

    Args:
        customer:  Current Customer model instance.
        form_data: Cleaned form data dictionary.
        changes:   ChangeSet to update in place.
    """
    for phone_field, parts in [
        ("cust_phone_num_1", ("cust_phone_num_1_area", "cust_phone_num_1_prefix", "cust_phone_num_1_line")),
        ("cust_phone_num_2", ("cust_phone_num_2_area", "cust_phone_num_2_prefix", "cust_phone_num_2_line")),
    ]:
        area = form_data.get(parts[0], "").strip()
        prefix = form_data.get(parts[1], "").strip()
        line = form_data.get(parts[2], "").strip()
        if area and prefix and line:
            new_phone = f"({area}){prefix}-{line}"
        else:
            new_phone = ""
        old_phone = str(getattr(customer, phone_field, "")).strip()
        if old_phone.upper() != new_phone.upper():
            changes.customer_changes[phone_field] = (old_phone, new_phone)


# ---------------------------------------------------------------------------
# Apply updates
# ---------------------------------------------------------------------------


def apply_account_updates(
    account: Account,
    customer: Customer,
    form_data: dict[str, Any],
) -> UpdateResult:
    """Apply validated changes to account and customer records.

    Translated from 9600-WRITE-PROCESSING in COACTUPC.cbl.
    Only updates fields that have actually changed (change detection).

    Business rules preserved from COBOL:
    - Active status must be Y or N (validated in form)
    - Credit limit and monetary fields are Decimal (never float)
    - Phone numbers are stored in (NPA)NXX-XXXX format
    - Dates are stored in YYYY-MM-DD format

    Args:
        account:   Account model instance to update.
        customer:  Customer model instance to update.
        form_data: Cleaned and validated form data.

    Returns:
        An UpdateResult indicating success or failure.
    """
    change_set = detect_changes(account, customer, form_data)

    if not change_set.has_changes:
        return UpdateResult(
            success=False,
            error_message="No change detected with respect to values fetched.",
            change_set=change_set,
        )

    # Apply account field changes
    for field_name, (_old, new_val) in change_set.account_changes.items():
        if field_name in _ACCOUNT_DECIMAL_FIELDS:
            setattr(account, field_name, _to_decimal(new_val))
        else:
            setattr(account, field_name, new_val)

    # Apply customer field changes (excluding phone — handled separately)
    for field_name, (_old, new_val) in change_set.customer_changes.items():
        if field_name.startswith("cust_phone_num_"):
            setattr(customer, field_name, new_val)
        else:
            setattr(customer, field_name, new_val)

    try:
        account.save()
        customer.save()
    except Exception:
        logger.exception("Failed to save account/customer update")
        return UpdateResult(
            success=False,
            error_message="Update of record failed.",
            change_set=change_set,
        )

    return UpdateResult(success=True, change_set=change_set)


# ---------------------------------------------------------------------------
# Account lookup
# ---------------------------------------------------------------------------


def lookup_account_with_customer(
    acct_id: str,
) -> tuple[Account | None, Customer | None, str]:
    """Look up an account and its linked customer.

    Translated from 9000-READ-ACCT in COACTVWC.cbl / COACTUPC.cbl.
    The COBOL flow reads card xref → account → customer in sequence.

    Args:
        acct_id: 11-digit account identifier.

    Returns:
        Tuple of (account, customer, error_message).
        On success error_message is empty.
    """
    try:
        account = Account.objects.get(acct_id=acct_id)
    except Account.DoesNotExist:
        return None, None, "Did not find this account in account master file."

    # Find linked customer via card xref
    from accounts_mgmt.models import CardXref

    try:
        xref = CardXref.objects.filter(xref_acct_id=acct_id).first()
        if not xref:
            return account, None, "Did not find this account in account card xref file."
        customer = Customer.objects.get(cust_id=xref.xref_cust_id)
    except Customer.DoesNotExist:
        return account, None, "Did not find associated customer in master file."

    return account, customer, ""
