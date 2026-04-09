"""
COCRDLIC - Credit Card List Program (Python Translation)

Translated from the COBOL program COCRDLIC.CBL (1,459 lines) in the AWS
CardDemo mainframe modernization project.  This module implements the
business logic for browsing and searching credit cards with pagination.

Original: CICS COBOL program using BMS maps and VSAM files.
This translation separates the pure business logic (search, pagination,
selection) from the CICS presentation layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from coactvwc import (
    CardRecord,
    CardXrefRepository,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROGRAM_NAME = "COCRDLIC"
TRANSACTION_ID = "CCLI"

TITLE_01 = "      AWS Mainframe Modernization       "
TITLE_02 = "              CardDemo                  "

PAGE_SIZE = 7  # Number of card rows displayed per page on the BMS screen


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
class CardListItem:
    """One row in the card list display."""
    card_num: str = ""
    acct_id: str = ""
    card_status: str = ""
    expiration_date: str = ""
    embossed_name: str = ""


@dataclass
class CardListResult:
    """Outcome of a card-list search operation."""
    success: bool = False
    message: str = ""
    cards: list[CardListItem] = field(default_factory=list)
    total_cards: int = 0
    page_num: int = 1
    has_more: bool = False
    has_previous: bool = False


@dataclass
class CardSelectionResult:
    """Outcome of selecting a card from the list."""
    success: bool = False
    message: str = ""
    selected_card_num: str = ""
    selected_acct_id: str = ""
    target_program: str = ""  # 'COCRDSLC' for view, 'COCRDUPC' for update


# ---------------------------------------------------------------------------
# Repository interfaces
# ---------------------------------------------------------------------------

class CardRepository:
    """
    Abstract interface for card data access.

    In the original COBOL program these are CICS STARTBR / READNEXT /
    READPREV / ENDBR operations against VSAM KSDS files.
    """

    def get_card(self, card_num: str) -> Optional[CardRecord]:
        """Read a single card record by card number."""
        raise NotImplementedError

    def list_cards_by_account(self, acct_id: str) -> list[CardRecord]:
        """Return all cards associated with an account (via CARDAIX)."""
        raise NotImplementedError

    def list_cards_from(
        self, start_card: str, limit: int,
    ) -> list[CardRecord]:
        """
        Browse cards starting from *start_card* (STARTBR + READNEXT).

        Returns up to *limit* records in ascending key order.
        """
        raise NotImplementedError

    def list_all_cards(self) -> list[CardRecord]:
        """Return all card records (for small test data sets)."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# In-memory repository for testing
# ---------------------------------------------------------------------------

class InMemoryCardRepository(CardRepository):
    """Simple in-memory implementation backed by a Python dict."""

    def __init__(self) -> None:
        self.cards: dict[str, CardRecord] = {}

    def add_card(self, record: CardRecord) -> None:
        """Register a card record."""
        self.cards[record.card_num] = record

    def get_card(self, card_num: str) -> Optional[CardRecord]:
        return self.cards.get(card_num)

    def list_cards_by_account(self, acct_id: str) -> list[CardRecord]:
        return sorted(
            [c for c in self.cards.values() if c.acct_id == acct_id],
            key=lambda c: c.card_num,
        )

    def list_cards_from(
        self, start_card: str, limit: int,
    ) -> list[CardRecord]:
        sorted_cards = sorted(self.cards.values(), key=lambda c: c.card_num)
        result: list[CardRecord] = []
        for card in sorted_cards:
            if card.card_num >= start_card:
                result.append(card)
                if len(result) >= limit:
                    break
        return result

    def list_all_cards(self) -> list[CardRecord]:
        return sorted(self.cards.values(), key=lambda c: c.card_num)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_account_filter(acct_id: str) -> ValidationResult:
    """
    Validate account ID search filter.

    Business rules (from 2210-EDIT-ACCOUNT):
    1. If supplied, must be numeric.
    2. If supplied, must not be all zeros.
    """
    raw = acct_id.strip()
    if raw == "" or raw == "*":
        return ValidationResult(is_valid=True)  # blank = no filter

    if not raw.isdigit():
        return ValidationResult(
            is_valid=False,
            error_message=(
                "Account filter, if supplied, must be a 11 digit number"
            ),
            error_field="acct_id",
        )

    if int(raw) == 0:
        return ValidationResult(
            is_valid=False,
            error_message=(
                "Account filter, if supplied, must be a 11 digit number"
            ),
            error_field="acct_id",
        )

    return ValidationResult(is_valid=True)


