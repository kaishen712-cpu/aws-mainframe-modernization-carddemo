"""Statement generation variant — batch management command.

Translated from CBSTM03B.CBL (~230 lines).

This is a simplified statement generation subroutine variant that
focuses on file-based processing. In the original COBOL, CBSTM03B
was called as a subroutine by CBSTM03A for specialized file handling.

In the Python translation, this command provides an alternative
statement format with different grouping and summary options.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandParser

from batch.models import Account, CardXref, Transaction

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Generate statements (variant) — translated from CBSTM03B.CBL."""

    help = "Generate account statements variant format (CBSTM03B.CBL)"

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command-line arguments."""
        parser.add_argument(
            "--output-dir",
            type=str,
            default="statements_v2",
            help="Output directory (default: statements_v2/)",
        )
        parser.add_argument(
            "--acct-id",
            type=str,
            default="",
            help="Generate for a specific account only",
        )

    def handle(self, *args: object, **options: object) -> None:
        """Execute statement generation variant.

        Translated from PROCEDURE DIVISION of CBSTM03B.CBL.
        """
        output_dir = Path(str(options.get("output_dir", "statements_v2") or "statements_v2"))
        acct_filter = str(options.get("acct_id", "") or "")

        output_dir.mkdir(parents=True, exist_ok=True)
        statements_generated = 0

        accounts = Account.objects.all().order_by("acct_id")
        if acct_filter:
            accounts = accounts.filter(acct_id=acct_filter)

        for account in accounts:
            self._generate_statement(output_dir, account)
            statements_generated += 1

        self.stdout.write(f"Statements (v2) generated: {statements_generated}")

    def _generate_statement(self, output_dir: Path, account: Account) -> None:
        """Generate a single account statement in summary format.

        Translated from the file processing logic in CBSTM03B.CBL.
        Groups transactions by type and provides subtotals.
        """
        # Get all cards for this account
        card_nums = list(
            CardXref.objects.filter(xref_acct_id=account.acct_id).values_list(
                "xref_card_num", flat=True
            )
        )

        # Get transactions grouped by type
        transactions = Transaction.objects.filter(tran_card_num__in=card_nums).order_by(
            "tran_type_cd", "tran_orig_ts"
        )

        # Group by type code
        grouped: dict[str, list[Transaction]] = {}
        for txn in transactions:
            grouped.setdefault(txn.tran_type_cd, []).append(txn)

        statement_date = datetime.now(tz=UTC).strftime("%Y-%m-%d")

        lines: list[str] = []
        lines.append(f"STATEMENT SUMMARY — Account {account.acct_id}")
        lines.append(f"Date: {statement_date}")
        lines.append("=" * 50)
        lines.append(f"Balance: {account.acct_curr_bal}")
        lines.append(f"Credit Limit: {account.acct_credit_limit}")
        lines.append("")

        for type_cd in sorted(grouped):
            type_txns = grouped[type_cd]
            subtotal = sum((txn.tran_amt for txn in type_txns), Decimal("0"))
            lines.append(f"Type {type_cd}: {len(type_txns)} transactions, subtotal: {subtotal}")
            for txn in type_txns:
                lines.append(
                    f"  {txn.tran_orig_ts[:10]}  {txn.tran_desc[:30]:<30}  {txn.tran_amt:>10}"
                )
            lines.append("")

        file_path = output_dir / f"stmt_v2_{account.acct_id}.txt"
        file_path.write_text("\n".join(lines) + "\n")
