"""
COCRDSLC - Credit Card View Program (Python Translation)

Translated from the COBOL program COCRDSLC.CBL (887 lines) in the AWS
CardDemo mainframe modernization project.  This module implements the
business logic for viewing credit card details in read-only mode.

Original: CICS COBOL program using BMS maps and VSAM files.
This translation separates the pure business logic (validation, data
lookup, result building) from the CICS presentation layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from coactvwc import (
    AccountRecord,
    AccountRepository,
    CardRecord,
    CardXrefRecord,
    CardXrefRepository,
    CustomerRecord,
    CustomerRepository,
)
from cocrdlic import CardRepository


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROGRAM_NAME = "COCRDSLC"
TRANSACTION_ID = "CCDL"

TITLE_01 = "      AWS Mainframe Modernization       "
TITLE_02 = "              CardDemo                  "


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
class CardViewResult:
    """Outcome of a view-card operation."""
    success: bool = False
    message: str = ""
    card: Optional[CardRecord] = None
    account: Optional[AccountRecord] = None
    customer: Optional[CustomerRecord] = None
    card_xref: Optional[CardXrefRecord] = None


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_account_id(acct_id: str) -> ValidationResult:
    """
    Validate the account ID filter.

    Business rules (from 2210-EDIT-ACCOUNT):
    1. Must be supplied (not blank).
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

    Business rules (from 2220-EDIT-CARD):
    1. Must be supplied (not blank).
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


# ---------------------------------------------------------------------------
# Core view-card logic
# ---------------------------------------------------------------------------

def view_card_details(
    acct_id_input: str,
    card_num_input: str,
    card_repo: CardRepository,
    acct_repo: AccountRepository,
    xref_repo: CardXrefRepository,
    cust_repo: CustomerRepository,
) -> CardViewResult:
    """
    Full card-view workflow: validate inputs, look up card, account, customer.

    This is the top-level entry point that mirrors the COBOL program's
    9000-READ-DATA paragraph chain.

    Parameters
    ----------
    acct_id_input : str
        Account ID from the user or from the calling program.
    card_num_input : str
        Card number from the user or from the calling program.
    card_repo : CardRepository
        Data access for card records.
    acct_repo : AccountRepository
        Data access for account records.
    xref_repo : CardXrefRepository
        Data access for card cross-reference records.
    cust_repo : CustomerRepository
        Data access for customer records.

    Returns
    -------
    CardViewResult
        Contains card, account, customer, and xref data on success,
        or an error message on failure.
    """
    # Validate card number (required)
    v_card = validate_card_number(card_num_input)
    if not v_card.is_valid:
        # If card not provided, check if account ID can find a card
        v_acct = validate_account_id(acct_id_input)
        if not v_acct.is_valid:
            return CardViewResult(
                success=False,
                message="Please provide account ID and/or card number",
            )
        # Try to find card via account xref
        normalised_acct = acct_id_input.strip().zfill(11)
        xref = xref_repo.lookup_by_account(normalised_acct)
        if xref is None:
            return CardViewResult(
                success=False,
                message="Did not find account in card xref file",
            )
        card_num_input = xref.card_num

    normalised_card = card_num_input.strip().zfill(16)

    # Step 1: Read card record (9100-GETCARD-BYACCTCARD)
    card = card_repo.get_card(normalised_card)
    if card is None:
        return CardViewResult(
            success=False,
            message="Did not find acct+card combination in card file",
        )

    # Step 2: Look up cross-reference for customer info
    xref = xref_repo.lookup_by_card(normalised_card)

    # Step 3: Read account master
    account = None
    if card.acct_id:
        account = acct_repo.get_account(card.acct_id)

    # Step 4: Read customer master
    customer = None
    if xref and xref.cust_id:
        customer = cust_repo.get_customer(xref.cust_id)

    return CardViewResult(
        success=True,
        message="Card details retrieved successfully",
        card=card,
        account=account,
        customer=customer,
        card_xref=xref,
    )


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def get_header_info() -> dict[str, str]:
    """Return screen header information for the Credit Card View screen."""
    now = datetime.now()
    return {
        "title01": TITLE_01,
        "title02": TITLE_02,
        "program_name": PROGRAM_NAME,
        "transaction_id": TRANSACTION_ID,
        "current_date": now.strftime("%m/%d/%y"),
        "current_time": now.strftime("%H:%M:%S"),
    }
