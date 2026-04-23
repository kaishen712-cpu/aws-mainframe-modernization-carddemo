"""
Unit tests for CBSTM03A — Account Statements.

Tests cover:
- Empty input (no xref records)
- Single account with single card and transaction
- Multiple accounts
- Customer and account data populates statement
- Missing customer/account records handled gracefully
- Multiple cards per account
- Text statement formatting
- HTML statement formatting
- Currency formatting
"""

from __future__ import annotations

import unittest

from cbstm03a import (
    AccountStatement,
    CardTransactions,
    StatementTransaction,
    format_statement_text,
    format_statement_html,
    generate_account_statements,
    generate_statement_report,
    generate_statement_html,
    _format_currency,
)
from cbstm03b import (
    AccountRecord,
    CustomerRecord,
    InMemoryAccountFileRepository,
    InMemoryCustomerFileRepository,
    InMemoryTrnxFileRepository,
    InMemoryXrefFileRepository,
    TrnxRecord,
    XrefRecord,
)


def _make_repos():
    """Create a set of empty in-memory repositories."""
    return (
        InMemoryTrnxFileRepository(),
        InMemoryXrefFileRepository(),
        InMemoryCustomerFileRepository(),
        InMemoryAccountFileRepository(),
    )


def _make_trnx(**overrides: object) -> TrnxRecord:
    defaults = dict(
        trnx_card_num="4111111111111111",
        trnx_id="TRN0000000000001",
        trnx_type_cd="SA",
        trnx_cat_cd="0001",
        trnx_source="ONLINE",
        trnx_desc="Purchase",
        trnx_amt=100.00,
        trnx_merchant_id="000000001",
        trnx_merchant_name="Test",
        trnx_merchant_city="NYC",
        trnx_merchant_zip="10001",
        trnx_orig_ts="2024-01-15-10.30.00.000000",
        trnx_proc_ts="2024-01-15-12.00.00.000000",
    )
    defaults.update(overrides)
    return TrnxRecord(**defaults)  # type: ignore[arg-type]


def _make_xref(**overrides: object) -> XrefRecord:
    defaults = dict(
        xref_card_num="4111111111111111",
        xref_cust_id="000000001",
        xref_acct_id="00000000001",
    )
    defaults.update(overrides)
    return XrefRecord(**defaults)  # type: ignore[arg-type]


def _make_customer(**overrides: object) -> CustomerRecord:
    defaults = dict(
        cust_id="000000001",
        cust_first_name="JOHN",
        cust_middle_name="Q",
        cust_last_name="PUBLIC",
        cust_addr_line_1="123 MAIN ST",
        cust_addr_line_2="APT 4B",
        cust_addr_line_3="",
        cust_addr_state_cd="NY",
        cust_addr_country_cd="US",
        cust_addr_zip="10001",
        cust_phone_num_1="2125551234",
        cust_phone_num_2="",
        cust_ssn="123456789",
        cust_govt_issued_id="DL12345",
        cust_dob_yyyymmdd="1985-06-15",
        cust_eft_account_id="EFT001",
        cust_pri_card_holder_ind="Y",
        cust_fico_credit_score="750",
    )
    defaults.update(overrides)
    return CustomerRecord(**defaults)  # type: ignore[arg-type]


def _make_account(**overrides: object) -> AccountRecord:
    defaults = dict(
        acct_id="00000000001",
        acct_active_status="Y",
        acct_curr_bal=5000.00,
        acct_credit_limit=10000.00,
        acct_cash_credit_limit=2000.00,
        acct_open_date="2020-01-15",
        acct_expiration_date="2025-12-31",
        acct_reissue_date="2023-06-01",
        acct_curr_cyc_credit=1000.00,
        acct_curr_cyc_debit=500.00,
        acct_addr_zip="10001",
        acct_group_id="GRP001",
    )
    defaults.update(overrides)
    return AccountRecord(**defaults)  # type: ignore[arg-type]


class TestFormatCurrency(unittest.TestCase):
    """Tests for _format_currency helper."""

    def test_positive_amount(self) -> None:
        self.assertEqual(_format_currency(1234.56), "$1,234.56")

    def test_negative_amount(self) -> None:
        self.assertEqual(_format_currency(-500.00), "-$500.00")

    def test_zero(self) -> None:
        self.assertEqual(_format_currency(0.0), "$0.00")

    def test_large_amount(self) -> None:
        self.assertEqual(_format_currency(999999.99), "$999,999.99")


