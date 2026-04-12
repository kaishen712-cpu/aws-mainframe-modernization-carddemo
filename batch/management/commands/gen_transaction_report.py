"""Transaction report generation — batch management command.

Translated from CBTRN01C.cbl (~495 lines).

Original COBOL program flow:
1. Open DALYTRAN, XREF, ACCOUNT files
2. Read daily transactions sequentially
3. For each: look up XREF (card -> account), then look up ACCOUNT
4. Print transaction details with account information
5. Close all files
"""

from __future__ import annotations

import logging
from pathlib import Path

from django.core.management.base import BaseCommand, CommandParser

from batch.models import Account, CardXref, DailyTransaction

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Generate transaction report — translated from CBTRN01C.cbl."""

    help = "Generate daily transaction report (CBTRN01C.cbl)"

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command-line arguments."""
        parser.add_argument(
            "--output",
            type=str,
            default="",
            help="Output file path (default: stdout)",
        )

    def handle(self, *args: object, **options: object) -> None:
        """Execute the transaction report generation.

        Translated from PROCEDURE DIVISION of CBTRN01C.cbl.
        """
        output_path = str(options.get("output", "") or "")
        lines: list[str] = []

        # Report header
        lines.append("=" * 80)
        lines.append("DAILY TRANSACTION REPORT")
        lines.append("=" * 80)
        lines.append("")

        daily_transactions = DailyTransaction.objects.all().order_by(
            "dalytran_id"
        )
        transaction_count = 0

        for daily_txn in daily_transactions:
            # Look up cross-reference
            # Translated from XREF lookup in CBTRN01C.cbl
            xref = CardXref.objects.filter(
                xref_card_num=daily_txn.dalytran_card_num
            ).first()

            acct_id = xref.xref_acct_id if xref else "UNKNOWN"

            # Look up account
            # Translated from ACCOUNT lookup in CBTRN01C.cbl
            account = None
            if xref:
                account = Account.objects.filter(
                    acct_id=xref.xref_acct_id
                ).first()

            # Format report line
            lines.append(f"Transaction ID  : {daily_txn.dalytran_id}")
            lines.append(f"Card Number     : ****{daily_txn.dalytran_card_num[-4:]}")
            lines.append(f"Account ID      : {acct_id}")
            type_cat = f"{daily_txn.dalytran_type_cd}/{daily_txn.dalytran_cat_cd}"
            lines.append(f"Type/Category   : {type_cat}")
            lines.append(f"Amount          : {daily_txn.dalytran_amt}")
            lines.append(f"Description     : {daily_txn.dalytran_desc}")
            lines.append(f"Merchant        : {daily_txn.dalytran_merchant_name}")
            lines.append(f"Timestamp       : {daily_txn.dalytran_orig_ts}")
            if account:
                lines.append(f"Account Balance : {account.acct_curr_bal}")
                lines.append(f"Credit Limit    : {account.acct_credit_limit}")
            lines.append("-" * 80)
            transaction_count += 1

        lines.append("")
        lines.append(f"Total Transactions: {transaction_count}")

        report_text = "\n".join(lines) + "\n"

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(report_text)
            self.stdout.write(f"Report written to {output_path}")
        else:
            self.stdout.write(report_text)
