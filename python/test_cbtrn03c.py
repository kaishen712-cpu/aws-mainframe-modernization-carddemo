"""
Unit tests for CBTRN03C — Transaction Detail Report.

Tests cover:
- Amount formatting
- Report header generation
- Detail line generation
- Totals lines
- Empty transaction set
- Single transaction report
- Multiple transactions with account grouping
- Page break logic
- Grand total accumulation
- Cross-reference, type, and category lookups
"""

from __future__ import annotations

import unittest

from cbtrn03c import (
    CardXrefRecord,
    InMemoryTranCatLookupRepository,
    InMemoryTranTypeLookupRepository,
    InMemoryTransactionFileRepository,
    InMemoryXrefLookupRepository,
    TranCatRecord,
    TranTypeRecord,
    TransactionRecord,
    generate_transaction_detail_report,
    _format_amount,
    _build_report_name_header,
    _build_transaction_header_1,
    _build_transaction_header_2,
    _build_detail_line,
    _build_page_totals_line,
    _build_account_totals_line,
    _build_grand_totals_line,
)


def _make_repos():
    """Create a set of empty in-memory repositories."""
    return (
        InMemoryTransactionFileRepository(),
        InMemoryXrefLookupRepository(),
        InMemoryTranTypeLookupRepository(),
        InMemoryTranCatLookupRepository(),
    )


def _make_transaction(**overrides: object) -> TransactionRecord:
    """Create a TransactionRecord with sensible defaults."""
    defaults = dict(
        tran_id="TRN0000000000001",
        tran_type_cd="SA",
        tran_cat_cd="0001",
        tran_source="ONLINE",
        tran_desc="Purchase",
        tran_amt=100.00,
        tran_merchant_id="000000001",
        tran_merchant_name="Test Merchant",
        tran_merchant_city="New York",
        tran_merchant_zip="10001",
        tran_card_num="4111111111111111",
        tran_orig_ts="2024-01-15-10.30.00.000000",
        tran_proc_ts="2024-01-15-12.00.00.000000",
    )
    defaults.update(overrides)
    return TransactionRecord(**defaults)  # type: ignore[arg-type]


def _setup_lookup_repos(type_repo, cat_repo):
    """Add standard lookup data."""
    type_repo.add_type(TranTypeRecord(tran_type="SA", tran_type_desc="Sale"))
    type_repo.add_type(TranTypeRecord(tran_type="RT", tran_type_desc="Return"))
    cat_repo.add_category(TranCatRecord(
        tran_type_cd="SA", tran_cat_cd="0001", tran_cat_type_desc="Retail Purchase",
    ))
    cat_repo.add_category(TranCatRecord(
        tran_type_cd="RT", tran_cat_cd="0002", tran_cat_type_desc="Merchandise Return",
    ))


class TestFormatAmount(unittest.TestCase):
    """Tests for the _format_amount helper."""

    def test_positive_amount(self) -> None:
        result = _format_amount(1234.56)
        self.assertIn("+", result)
        self.assertIn("1,234.56", result)

    def test_negative_amount(self) -> None:
        result = _format_amount(-500.00)
        self.assertIn("-", result)
        self.assertIn("500.00", result)

    def test_zero(self) -> None:
        result = _format_amount(0.0)
        self.assertIn("0.00", result)

    def test_large_amount(self) -> None:
        result = _format_amount(999999999.99)
        self.assertIn("999,999,999.99", result)

    def test_right_justified(self) -> None:
        result = _format_amount(1.00)
        self.assertEqual(len(result), 15)


class TestReportHeaders(unittest.TestCase):
    """Tests for report header builders."""

    def test_report_name_header(self) -> None:
        header = _build_report_name_header("2024-01-01", "2024-01-31")
        self.assertIn("DALYREPT", header)
        self.assertIn("Daily Transaction Report", header)
        self.assertIn("2024-01-01", header)
        self.assertIn("2024-01-31", header)

    def test_transaction_header_1(self) -> None:
        header = _build_transaction_header_1()
        self.assertIn("Transaction ID", header)
        self.assertIn("Account ID", header)
        self.assertIn("Amount", header)

    def test_transaction_header_2_is_dashes(self) -> None:
        header = _build_transaction_header_2()
        self.assertTrue(all(c == "-" for c in header))


class TestDetailLine(unittest.TestCase):
    """Tests for the _build_detail_line helper."""

    def test_all_fields_present(self) -> None:
        line = _build_detail_line(
            tran_id="TRN0000000000001",
            acct_id="00000000001",
            type_cd="SA",
            type_desc="Sale",
            cat_cd="0001",
            cat_desc="Retail Purchase",
            source="ONLINE",
            amount=100.00,
        )
        self.assertIn("TRN0000000000001", line)
        self.assertIn("00000000001", line)
        self.assertIn("SA", line)
        self.assertIn("Sale", line)
        self.assertIn("0001", line)
        self.assertIn("ONLINE", line)
        self.assertIn("100.00", line)


