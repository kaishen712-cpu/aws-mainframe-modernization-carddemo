"""
COCRDUPC - Credit Card Update Program (Python Translation)

Translated from the COBOL program COCRDUPC.CBL (1,560 lines) in the AWS
CardDemo mainframe modernization project.  This module implements the
business logic for updating credit card details with a confirmation
workflow.

Original: CICS COBOL program using BMS maps and VSAM files.
This translation separates the pure business logic (validation, change
detection, update operations) from the CICS presentation layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from coactvwc import (
    CardRecord,
    CardXrefRepository,
)
from cocrdlic import CardRepository, InMemoryCardRepository


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROGRAM_NAME = "COCRDUPC"
TRANSACTION_ID = "CCUP"

TITLE_01 = "      AWS Mainframe Modernization       "
TITLE_02 = "              CardDemo                  "

VALID_CARD_STATUSES = {"Y", "N"}


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
class CardUpdateInput:
    """
    All user-supplied fields from the Credit Card Update screen.

    Corresponds to the CCRDUPAI screen input fields plus the old-values
    snapshot stored in the COMMAREA (WS-THIS-PROGCOMMAREA).
    """
    acct_id: str = ""
    card_num: str = ""
    embossed_name: str = ""
    expiry_month: str = ""
    expiry_year: str = ""
    active_status: str = ""


@dataclass
class CardUpdateResult:
    """Outcome of an update-card operation."""
    success: bool = False
    message: str = ""
    info_message: str = ""
    changes_detected: bool = False
    needs_confirmation: bool = False


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_account_id(acct_id: str) -> ValidationResult:
    """
    Validate the account ID filter for the card update screen.

    Business rules (from 1210-EDIT-ACCOUNT):
    1. Must be supplied.
    2. Must be numeric.
    3. Must not be all zeros.
    """
    raw = acct_id.strip()
    if raw == "" or raw == "*":
        return ValidationResult(
            is_valid=False,
            error_message="Account ID not provided",
            error_field="acct_id",
        )

    if not raw.isdigit():
        return ValidationResult(
            is_valid=False,
            error_message=(
                "Account filter, if supplied must be a 11 digit number"
            ),
            error_field="acct_id",
        )

    if int(raw) == 0:
        return ValidationResult(
            is_valid=False,
            error_message=(
                "Account filter, if supplied must be a 11 digit number"
            ),
            error_field="acct_id",
        )

    return ValidationResult(is_valid=True)


def validate_card_number(card_num: str) -> ValidationResult:
    """
    Validate the card number filter.

    Business rules (from 1220-EDIT-CARD):
    1. Must be supplied.
    2. Must be numeric.
    3. Must not be all zeros.
    """
    raw = card_num.strip()
    if raw == "" or raw == "*":
        return ValidationResult(
            is_valid=False,
            error_message="Card number not provided",
            error_field="card_num",
        )

    if not raw.isdigit():
        return ValidationResult(
            is_valid=False,
            error_message=(
                "Card ID filter, if supplied must be a 16 digit number"
            ),
            error_field="card_num",
        )

    if int(raw) == 0:
        return ValidationResult(
            is_valid=False,
            error_message=(
                "Card ID filter, if supplied must be a 16 digit number"
            ),
            error_field="card_num",
        )

    return ValidationResult(is_valid=True)


def validate_embossed_name(name: str) -> ValidationResult:
    """
    Validate the card embossed name field.

    Business rules (from 1230-EDIT-NAME):
    - Must be supplied (not blank).
    """
    raw = name.strip()
    if raw == "":
        return ValidationResult(
            is_valid=False,
            error_message="Card holder name is required",
            error_field="embossed_name",
        )

    return ValidationResult(is_valid=True)


def validate_card_status(status: str) -> ValidationResult:
    """
    Validate the card active status field.

    Business rules (from 1240-EDIT-CARDSTATUS):
    - Must be 'Y' or 'N'.
    """
    s = status.strip().upper()
    if s not in VALID_CARD_STATUSES:
        return ValidationResult(
            is_valid=False,
            error_message="Card status must be Y or N",
            error_field="active_status",
        )
    return ValidationResult(is_valid=True)


def validate_expiry_month(month: str) -> ValidationResult:
    """
    Validate the card expiry month.

    Business rules (from 1250-EDIT-EXPIRY-MON):
    - Must be numeric.
    - Must be 1-12.
    """
    raw = month.strip()
    if raw == "":
        return ValidationResult(
            is_valid=False,
            error_message="Expiry month is required",
            error_field="expiry_month",
        )

    if not raw.isdigit():
        return ValidationResult(
            is_valid=False,
            error_message="Expiry month must be numeric (01-12)",
            error_field="expiry_month",
        )

    val = int(raw)
    if val < 1 or val > 12:
        return ValidationResult(
            is_valid=False,
            error_message="Card expiry month must be between 1 and 12",
            error_field="expiry_month",
        )

    return ValidationResult(is_valid=True)


def validate_expiry_year(year: str) -> ValidationResult:
    """
    Validate the card expiry year.

    Business rules (from 1260-EDIT-EXPIRY-YEAR):
    - Must be numeric.
    - Must be a 4-digit year.
    """
    raw = year.strip()
    if raw == "":
        return ValidationResult(
            is_valid=False,
            error_message="Expiry year is required",
            error_field="expiry_year",
        )

    if not raw.isdigit():
        return ValidationResult(
            is_valid=False,
            error_message="Expiry year must be numeric",
            error_field="expiry_year",
        )

    if len(raw) != 4:
        return ValidationResult(
            is_valid=False,
            error_message="Expiry year must be a 4-digit year",
            error_field="expiry_year",
        )

    val = int(raw)
    if val < 1000:
        return ValidationResult(
            is_valid=False,
            error_message="Invalid card expiry year",
            error_field="expiry_year",
        )

    return ValidationResult(is_valid=True)


def validate_card_update_fields(update_input: CardUpdateInput) -> ValidationResult:
    """
    Validate all updatable card fields.

    Runs field-level validations in sequence, returning the first error.
    """
    v = validate_embossed_name(update_input.embossed_name)
    if not v.is_valid:
        return v

    v = validate_card_status(update_input.active_status)
    if not v.is_valid:
        return v

    v = validate_expiry_month(update_input.expiry_month)
    if not v.is_valid:
        return v

    v = validate_expiry_year(update_input.expiry_year)
    if not v.is_valid:
        return v

    return ValidationResult(is_valid=True)


# ---------------------------------------------------------------------------
# Change detection
# ---------------------------------------------------------------------------

def detect_card_changes(
    old_card: CardRecord,
    update_input: CardUpdateInput,
) -> dict[str, tuple[str, str]]:
    """
    Compare current card values with submitted input.

    Returns a dict of field_name -> (old_value, new_value) for each
    field that has changed.
    """
    changes: dict[str, tuple[str, str]] = {}

    # Embossed name (case-insensitive comparison per COBOL UPPER-CASE)
    old_name = old_card.embossed_name.strip().upper()
    new_name = update_input.embossed_name.strip().upper()
    if old_name != new_name and new_name != "":
        changes["embossed_name"] = (old_card.embossed_name.strip(), update_input.embossed_name.strip())

    # Active status
    old_status = old_card.active_status.strip().upper()
    new_status = update_input.active_status.strip().upper()
    if old_status != new_status and new_status != "":
        changes["active_status"] = (old_card.active_status, new_status)

    # Expiry month
    old_exp = old_card.expiration_date.strip()
    # Parse old expiry month/year from the date field (format varies)
    old_month = ""
    old_year = ""
    if len(old_exp) >= 7:
        # Try YYYY-MM-DD format
        parts = old_exp.split("-")
        if len(parts) >= 2:
            old_year = parts[0]
            old_month = parts[1]

    new_month = update_input.expiry_month.strip().zfill(2)
    new_year = update_input.expiry_year.strip()

    if old_month != new_month and update_input.expiry_month.strip() != "":
        changes["expiry_month"] = (old_month, new_month)

    if old_year != new_year and update_input.expiry_year.strip() != "":
        changes["expiry_year"] = (old_year, new_year)

    return changes


# ---------------------------------------------------------------------------
# Core update logic
# ---------------------------------------------------------------------------

def lookup_card_for_update(
    acct_id_input: str,
    card_num_input: str,
    card_repo: CardRepository,
    xref_repo: CardXrefRepository,
) -> CardUpdateResult:
    """
    Validate search keys and fetch card data for editing.

    Corresponds to the initial fetch flow when the user enters search
    criteria.
    """
    v = validate_account_id(acct_id_input)
    if not v.is_valid:
        return CardUpdateResult(success=False, message=v.error_message)

    v = validate_card_number(card_num_input)
    if not v.is_valid:
        return CardUpdateResult(success=False, message=v.error_message)

    normalised_card = card_num_input.strip().zfill(16)
    card = card_repo.get_card(normalised_card)
    if card is None:
        return CardUpdateResult(
            success=False,
            message="Did not find acct+card combination in card file",
        )

    return CardUpdateResult(
        success=True,
        message="Card details ready for update",
        info_message="Card details ready for update",
    )


def update_card(
    card_num: str,
    update_input: CardUpdateInput,
    old_card: CardRecord,
    card_repo: CardRepository,
    confirmed: bool = False,
) -> CardUpdateResult:
    """
    Full card-update workflow: validate, detect changes, apply.

    Parameters
    ----------
    card_num : str
        The 16-digit card number.
    update_input : CardUpdateInput
        The user's submitted field values.
    old_card : CardRecord
        The original card record fetched before editing.
    card_repo : CardRepository
        Data access for card records (must support update).
    confirmed : bool
        Whether the user has confirmed the changes (PF5).

    Returns
    -------
    CardUpdateResult
        Indicates success, validation errors, or need for confirmation.
    """
    # Step 1: Validate all fields
    val = validate_card_update_fields(update_input)
    if not val.is_valid:
        return CardUpdateResult(
            success=False,
            message=val.error_message,
        )

    # Step 2: Detect changes
    changes = detect_card_changes(old_card, update_input)
    if not changes:
        return CardUpdateResult(
            success=False,
            message="No changes detected",
            changes_detected=False,
        )

    # Step 3: If not confirmed, prompt
    if not confirmed:
        return CardUpdateResult(
            success=False,
            message="",
            info_message="Changes validated. Press F5 to confirm update",
            changes_detected=True,
            needs_confirmation=True,
        )

    # Step 4: Apply the update
    normalised = card_num.strip().zfill(16)
    updated = _apply_card_changes(old_card, update_input)

    if isinstance(card_repo, InMemoryCardRepository):
        card_repo.cards[normalised] = updated
        return CardUpdateResult(
            success=True,
            message="",
            info_message="Changes committed to database",
            changes_detected=True,
        )

    return CardUpdateResult(
        success=False,
        message="Update of card record failed",
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _apply_card_changes(
    old_card: CardRecord,
    update_input: CardUpdateInput,
) -> CardRecord:
    """Build a new CardRecord with applied changes."""
    new_month = update_input.expiry_month.strip().zfill(2)
    new_year = update_input.expiry_year.strip()

    # Reconstruct expiration date
    if new_year and new_month:
        new_exp_date = f"{new_year}-{new_month}-01"
    else:
        new_exp_date = old_card.expiration_date

    return CardRecord(
        card_num=old_card.card_num,
        acct_id=old_card.acct_id,
        cvv_cd=old_card.cvv_cd,
        embossed_name=(
            update_input.embossed_name.strip()
            if update_input.embossed_name.strip()
            else old_card.embossed_name
        ),
        expiration_date=new_exp_date,
        active_status=(
            update_input.active_status.strip().upper()
            if update_input.active_status.strip()
            else old_card.active_status
        ),
    )


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def get_header_info() -> dict[str, str]:
    """Return screen header information for the Credit Card Update screen."""
    now = datetime.now()
    return {
        "title01": TITLE_01,
        "title02": TITLE_02,
        "program_name": PROGRAM_NAME,
        "transaction_id": TRANSACTION_ID,
        "current_date": now.strftime("%m/%d/%y"),
        "current_time": now.strftime("%H:%M:%S"),
    }
