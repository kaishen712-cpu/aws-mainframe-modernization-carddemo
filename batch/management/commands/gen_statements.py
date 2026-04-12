"""Statement generation — batch management command.

Translated from CBSTM03A.CBL (924 lines).

Original COBOL program flow:
1. Open XREF, ACCOUNT, TRANSACTION, CUSTOMER files
2. Read cross-references sequentially (one per card/account)
3. For each account: gather transactions, customer info, account info
4. Generate statement in text format
5. Optionally generate HTML format
6. Close all files

This is a complex program with COMP/COMP-3 variables, 2D arrays,
ALTER/GO TO statements in the original COBOL. The Python translation
simplifies the control flow while preserving all business logic.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandParser

from batch.models import Account, CardXref, Customer, Transaction

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Generate account statements — translated from CBSTM03A.CBL."""

    help = "Generate account statements (CBSTM03A.CBL)"

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command-line arguments."""
        parser.add_argument(
            "--output-dir",
            type=str,
            default="statements",
            help="Output directory for statement files (default: statements/)",
        )
        parser.add_argument(
            "--format",
            type=str,
            choices=["text", "html", "both"],
            default="text",
            help="Output format (default: text)",
        )
        parser.add_argument(
            "--acct-id",
            type=str,
            default="",
            help="Generate statement for a specific account only",
        )

    def handle(self, *args: object, **options: object) -> None:
        """Execute statement generation.

        Translated from PROCEDURE DIVISION of CBSTM03A.CBL.
        """
        output_dir = Path(str(options.get("output_dir", "statements") or "statements"))
        output_format = str(options.get("format", "text") or "text")
        acct_filter = str(options.get("acct_id", "") or "")

        output_dir.mkdir(parents=True, exist_ok=True)

        statements_generated = 0

        # Get all unique accounts from cross-references
        xref_qs = CardXref.objects.all().order_by("xref_acct_id")
        if acct_filter:
            xref_qs = xref_qs.filter(xref_acct_id=acct_filter)

        processed_accounts: set[str] = set()

        for xref in xref_qs:
            if xref.xref_acct_id in processed_accounts:
                continue
            processed_accounts.add(xref.xref_acct_id)

            statement = self._build_statement(xref)
            if statement is None:
                continue

            if output_format in ("text", "both"):
                self._write_text_statement(output_dir, xref.xref_acct_id, statement)
            if output_format in ("html", "both"):
                self._write_html_statement(output_dir, xref.xref_acct_id, statement)
            statements_generated += 1

        self.stdout.write(f"Statements generated: {statements_generated}")

    def _build_statement(self, xref: CardXref) -> dict[str, object] | None:
        """Build statement data for a single account.

        Gathers account, customer, and transaction information.
        """
        account = Account.objects.filter(acct_id=xref.xref_acct_id).first()
        if account is None:
            return None

        customer = Customer.objects.filter(cust_id=xref.xref_cust_id).first()

        # Get all cards for this account
        card_nums = list(
            CardXref.objects.filter(xref_acct_id=xref.xref_acct_id).values_list(
                "xref_card_num", flat=True
            )
        )

        # Get transactions for all cards on this account
        transactions = list(
            Transaction.objects.filter(tran_card_num__in=card_nums).order_by("tran_orig_ts")
        )

        return {
            "account": account,
            "customer": customer,
            "card_nums": card_nums,
            "transactions": transactions,
            "statement_date": datetime.now(tz=UTC).strftime("%Y-%m-%d"),
        }

    def _write_text_statement(
        self,
        output_dir: Path,
        acct_id: str,
        statement: dict[str, object],
    ) -> None:
        """Write a text-format statement file."""
        account: Account = statement["account"]  # type: ignore[assignment]
        customer: Customer | None = statement["customer"]  # type: ignore[assignment]
        transactions: list[Transaction] = statement["transactions"]  # type: ignore[assignment]
        statement_date: str = statement["statement_date"]  # type: ignore[assignment]

        lines: list[str] = []
        lines.append("=" * 60)
        lines.append("          ACCOUNT STATEMENT")
        lines.append(f"          Date: {statement_date}")
        lines.append("=" * 60)
        lines.append("")

        if customer:
            lines.append(f"Name: {customer.cust_first_name} {customer.cust_last_name}")
            lines.append(f"Address: {customer.cust_addr_line_1}")
            if customer.cust_addr_line_2:
                lines.append(f"         {customer.cust_addr_line_2}")
            lines.append("")

        lines.append(f"Account ID: {acct_id}")
        lines.append(f"Current Balance: {account.acct_curr_bal}")
        lines.append(f"Credit Limit: {account.acct_credit_limit}")
        lines.append(f"Available Credit: {account.acct_credit_limit - account.acct_curr_bal}")
        lines.append("")
        lines.append("-" * 60)
        lines.append("TRANSACTIONS")
        lines.append("-" * 60)

        for txn in transactions:
            lines.append(
                f"  {txn.tran_orig_ts[:10]}  {txn.tran_desc[:30]:<30}  {txn.tran_amt:>10}"
            )

        lines.append("-" * 60)
        lines.append(f"  Cycle Credits:  {account.acct_curr_cyc_credit}")
        lines.append(f"  Cycle Debits:   {account.acct_curr_cyc_debit}")
        lines.append("=" * 60)

        file_path = output_dir / f"stmt_{acct_id}.txt"
        file_path.write_text("\n".join(lines) + "\n")

    def _write_html_statement(
        self,
        output_dir: Path,
        acct_id: str,
        statement: dict[str, object],
    ) -> None:
        """Write an HTML-format statement file."""
        account: Account = statement["account"]  # type: ignore[assignment]
        customer: Customer | None = statement["customer"]  # type: ignore[assignment]
        transactions: list[Transaction] = statement["transactions"]  # type: ignore[assignment]
        statement_date: str = statement["statement_date"]  # type: ignore[assignment]

        cust_name = ""
        if customer:
            cust_name = f"{customer.cust_first_name} {customer.cust_last_name}"

        txn_rows = ""
        for txn in transactions:
            txn_rows += (
                f"<tr><td>{txn.tran_orig_ts[:10]}</td>"
                f"<td>{txn.tran_desc}</td>"
                f"<td style='text-align:right'>{txn.tran_amt}</td></tr>\n"
            )

        html = f"""<!DOCTYPE html>
<html><head><title>Statement - {acct_id}</title></head>
<body>
<h1>Account Statement</h1>
<p>Date: {statement_date}</p>
<p>Name: {cust_name}</p>
<p>Account: {acct_id}</p>
<table border="1">
<tr><th>Balance</th><td>{account.acct_curr_bal}</td></tr>
<tr><th>Credit Limit</th><td>{account.acct_credit_limit}</td></tr>
</table>
<h2>Transactions</h2>
<table border="1">
<tr><th>Date</th><th>Description</th><th>Amount</th></tr>
{txn_rows}</table>
</body></html>
"""
        file_path = output_dir / f"stmt_{acct_id}.html"
        file_path.write_text(html)