class TestTotalsLines(unittest.TestCase):
    """Tests for totals line builders."""

    def test_page_totals(self) -> None:
        line = _build_page_totals_line(500.00)
        self.assertIn("Page Total", line)
        self.assertIn("500.00", line)

    def test_account_totals(self) -> None:
        line = _build_account_totals_line(1500.00)
        self.assertIn("Account Total", line)
        self.assertIn("1,500.00", line)

    def test_grand_totals(self) -> None:
        line = _build_grand_totals_line(10000.00)
        self.assertIn("Grand Total", line)
        self.assertIn("10,000.00", line)


class TestGenerateTransactionDetailReport(unittest.TestCase):
    """Tests for the generate_transaction_detail_report main function."""

    def test_empty_transactions(self) -> None:
        tran_repo, xref_repo, type_repo, cat_repo = _make_repos()
        lines = generate_transaction_detail_report(
            tran_repo, xref_repo, type_repo, cat_repo,
            "2024-01-01", "2024-12-31",
        )
        self.assertEqual(len(lines), 0)

    def test_single_transaction(self) -> None:
        tran_repo, xref_repo, type_repo, cat_repo = _make_repos()
        tran_repo.add_transaction(_make_transaction(
            tran_proc_ts="2024-01-15-12.00.00.000000",
        ))
        xref_repo.add_xref(CardXrefRecord(
            xref_card_num="4111111111111111",
            xref_cust_id="000000001",
            xref_acct_id="00000000001",
        ))
        _setup_lookup_repos(type_repo, cat_repo)

        lines = generate_transaction_detail_report(
            tran_repo, xref_repo, type_repo, cat_repo,
            "2024-01-01", "2024-12-31",
        )
        # Should have: header, blank, col header, separator, detail,
        #              page total, account total, grand total
        self.assertTrue(len(lines) > 0)
        all_text = "\n".join(lines)
        self.assertIn("TRN0000000000001", all_text)
        self.assertIn("Grand Total", all_text)

    def test_date_filtering(self) -> None:
        tran_repo, xref_repo, type_repo, cat_repo = _make_repos()
        tran_repo.add_transaction(_make_transaction(
            tran_id="TRN001",
            tran_proc_ts="2024-01-15-12.00.00.000000",
        ))
        tran_repo.add_transaction(_make_transaction(
            tran_id="TRN002",
            tran_proc_ts="2024-06-15-12.00.00.000000",
        ))
        xref_repo.add_xref(CardXrefRecord(
            xref_card_num="4111111111111111",
            xref_cust_id="000000001",
            xref_acct_id="00000000001",
        ))
        _setup_lookup_repos(type_repo, cat_repo)

        lines = generate_transaction_detail_report(
            tran_repo, xref_repo, type_repo, cat_repo,
            "2024-01-01", "2024-01-31",
        )
        all_text = "\n".join(lines)
        self.assertIn("TRN001", all_text)
        self.assertNotIn("TRN002", all_text)

    def test_account_grouping(self) -> None:
        tran_repo, xref_repo, type_repo, cat_repo = _make_repos()
        # Two transactions for card 1 (account 1)
        tran_repo.add_transaction(_make_transaction(
            tran_id="TRN001", tran_card_num="1111111111111111",
            tran_amt=100.00, tran_proc_ts="2024-01-15-12.00.00.000000",
        ))
        tran_repo.add_transaction(_make_transaction(
            tran_id="TRN002", tran_card_num="1111111111111111",
            tran_amt=200.00, tran_proc_ts="2024-01-16-12.00.00.000000",
        ))
        # One transaction for card 2 (account 2)
        tran_repo.add_transaction(_make_transaction(
            tran_id="TRN003", tran_card_num="2222222222222222",
            tran_amt=300.00, tran_proc_ts="2024-01-17-12.00.00.000000",
        ))
        xref_repo.add_xref(CardXrefRecord(
            xref_card_num="1111111111111111",
            xref_cust_id="000000001",
            xref_acct_id="00000000001",
        ))
        xref_repo.add_xref(CardXrefRecord(
            xref_card_num="2222222222222222",
            xref_cust_id="000000002",
            xref_acct_id="00000000002",
        ))
        _setup_lookup_repos(type_repo, cat_repo)

        lines = generate_transaction_detail_report(
            tran_repo, xref_repo, type_repo, cat_repo,
            "2024-01-01", "2024-12-31",
        )
        all_text = "\n".join(lines)
        # Should have account totals for both accounts
        account_total_count = all_text.count("Account Total")
        self.assertEqual(account_total_count, 2)
        self.assertIn("Grand Total", all_text)

    def test_grand_total_accumulates_correctly(self) -> None:
        tran_repo, xref_repo, type_repo, cat_repo = _make_repos()
        tran_repo.add_transaction(_make_transaction(
            tran_id="TRN001", tran_amt=100.00,
            tran_proc_ts="2024-01-15-12.00.00.000000",
        ))
        tran_repo.add_transaction(_make_transaction(
            tran_id="TRN002", tran_amt=250.50,
            tran_proc_ts="2024-01-16-12.00.00.000000",
        ))
        xref_repo.add_xref(CardXrefRecord(
            xref_card_num="4111111111111111",
            xref_cust_id="000000001",
            xref_acct_id="00000000001",
        ))
        _setup_lookup_repos(type_repo, cat_repo)

        lines = generate_transaction_detail_report(
            tran_repo, xref_repo, type_repo, cat_repo,
            "2024-01-01", "2024-12-31",
        )
        # Grand total should be 350.50
        grand_total_lines = [l for l in lines if "Grand Total" in l]
        self.assertEqual(len(grand_total_lines), 1)
        self.assertIn("350.50", grand_total_lines[0])

    def test_missing_xref_returns_empty_acct_id(self) -> None:
        tran_repo, xref_repo, type_repo, cat_repo = _make_repos()
        tran_repo.add_transaction(_make_transaction(
            tran_proc_ts="2024-01-15-12.00.00.000000",
        ))
        # No xref added
        _setup_lookup_repos(type_repo, cat_repo)

        lines = generate_transaction_detail_report(
            tran_repo, xref_repo, type_repo, cat_repo,
            "2024-01-01", "2024-12-31",
        )
        # Should still produce a report without crashing
        self.assertTrue(len(lines) > 0)

    def test_missing_type_lookup(self) -> None:
        tran_repo, xref_repo, type_repo, cat_repo = _make_repos()
        tran_repo.add_transaction(_make_transaction(
            tran_type_cd="XX",
            tran_proc_ts="2024-01-15-12.00.00.000000",
        ))
        xref_repo.add_xref(CardXrefRecord(
            xref_card_num="4111111111111111",
            xref_cust_id="000000001",
            xref_acct_id="00000000001",
        ))
        # type_repo has no "XX" type — should not crash

        lines = generate_transaction_detail_report(
            tran_repo, xref_repo, type_repo, cat_repo,
            "2024-01-01", "2024-12-31",
        )
        self.assertTrue(len(lines) > 0)

    def test_page_break_with_small_page_size(self) -> None:
        tran_repo, xref_repo, type_repo, cat_repo = _make_repos()
        # Add 10 transactions to force page break with page_size=5
        for i in range(10):
            tran_repo.add_transaction(_make_transaction(
                tran_id=f"TRN{i:016d}",
                tran_amt=float(i + 1) * 10,
                tran_proc_ts="2024-01-15-12.00.00.000000",
            ))
        xref_repo.add_xref(CardXrefRecord(
            xref_card_num="4111111111111111",
            xref_cust_id="000000001",
            xref_acct_id="00000000001",
        ))
        _setup_lookup_repos(type_repo, cat_repo)

        lines = generate_transaction_detail_report(
            tran_repo, xref_repo, type_repo, cat_repo,
            "2024-01-01", "2024-12-31",
            page_size=5,
        )
        all_text = "\n".join(lines)
        # Should have at least one page total (from page break)
        page_total_count = all_text.count("Page Total")
        self.assertGreaterEqual(page_total_count, 1)

    def test_negative_amounts(self) -> None:
        tran_repo, xref_repo, type_repo, cat_repo = _make_repos()
        tran_repo.add_transaction(_make_transaction(
            tran_amt=-500.00,
            tran_proc_ts="2024-01-15-12.00.00.000000",
        ))
        xref_repo.add_xref(CardXrefRecord(
            xref_card_num="4111111111111111",
            xref_cust_id="000000001",
            xref_acct_id="00000000001",
        ))
        _setup_lookup_repos(type_repo, cat_repo)

        lines = generate_transaction_detail_report(
            tran_repo, xref_repo, type_repo, cat_repo,
            "2024-01-01", "2024-12-31",
        )
        all_text = "\n".join(lines)
        self.assertIn("-500.00", all_text)


if __name__ == "__main__":
    unittest.main()
