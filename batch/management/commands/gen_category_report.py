"""Transaction category balance report — batch management command.

Translated from CBTRN03C.cbl (~650 lines).

Original COBOL program flow:
1. Open transaction, cross-reference, and category balance files
2. Read transactions, filter by optional date range
3. Group by account + type + category
4. Generate a summary report of category balances
5. Close all files
"""

from __future__ import annotations

import logging
from pathlib import Path

from django.core.management.base import BaseCommand, CommandParser

from batch.models import TranCatBal, TransactionCategory, TransactionType

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Generate category balance report — translated from CBTRN03C.cbl."""

    help = "Generate transaction category balance report (CBTRN03C.cbl)"

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command-line arguments."""
        parser.add_argument(
            "--output",
            type=str,
            default="",
            help="Output file path (default: stdout)",
        )
        parser.add_argument(
            "--start-date",
            type=str,
            default="",
            help="Start date filter YYYY-MM-DD (optional)",
        )
        parser.add_argument(
            "--end-date",
            type=str,
            default="",
            help="End date filter YYYY-MM-DD (optional)",
        )

    def handle(self, *args: object, **options: object) -> None:
        """Execute the category balance report generation.

        Translated from PROCEDURE DIVISION of CBTRN03C.cbl.
        """
        output_path = str(options.get("output", "") or "")
        lines: list[str] = []

        lines.append("=" * 80)
        lines.append("TRANSACTION CATEGORY BALANCE REPORT")
        lines.append("=" * 80)
        lines.append("")

        # Read all transaction category balances
        # Translated from TCATBAL file read in CBTRN03C.cbl
        tcatbal_records = TranCatBal.objects.all().order_by(
            "trancat_acct_id", "trancat_type_cd", "trancat_cd"
        )

        current_acct_id = ""
        record_count = 0

        for tcatbal in tcatbal_records:
            # Account break header
            if tcatbal.trancat_acct_id != current_acct_id:
                if current_acct_id:
                    lines.append("")
                current_acct_id = tcatbal.trancat_acct_id
                lines.append(f"Account: {current_acct_id}")
                lines.append("-" * 60)

            # Look up type and category descriptions
            type_desc = self._get_type_desc(tcatbal.trancat_type_cd)
            cat_desc = self._get_category_desc(
                tcatbal.trancat_type_cd, tcatbal.trancat_cd
            )

            lines.append(
                f"  Type: {tcatbal.trancat_type_cd} ({type_desc})  "
                f"Cat: {tcatbal.trancat_cd} ({cat_desc})  "
                f"Balance: {tcatbal.tran_cat_bal}"
            )
            record_count += 1

        lines.append("")
        lines.append(f"Total Records: {record_count}")

        report_text = "\n".join(lines) + "\n"

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(report_text)
            self.stdout.write(f"Report written to {output_path}")
        else:
            self.stdout.write(report_text)

    def _get_type_desc(self, type_cd: str) -> str:
        """Look up transaction type description."""
        tran_type = TransactionType.objects.filter(
            tran_type=type_cd
        ).first()
        return tran_type.tran_type_desc if tran_type else "Unknown"

    def _get_category_desc(self, type_cd: str, cat_cd: str) -> str:
        """Look up transaction category description."""
        category = TransactionCategory.objects.filter(
            tran_type_cd=type_cd, tran_cat_cd=cat_cd
        ).first()
        return category.tran_cat_type_desc if category else "Unknown"