class TestGenerateAccountStatements(unittest.TestCase):
    """Tests for the generate_account_statements main function."""

    def test_empty_xrefs(self) -> None:
        trnx_repo, xref_repo, cust_repo, acct_repo = _make_repos()
        stmts = generate_account_statements(trnx_repo, xref_repo, cust_repo, acct_repo)
        self.assertEqual(len(stmts), 0)

    def test_single_account_with_transaction(self) -> None:
        trnx_repo, xref_repo, cust_repo, acct_repo = _make_repos()
        xref_repo.add_record(_make_xref())
        cust_repo.add_record(_make_customer())
        acct_repo.add_record(_make_account())
        trnx_repo.add_record(_make_trnx())

        stmts = generate_account_statements(trnx_repo, xref_repo, cust_repo, acct_repo)
        self.assertEqual(len(stmts), 1)
        stmt = stmts[0]
        self.assertEqual(stmt.acct_id, "00000000001")
        self.assertEqual(stmt.cust_first_name, "JOHN")
        self.assertEqual(stmt.acct_curr_bal, 5000.00)
        self.assertEqual(len(stmt.card_transactions), 1)
        self.assertEqual(len(stmt.card_transactions[0].transactions), 1)

    def test_multiple_accounts(self) -> None:
        trnx_repo, xref_repo, cust_repo, acct_repo = _make_repos()
        xref_repo.add_record(_make_xref(
            xref_card_num="1111111111111111",
            xref_cust_id="000000001",
            xref_acct_id="00000000001",
        ))
        xref_repo.add_record(_make_xref(
            xref_card_num="2222222222222222",
            xref_cust_id="000000002",
            xref_acct_id="00000000002",
        ))
        cust_repo.add_record(_make_customer(cust_id="000000001"))
        cust_repo.add_record(_make_customer(cust_id="000000002", cust_first_name="JANE"))
        acct_repo.add_record(_make_account(acct_id="00000000001"))
        acct_repo.add_record(_make_account(acct_id="00000000002", acct_curr_bal=3000.00))

        stmts = generate_account_statements(trnx_repo, xref_repo, cust_repo, acct_repo)
        self.assertEqual(len(stmts), 2)
        self.assertEqual(stmts[0].acct_id, "00000000001")
        self.assertEqual(stmts[1].acct_id, "00000000002")

    def test_missing_customer(self) -> None:
        trnx_repo, xref_repo, cust_repo, acct_repo = _make_repos()
        xref_repo.add_record(_make_xref())
        acct_repo.add_record(_make_account())
        # No customer record

        stmts = generate_account_statements(trnx_repo, xref_repo, cust_repo, acct_repo)
        self.assertEqual(len(stmts), 1)
        self.assertEqual(stmts[0].cust_first_name, "")

    def test_missing_account(self) -> None:
        trnx_repo, xref_repo, cust_repo, acct_repo = _make_repos()
        xref_repo.add_record(_make_xref())
        cust_repo.add_record(_make_customer())
        # No account record

        stmts = generate_account_statements(trnx_repo, xref_repo, cust_repo, acct_repo)
        self.assertEqual(len(stmts), 1)
        self.assertEqual(stmts[0].acct_curr_bal, 0.0)

    def test_multiple_cards_same_account(self) -> None:
        trnx_repo, xref_repo, cust_repo, acct_repo = _make_repos()
        xref_repo.add_record(_make_xref(
            xref_card_num="1111111111111111",
            xref_cust_id="000000001",
            xref_acct_id="00000000001",
        ))
        xref_repo.add_record(_make_xref(
            xref_card_num="2222222222222222",
            xref_cust_id="000000001",
            xref_acct_id="00000000001",
        ))
        cust_repo.add_record(_make_customer())
        acct_repo.add_record(_make_account())
        trnx_repo.add_record(_make_trnx(trnx_card_num="1111111111111111", trnx_id="T001"))
        trnx_repo.add_record(_make_trnx(trnx_card_num="2222222222222222", trnx_id="T002"))

        stmts = generate_account_statements(trnx_repo, xref_repo, cust_repo, acct_repo)
        self.assertEqual(len(stmts), 1)
        self.assertEqual(len(stmts[0].card_transactions), 2)