def validate_card_filter(card_num: str) -> ValidationResult:
    """
    Validate card number search filter.

    Business rules (from 2220-EDIT-CARD):
    1. If supplied, must be numeric.
    2. If supplied, must not be all zeros.
    """
    raw = card_num.strip()
    if raw == "" or raw == "*":
        return ValidationResult(is_valid=True)  # blank = no filter

    if not raw.isdigit():
        return ValidationResult(
            is_valid=False,
            error_message=(
                "Card filter, if supplied, must be a 16 digit number"
            ),
            error_field="card_num",
        )

    if int(raw) == 0:
        return ValidationResult(
            is_valid=False,
            error_message=(
                "Card filter, if supplied, must be a 16 digit number"
            ),
            error_field="card_num",
        )

    return ValidationResult(is_valid=True)


# ---------------------------------------------------------------------------
# Core search / pagination logic
# ---------------------------------------------------------------------------

def search_cards(
    acct_id_filter: str,
    card_num_filter: str,
    card_repo: CardRepository,
    xref_repo: CardXrefRepository,
    page: int = 1,
) -> CardListResult:
    """
    Search and paginate credit card records.

    Parameters
    ----------
    acct_id_filter : str
        Optional account ID filter.
    card_num_filter : str
        Optional card number filter.
    card_repo : CardRepository
        Data access for card records.
    xref_repo : CardXrefRepository
        Data access for cross-reference records.
    page : int
        1-based page number.

    Returns
    -------
    CardListResult
        Paginated results with navigation flags.
    """
    # Validate filters
    v = validate_account_filter(acct_id_filter)
    if not v.is_valid:
        return CardListResult(success=False, message=v.error_message)

    v = validate_card_filter(card_num_filter)
    if not v.is_valid:
        return CardListResult(success=False, message=v.error_message)

    acct_raw = acct_id_filter.strip()
    card_raw = card_num_filter.strip()

    # Both blank - show all cards
    if (acct_raw == "" or acct_raw == "*") and (card_raw == "" or card_raw == "*"):
        all_cards = card_repo.list_all_cards()
    elif acct_raw and acct_raw != "*":
        normalised = acct_raw.zfill(11)
        all_cards = card_repo.list_cards_by_account(normalised)
    elif card_raw and card_raw != "*":
        normalised_card = card_raw.zfill(16)
        card = card_repo.get_card(normalised_card)
        all_cards = [card] if card else []
    else:
        all_cards = card_repo.list_all_cards()

    if not all_cards:
        return CardListResult(
            success=False,
            message="No cards found matching the criteria",
            total_cards=0,
        )

    # Paginate
    total = len(all_cards)
    start_idx = (page - 1) * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    page_cards = all_cards[start_idx:end_idx]

    items = [
        CardListItem(
            card_num=c.card_num,
            acct_id=c.acct_id,
            card_status=c.active_status,
            expiration_date=c.expiration_date,
            embossed_name=c.embossed_name,
        )
        for c in page_cards
    ]

    return CardListResult(
        success=True,
        message=f"Showing page {page}",
        cards=items,
        total_cards=total,
        page_num=page,
        has_more=end_idx < total,
        has_previous=page > 1,
    )


def select_card(
    card_num: str,
    action: str,
    card_repo: CardRepository,
) -> CardSelectionResult:
    """
    Handle user selecting a card from the list for view or update.

    Parameters
    ----------
    card_num : str
        The card number the user selected.
    action : str
        'view' for COCRDSLC (credit card view) or 'update' for COCRDUPC.
    card_repo : CardRepository
        Data access for card records.

    Returns
    -------
    CardSelectionResult
        Contains the target program name for XCTL.
    """
    card = card_repo.get_card(card_num)
    if card is None:
        return CardSelectionResult(
            success=False,
            message=f"Card {card_num} not found",
        )

    target = "COCRDSLC" if action == "view" else "COCRDUPC"

    return CardSelectionResult(
        success=True,
        selected_card_num=card.card_num,
        selected_acct_id=card.acct_id,
        target_program=target,
    )


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def get_header_info() -> dict[str, str]:
    """Return screen header information for the Credit Card List screen."""
    now = datetime.now()
    return {
        "title01": TITLE_01,
        "title02": TITLE_02,
        "program_name": PROGRAM_NAME,
        "transaction_id": TRANSACTION_ID,
        "current_date": now.strftime("%m/%d/%y"),
        "current_time": now.strftime("%H:%M:%S"),
    }
