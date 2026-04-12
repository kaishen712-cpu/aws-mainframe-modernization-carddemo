"""Unit tests for report generation commands — 70% coverage target.

Tests gen_transaction_report, gen_category_report, gen_statements,
and gen_statements_v2 management commands.
"""

from __future__ import annotations

from decimal import Decimal
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command

from batch.models import (
    Account,
    CardXref,
    Customer,
    DailyTransaction,
    TranCatBal,
    Transaction,
    TransactionCategory,
    TransactionType,
)


@pytest.fixture()
def _report_data(db: None) -> None:
    """Create synthetic test data for report generation."""
    Account.objects.create(
        acct_id="00000000001",
        acct_active_status="Y",
        acct_curr_bal=Decimal("1000.00"),
        acct_credit_limit=Decimal("5000.00"),
        acct_curr_cyc_credit=Decimal("500.00"),
        acct_curr_cyc_debit=Decimal("200.00"),
        acct_group_id="GROUP1",
    )
    Customer.objects.create(
        cust_id="000000001",
        cust_first_name="John",
        cust_last_name="Doe",
        cust_addr_line_1="123 Main St",
    )
    CardXref.objects.create(
        xref_card_num="4111111111111111",
        xref_cust_id="000000001",
        xref_acct_id="00000000001",
    )
    DailyTransaction.objects.create(
        dalytran_id="0000000000000001",
        dalytran_type_cd="01",
        dalytran_cat_cd="0001",
        dalytran_source="Online",
        dalytran_desc="Test purchase",
        dalytran_amt=Decimal("100.00"),
        dalytran_merchant_id="000000001",
        dalytran_merchant_name="Test Store",
        dalytran_merchant_city="Test City",
        dalytran_merchant_zip="12345",
        dalytran_card_num="4111111111111111",
        dalytran_orig_ts="2025-06-15-10.30.00.000000",
    )
    Transaction.objects.create(
        tran_id="0000000000000001",
        tran_type_cd="01",
        tran_cat_cd="0001",
        tran_source="Online",
        tran_desc="Test purchase",
        tran_amt=Decimal("100.00"),
        tran_merchant_id="000000001",
        tran_merchant_name="Test Store",
        tran_merchant_city="Test City",
        tran_merchant_zip="12345",
        tran_card_num="4111111111111111",
        tran_orig_ts="2025-06-15-10.30.00.000000",
        tran_proc_ts="2025-06-15-10.30.01.000000",
    )
    TranCatBal.objects.create(
        trancat_acct_id="00000000001",
        trancat_type_cd="01",
        trancat_cd="0001",
        tran_cat_bal=Decimal("100.00"),
    )
    TransactionType.objects.create(
        tran_type="01",
        tran_type_desc="Purchase",
    )
    TransactionCategory.objects.create(
        tran_type_cd="01",
        tran_cat_cd="0001",
        tran_cat_type_desc="Retail",
    )


@pytest.mark.usefixtures("_report_data")
class TestGenTransactionReport:
    """Tests for gen_transaction_report command."""

    def test_report_to_stdout(self) -> None:
        """Report output to stdout contains transaction details."""
        out = StringIO()
        call_command("gen_transaction_report", stdout=out)
        output = out.getvalue()
        assert "DAILY TRANSACTION REPORT" in output
        assert "Total Transactions: 1" in output

    def test_report_masks_card_number(self) -> None:
        """Card numbers are masked in report output."""
        out = StringIO()
        call_command("gen_transaction_report", stdout=out)
        output = out.getvalue()
        assert "****1111" in output
        assert "4111111111111111" not in output

    def test_report_to_file(self, tmp_path: Path) -> None:
        """Report written to file when --output specified."""
        output_file = tmp_path / "report.txt"
        call_command("gen_transaction_report", output=str(output_file))
        assert output_file.exists()
        content = output_file.read_text()
        assert "DAILY TRANSACTION REPORT" in content


class TestGenTransactionReportEmpty:
    """Tests for gen_transaction_report on empty database."""

    def test_report_empty_database(self, db: None) -> None:
        """Report generates without errors on empty database."""
        out = StringIO()
        call_command("gen_transaction_report", stdout=out)
        assert "Total Transactions: 0" in out.getvalue()