class TestFormatStatementText(unittest.TestCase):
    """Tests for format_statement_text."""

    def _make_stmt(self) -> AccountStatement:
        return AccountStatement(
            acct_id="00000000001",
            acct_status="Y",
            acct_curr_bal=5000.00,
            acct_credit_limit=10000.00,
            acct_cash_credit_limit=2000.00,
            acct_open_date="2020-01-15",
            acct_expiration_date="2025-12-31",
            cust_id="000000001",
            cust_first_name="JOHN",
            cust_middle_name="Q",
            cust_last_name="PUBLIC",
            cust_addr_line_1="123 MAIN ST",
            cust_addr_line_2="APT 4B",
            cust_addr_line_3="",
            cust_addr_state_cd="NY",
            cust_addr_zip="10001",
            card_transactions=[
                CardTransactions(
                    card_num="4111111111111111",
                    transactions=[
                        StatementTransaction(
                            tran_id="TRN001",
                            tran_type_cd="SA",
                            tran_cat_cd="0001",
                            tran_source="ONLINE",
                            tran_desc="Purchase",
                            tran_amt=100.00,
                        ),
                    ],
                ),
            ],
        )

    def test_contains_header(self) -> None:
        lines = format_statement_text(self._make_stmt())
        self.assertTrue(any("ACCOUNT STATEMENT" in l for l in lines))

    def test_contains_customer_name(self) -> None:
        lines = format_statement_text(self._make_stmt())
        all_text = "\n".join(lines)
        self.assertIn("JOHN", all_text)
        self.assertIn("PUBLIC", all_text)

    def test_contains_account_info(self) -> None:
        lines = format_statement_text(self._make_stmt())
        all_text = "\n".join(lines)
        self.assertIn("00000000001", all_text)
        self.assertIn("$5,000.00", all_text)
        self.assertIn("$10,000.00", all_text)

    def test_contains_transaction(self) -> None:
        lines = format_statement_text(self._make_stmt())
        all_text = "\n".join(lines)
        self.assertIn("TRN001", all_text)
        self.assertIn("$100.00", all_text)

    def test_contains_card_number(self) -> None:
        lines = format_statement_text(self._make_stmt())
        all_text = "\n".join(lines)
        self.assertIn("4111111111111111", all_text)

    def test_no_transactions(self) -> None:
        stmt = self._make_stmt()
        stmt.card_transactions = []
        lines = format_statement_text(stmt)
        all_text = "\n".join(lines)
        self.assertNotIn("TRANSACTIONS", all_text)


class TestFormatStatementHtml(unittest.TestCase):
    """Tests for format_statement_html."""

    def _make_stmt(self) -> AccountStatement:
        return AccountStatement(
            acct_id="00000000001",
            acct_status="Y",
            acct_curr_bal=5000.00,
            acct_credit_limit=10000.00,
            acct_cash_credit_limit=2000.00,
            acct_open_date="2020-01-15",
            acct_expiration_date="2025-12-31",
            cust_id="000000001",
            cust_first_name="JOHN",
            cust_middle_name="",
            cust_last_name="DOE",
            cust_addr_line_1="456 ELM ST",
            cust_addr_line_2="",
            cust_addr_line_3="",
            cust_addr_state_cd="CA",
            cust_addr_zip="90210",
            card_transactions=[
                CardTransactions(
                    card_num="5555555555554444",
                    transactions=[
                        StatementTransaction(
                            tran_id="TRN002",
                            tran_type_cd="RT",
                            tran_cat_cd="0002",
                            tran_source="POS",
                            tran_desc="Return",
                            tran_amt=-50.00,
                        ),
                    ],
                ),
            ],
        )

    def test_is_valid_html(self) -> None:
        lines = format_statement_html(self._make_stmt())
        html = "\n".join(lines)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("<html>", html)
        self.assertIn("</html>", html)

    def test_contains_customer_name(self) -> None:
        lines = format_statement_html(self._make_stmt())
        html = "\n".join(lines)
        self.assertIn("JOHN", html)
        self.assertIn("DOE", html)

    def test_contains_account_info(self) -> None:
        lines = format_statement_html(self._make_stmt())
        html = "\n".join(lines)
        self.assertIn("00000000001", html)
        self.assertIn("$5,000.00", html)

    def test_contains_transaction(self) -> None:
        lines = format_statement_html(self._make_stmt())
        html = "\n".join(lines)
        self.assertIn("TRN002", html)
        self.assertIn("-$50.00", html)

    def test_no_transactions(self) -> None:
        stmt = self._make_stmt()
        stmt.card_transactions = []
        lines = format_statement_html(stmt)
        html = "\n".join(lines)
        self.assertNotIn("<h2>Transactions</h2>", html)


class TestConvenienceFunctions(unittest.TestCase):
    """Tests for generate_statement_report and generate_statement_html."""

    def test_report_returns_text_lines(self) -> None:
        trnx_repo, xref_repo, cust_repo, acct_repo = _make_repos()
        xref_repo.add_record(_make_xref())
        cust_repo.add_record(_make_customer())
        acct_repo.add_record(_make_account())

        lines = generate_statement_report(trnx_repo, xref_repo, cust_repo, acct_repo)
        all_text = "\n".join(lines)
        self.assertIn("ACCOUNT STATEMENT", all_text)

    def test_html_returns_html_lines(self) -> None:
        trnx_repo, xref_repo, cust_repo, acct_repo = _make_repos()
        xref_repo.add_record(_make_xref())
        cust_repo.add_record(_make_customer())
        acct_repo.add_record(_make_account())

        lines = generate_statement_html(trnx_repo, xref_repo, cust_repo, acct_repo)
        html = "\n".join(lines)
        self.assertIn("<html>", html)

    def test_empty_returns_empty(self) -> None:
        trnx_repo, xref_repo, cust_repo, acct_repo = _make_repos()
        lines = generate_statement_report(trnx_repo, xref_repo, cust_repo, acct_repo)
        self.assertEqual(len(lines), 0)


if __name__ == "__main__":
    unittest.main()
