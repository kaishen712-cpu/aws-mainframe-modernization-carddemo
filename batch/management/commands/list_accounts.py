"""List account data — batch management command.

Translated from CBACT02C.cbl (179 lines) — reads and prints card data,
and CBACT03C.cbl (179 lines) — reads and prints cross-reference data.

Combined into a single command that lists accounts with optional
card and cross-reference information.

Original COBOL program flow:
1. Open data file (CARDFILE or XREFFILE)
2. Read records sequentially
3. Display each record
4. Close file
"""

from __future__ import annotations

import logging

from django.core.management.base import BaseCommand, CommandParser

from batch.models import Account, Card, CardXref

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """List accounts — translated from CBACT02C.cbl / CBACT03C.cbl."""

    help = "List accounts with optional card/xref info (CBACT02C/03C.cbl)"

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command-line arguments."""
        parser.add_argument(
            "--show-cards",
            action="store_true",
            help="Include card information",
        )
        parser.add_argument(
            "--show-xref",
            action="store_true",
            help="Include cross-reference information",
        )
        parser.add_argument(
            "--acct-id",
            type=str,
            default="",
            help="Filter by account ID",
        )

    def handle(self, *args: object, **options: object) -> None:
        """Execute the account listing.

        Translated from PROCEDURE DIVISION of CBACT02C.cbl (card listing)
        and CBACT03C.cbl (cross-reference listing).
        """
        show_cards = bool(options.get("show_cards", False))
        show_xref = bool(options.get("show_xref", False))
        acct_filter = str(options.get("acct_id", "") or "")

        accounts = Account.objects.all().order_by("acct_id")
        if acct_filter:
            accounts = accounts.filter(acct_id=acct_filter)

        # Translated from paragraph 1100-DISPLAY-ACCT-RECORD in CBACT01C.cbl
        for account in accounts:
            self.stdout.write(f"ACCT-ID: {account.acct_id}")
            self.stdout.write(f"  Status: {account.acct_active_status}")
            self.stdout.write(f"  Balance: {account.acct_curr_bal}")
            self.stdout.write(f"  Credit Limit: {account.acct_credit_limit}")
            self.stdout.write(f"  Group ID: {account.acct_group_id}")

            if show_cards:
                cards = Card.objects.filter(
                    card_acct_id=account.acct_id
                )
                for card in cards:
                    self.stdout.write(
                        f"  Card: ****{card.card_num[-4:]} "
                        f"Status: {card.card_active_status}"
                    )

            if show_xref:
                xrefs = CardXref.objects.filter(
                    xref_acct_id=account.acct_id
                )
                for xref in xrefs:
                    self.stdout.write(
                        f"  Xref: ****{xref.xref_card_num[-4:]} "
                        f"Cust: {xref.xref_cust_id}"
                    )

            self.stdout.write("-" * 50)

        self.stdout.write(f"Total accounts: {accounts.count()}")
