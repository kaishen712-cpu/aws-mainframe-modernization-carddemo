"""Validate account data — batch management command.

Translated from account validation logic in CBACT01C-03C.cbl.

This command validates account data integrity by checking:
- Account records have valid required fields
- Cross-references point to existing accounts
- Card records reference existing accounts
- Balance fields are consistent

This combines validation aspects from all three CBACT programs.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from django.core.management.base import BaseCommand

from batch.models import Account, Card, CardXref

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Validate account data — translated from CBACT01C-03C.cbl."""

    help = "Validate account data integrity (CBACT01C-03C.cbl)"

    def handle(self, *args: object, **options: object) -> None:
        """Execute account validation checks.

        Validates data integrity across Account, Card, and CardXref tables.
        """
        errors: list[str] = []
        warnings: list[str] = []

        self._validate_accounts(errors, warnings)
        self._validate_xrefs(errors, warnings)
        self._validate_cards(errors, warnings)

        for warning in warnings:
            self.stdout.write(f"WARNING: {warning}")
        for error in errors:
            self.stderr.write(f"ERROR: {error}")

        self.stdout.write(f"Validation complete: {len(errors)} errors, {len(warnings)} warnings")

    def _validate_accounts(self, errors: list[str], warnings: list[str]) -> None:
        """Validate all account records."""
        for account in Account.objects.all():
            # Check required fields
            if not account.acct_id.strip():
                errors.append(f"Account {account.pk}: empty acct_id")

            if not account.acct_active_status.strip():
                warnings.append(f"Account {account.acct_id}: empty active status")

            # HUMAN REVIEW: credit limit threshold validation
            # These are hardcoded business rules that should be reviewed
            if account.acct_credit_limit < Decimal("0"):
                errors.append(f"Account {account.acct_id}: negative credit limit")

            # Balance sanity check
            if account.acct_curr_bal > account.acct_credit_limit * 2:
                warnings.append(f"Account {account.acct_id}: balance exceeds 2x credit limit")

    def _validate_xrefs(self, errors: list[str], warnings: list[str]) -> None:
        """Validate cross-reference records point to existing accounts."""
        for xref in CardXref.objects.all():
            if not Account.objects.filter(acct_id=xref.xref_acct_id).exists():
                errors.append(
                    f"Xref ****{xref.xref_card_num[-4:]}: account {xref.xref_acct_id} not found"
                )

    def _validate_cards(self, errors: list[str], warnings: list[str]) -> None:
        """Validate card records reference existing accounts."""
        for card in Card.objects.all():
            if not Account.objects.filter(acct_id=card.card_acct_id).exists():
                errors.append(
                    f"Card ****{card.card_num[-4:]}: account {card.card_acct_id} not found"
                )
