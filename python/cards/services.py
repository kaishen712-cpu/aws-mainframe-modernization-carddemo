"""
Business logic services for Credit Card Management.

Translated from COBOL programs:
- COCRDLIC.cbl — Card list/browse (STARTBR/READNEXT pattern)
- COCRDSLC.cbl — Card detail view
- COCRDUPC.cbl — Card update

Follows SRP: views handle HTTP, services handle business logic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.db.models import QuerySet

if TYPE_CHECKING:
    from python.cards.models import Card

logger = logging.getLogger(__name__)


@dataclass
class CardUpdateResult:
    """Outcome of a card update operation."""

    success: bool = False
    message: str = ""


def get_card_list(
    acct_id: str = "",
    card_num_filter: str = "",
    is_admin: bool = False,
) -> QuerySet[Card]:
    """Return filtered card queryset.

    Translated from COCRDLIC.cbl — 0000-MAIN / 9000-READ-DATA.

    Business rules:
    - Admin users see all cards if no filter provided.
    - Non-admin users only see cards for their account.
    - Optional filters by account ID and card number prefix.

    Args:
        acct_id: Account ID filter (required for non-admin).
        card_num_filter: Card number prefix filter.
        is_admin: Whether the user has admin privileges.

    Returns:
        Filtered queryset of Card objects.
    """
    from python.cards.models import Card

    queryset = Card.objects.all()

    if acct_id:
        queryset = queryset.filter(card_acct_id=acct_id)
    elif not is_admin:
        return Card.objects.none()

    if card_num_filter:
        queryset = queryset.filter(
            card_num__startswith=card_num_filter
        )

    return queryset.order_by("card_num")


def get_card_detail(
    acct_id: str,
    card_num: str,
) -> Card | None:
    """Retrieve a single card by account and card number.

    Translated from COCRDSLC.cbl — 9000-READ-DATA.

    Business rules:
    - Both account ID and card number must match.
    - Returns None if not found (NOTFND condition).

    Args:
        acct_id: The 11-digit account ID.
        card_num: The 16-digit card number.

    Returns:
        Card instance or None.
    """
    from python.cards.models import Card

    try:
        return Card.objects.get(
            card_acct_id=acct_id,
            card_num=card_num,
        )
    except Card.DoesNotExist:
        return None


def validate_card_update(
    card_name: str,
    card_status: str,
    expiry_month: str,
    expiry_year: str,
) -> CardUpdateResult:
    """Validate card update fields.

    Translated from COCRDUPC.cbl — 2000-PROCESS-INPUTS.

    Business rules:
    - Card name must be non-empty and contain only letters/spaces.
    - Card active status must be Y or N.
    - Expiry month must be 1-12.
    - Expiry year must be 1950-2099.

    Args:
        card_name: Embossed name on the card.
        card_status: Active status (Y/N).
        expiry_month: Expiration month (01-12).
        expiry_year: Expiration year (YYYY).

    Returns:
        CardUpdateResult with validation outcome.
    """
    if not card_name.strip():
        return CardUpdateResult(
            success=False,
            message="Card name not provided",
        )

    # COBOL: INSPECT CARD-NAME-CHECK REPLACING ALL alpha BY spaces
    name_check = card_name.strip()
    if not all(c.isalpha() or c.isspace() for c in name_check):
        return CardUpdateResult(
            success=False,
            message="Card name can only contain alphabets and spaces",
        )

    if card_status.upper() not in ("Y", "N"):
        return CardUpdateResult(
            success=False,
            message="Card Active Status must be Y or N",
        )

    try:
        month_val = int(expiry_month)
        if not (1 <= month_val <= 12):
            raise ValueError
    except (ValueError, TypeError):
        return CardUpdateResult(
            success=False,
            message="Card expiry month must be between 1 and 12",
        )

    try:
        year_val = int(expiry_year)
        # COBOL: 88 VALID-YEAR VALUES 1950 THRU 2099
        if not (1950 <= year_val <= 2099):
            raise ValueError
    except (ValueError, TypeError):
        return CardUpdateResult(
            success=False,
            message="Invalid card expiry year",
        )

    return CardUpdateResult(success=True, message="Validation passed")


def update_card(
    card_num: str,
    card_name: str,
    card_status: str,
    expiry_month: str,
    expiry_year: str,
    expiry_day: str = "01",
) -> CardUpdateResult:
    """Update a card record after validation.

    Translated from COCRDUPC.cbl — 9100-UPDATE-DATA.

    Business rules:
    - Validates all fields before updating.
    - Detects if no changes were made (NO-CHANGES-DETECTED).
    - Constructs expiration date as YYYY-MM-DD.

    Args:
        card_num: The card number to update.
        card_name: New embossed name.
        card_status: New active status (Y/N).
        expiry_month: New expiration month.
        expiry_year: New expiration year.
        expiry_day: Expiration day (defaults to 01).

    Returns:
        CardUpdateResult indicating success or failure.
    """
    from python.cards.models import Card

    validation = validate_card_update(
        card_name, card_status, expiry_month, expiry_year,
    )
    if not validation.success:
        return validation

    try:
        card = Card.objects.get(card_num=card_num)
    except Card.DoesNotExist:
        return CardUpdateResult(
            success=False,
            message="Did not find cards for this search condition",
        )

    new_exp_date = (
        f"{expiry_year.zfill(4)}-{expiry_month.zfill(2)}"
        f"-{expiry_day.zfill(2)}"
    )

    # COBOL: Check if any changes detected
    if (
        card.card_embossed_name == card_name.strip()
        and card.card_active_status == card_status.upper()
        and card.card_expiration_date == new_exp_date
    ):
        return CardUpdateResult(
            success=False,
            message=(
                "No change detected with respect to values fetched."
            ),
        )

    card.card_embossed_name = card_name.strip()
    card.card_active_status = card_status.upper()
    card.card_expiration_date = new_exp_date
    card.save()

    # CPS 234: Do not log card numbers in plain text
    logger.info("Card record updated successfully")

    return CardUpdateResult(
        success=True,
        message="Changes committed to database",
    )