@pytest.mark.usefixtures("_report_data")
class TestGenCategoryReport:
    """Tests for gen_category_report command."""

    def test_report_to_stdout(self) -> None:
        """Category report output contains balance details."""
        out = StringIO()
        call_command("gen_category_report", stdout=out)
        output = out.getvalue()
        assert "TRANSACTION CATEGORY BALANCE REPORT" in output
        assert "Total Records: 1" in output

    def test_report_includes_type_description(self) -> None:
        """Report includes transaction type description."""
        out = StringIO()
        call_command("gen_category_report", stdout=out)
        assert "Purchase" in out.getvalue()

    def test_report_includes_category_description(self) -> None:
        """Report includes category description."""
        out = StringIO()
        call_command("gen_category_report", stdout=out)
        assert "Retail" in out.getvalue()

    def test_report_to_file(self, tmp_path: Path) -> None:
        """Category report written to file."""
        output_file = tmp_path / "cat_report.txt"
        call_command("gen_category_report", output=str(output_file))
        assert output_file.exists()


class TestGenCategoryReportEmpty:
    """Tests for gen_category_report on empty database."""

    def test_report_empty_database(self, db: None) -> None:
        """Category report on empty DB."""
        out = StringIO()
        call_command("gen_category_report", stdout=out)
        assert "Total Records: 0" in out.getvalue()


@pytest.mark.usefixtures("_report_data")
class TestGenStatements:
    """Tests for gen_statements command."""

    def test_text_statement_generated(self, tmp_path: Path) -> None:
        """Text statement file created for account."""
        call_command("gen_statements", output_dir=str(tmp_path), format="text")
        stmt_file = tmp_path / "stmt_00000000001.txt"
        assert stmt_file.exists()
        content = stmt_file.read_text()
        assert "ACCOUNT STATEMENT" in content
        assert "John Doe" in content

    def test_html_statement_generated(self, tmp_path: Path) -> None:
        """HTML statement file created for account."""
        call_command("gen_statements", output_dir=str(tmp_path), format="html")
        stmt_file = tmp_path / "stmt_00000000001.html"
        assert stmt_file.exists()
        content = stmt_file.read_text()
        assert "<h1>Account Statement</h1>" in content

    def test_both_formats_generated(self, tmp_path: Path) -> None:
        """Both text and HTML statements generated."""
        call_command("gen_statements", output_dir=str(tmp_path), format="both")
        assert (tmp_path / "stmt_00000000001.txt").exists()
        assert (tmp_path / "stmt_00000000001.html").exists()

    def test_filter_by_account(self, tmp_path: Path) -> None:
        """Only specified account statement generated."""
        out = StringIO()
        call_command(
            "gen_statements",
            output_dir=str(tmp_path),
            acct_id="00000000001",
            stdout=out,
        )
        assert "Statements generated: 1" in out.getvalue()

    def test_statement_count_output(self, tmp_path: Path) -> None:
        """Command reports number of statements generated."""
        out = StringIO()
        call_command("gen_statements", output_dir=str(tmp_path), stdout=out)
        assert "Statements generated: 1" in out.getvalue()


class TestGenStatementsEmpty:
    """Tests for gen_statements on empty database."""

    def test_empty_database(self, tmp_path: Path, db: None) -> None:
        """No statements generated on empty database."""
        out = StringIO()
        call_command("gen_statements", output_dir=str(tmp_path), stdout=out)
        assert "Statements generated: 0" in out.getvalue()


@pytest.mark.usefixtures("_report_data")
class TestGenStatementsV2:
    """Tests for gen_statements_v2 command."""

    def test_statement_generated(self, tmp_path: Path) -> None:
        """V2 statement file created."""
        call_command("gen_statements_v2", output_dir=str(tmp_path))
        stmt_file = tmp_path / "stmt_v2_00000000001.txt"
        assert stmt_file.exists()
        content = stmt_file.read_text()
        assert "STATEMENT SUMMARY" in content

    def test_statement_includes_balance(self, tmp_path: Path) -> None:
        """V2 statement includes account balance."""
        call_command("gen_statements_v2", output_dir=str(tmp_path))
        content = (tmp_path / "stmt_v2_00000000001.txt").read_text()
        assert "Balance: 1000.00" in content

    def test_filter_by_account(self, tmp_path: Path) -> None:
        """V2 statement filtered by account."""
        out = StringIO()
        call_command(
            "gen_statements_v2",
            output_dir=str(tmp_path),
            acct_id="00000000001",
            stdout=out,
        )
        assert "Statements (v2) generated: 1" in out.getvalue()


class TestGenStatementsV2Empty:
    """Tests for gen_statements_v2 on empty database."""

    def test_empty_database(self, tmp_path: Path, db: None) -> None:
        """No V2 statements on empty database."""
        out = StringIO()
        call_command("gen_statements_v2", output_dir=str(tmp_path), stdout=out)
        assert "Statements (v2) generated: 0" in out.getvalue()
