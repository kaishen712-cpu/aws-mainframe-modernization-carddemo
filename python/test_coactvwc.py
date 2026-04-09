"""
Unit tests for coactvwc.py — the Python translation of COACTVWC.CBL.

These tests verify the same business rules that the original COBOL program
enforces for the Account View function.
"""

import unittest

from coactvwc import (
    AccountRecord,
    CardXrefRecord,
    CustomerRecord,
    InMemoryAccountRepository,
    InMemoryCardXrefRepository,
    InMemoryCustomerRepository,
    format_ssn,
    get_header_info,
    validate_account_id,
    view_account,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_account() -> AccountRecord:
    """Return a sample account record."""
    return AccountRecord(
        acct_id="00000000001",
        active_status="Y",
        curr_bal=1500.75,
        credit_limit=10000.00,
        cash_credit_limit=5000.00,
        open_date="2020-01-15",
        expiration_date="2025-12-31",
        reissue_date="2024-06-01",
        curr_cyc_credit=500.00,
        curr_cyc_debit=200.00,
        addr_zip="98101",
        group_id="GRP001",
    )


def _sample_customer() -> CustomerRecord:
    """Return a sample customer record."""
    return CustomerRecord(
        cust_id="000000001",
        first_name="JOHN",
        middle_name="Q",
        last_name="DOE",
        addr_line_1="123 Main St",
        addr_line_2="Apt 4B",
        addr_line_3="Seattle",
        addr_state_cd="WA",
        addr_country_cd="USA",
        addr_zip="98101",
        phone_num_1="(206)555-0100",
        phone_num_2="(206)555-0101",
        ssn="123456789",
        govt_issued_id="DL12345678",
        dob_yyyy_mm_dd="1985-03-15",
        eft_account_id="EFT0000001",
        pri_card_holder_ind="Y",
        fico_credit_score=750,
    )


def _sample_xref() -> CardXrefRecord:
    """Return a sample card cross-reference record."""
    return CardXrefRecord(
        card_num="4000123456789010",
        cust_id="000000001",
        acct_id="00000000001",
    )


def _make_repos():
    """Return pre-loaded repositories for a standard test scenario."""
    acct_repo = InMemoryAccountRepository()
    xref_repo = InMemoryCardXrefRepository()
    cust_repo = InMemoryCustomerRepository()

    acct_repo.add_account(_sample_account())
    xref_repo.add_xref(_sample_xref())
    cust_repo.add_customer(_sample_customer())

    return acct_repo, xref_repo, cust_repo


# ===========================================================================
# 1. Account ID validation
# ===========================================================================

class TestValidateAccountId(unittest.TestCase):
    """Tests corresponding to 2210-EDIT-ACCOUNT paragraph."""

    def test_valid_numeric_id(self):
        result = validate_account_id("00000000001")
        self.assertTrue(result.is_valid)

    def test_valid_short_numeric(self):
        """Short numeric input is valid (will be zero-padded later)."""
        result = validate_account_id("1")
        self.assertTrue(result.is_valid)

    def test_blank_input(self):
        result = validate_account_id("")
        self.assertFalse(result.is_valid)
        self.assertIn("Account number not provided", result.error_message)

    def test_spaces_input(self):
        result = validate_account_id("   ")
        self.assertFalse(result.is_valid)
        self.assertIn("Account number not provided", result.error_message)

    def test_asterisk_input(self):
        """Asterisk is treated as blank in the COBOL program."""
        result = validate_account_id("*")
        self.assertFalse(result.is_valid)
        self.assertIn("Account number not provided", result.error_message)

    def test_non_numeric(self):
        result = validate_account_id("ABC123")
        self.assertFalse(result.is_valid)
        self.assertIn("non-zero 11 digit number", result.error_message)

    def test_all_zeros(self):
        result = validate_account_id("00000000000")
        self.assertFalse(result.is_valid)
        self.assertIn("non-zero 11 digit number", result.error_message)

    def test_zero(self):
        result = validate_account_id("0")
        self.assertFalse(result.is_valid)
        self.assertIn("non-zero 11 digit number", result.error_message)


# ===========================================================================
# 2. Full view_account workflow
# ===========================================================================

class TestViewAccount(unittest.TestCase):
    """End-to-end tests for the view_account function."""

    def test_successful_view(self):
        """Happy path: valid account returns all data."""
        acct_repo, xref_repo, cust_repo = _make_repos()
        result = view_account("1", acct_repo, xref_repo, cust_repo)

        self.assertTrue(result.success)
        self.assertIsNotNone(result.account)
        self.assertIsNotNone(result.customer)
        self.assertIsNotNone(result.card_xref)
        self.assertEqual(result.account.acct_id, "00000000001")
        self.assertEqual(result.customer.first_name, "JOHN")
        self.assertEqual(result.card_xref.card_num, "4000123456789010")

    def test_full_11_digit_id(self):
        """Full 11-digit account ID works."""
        acct_repo, xref_repo, cust_repo = _make_repos()
        result = view_account("00000000001", acct_repo, xref_repo, cust_repo)
        self.assertTrue(result.success)

    def test_invalid_account_id(self):
        """Non-numeric account ID rejected before any lookup."""
        acct_repo, xref_repo, cust_repo = _make_repos()
        result = view_account("ABC", acct_repo, xref_repo, cust_repo)
        self.assertFalse(result.success)
        self.assertIn("non-zero 11 digit number", result.message)

    def test_blank_account_id(self):
        """Blank account ID rejected."""
        acct_repo, xref_repo, cust_repo = _make_repos()
        result = view_account("", acct_repo, xref_repo, cust_repo)
        self.assertFalse(result.success)
        self.assertIn("Account number not provided", result.message)

    def test_account_not_in_xref(self):
        """Account not found in cross-reference file."""
        acct_repo, xref_repo, cust_repo = _make_repos()
        result = view_account("99999999999", acct_repo, xref_repo, cust_repo)
        self.assertFalse(result.success)
        self.assertIn("not found in Cross ref file", result.message)

    def test_account_not_in_master(self):
        """Account in xref but not in account master."""
        acct_repo = InMemoryAccountRepository()
        xref_repo = InMemoryCardXrefRepository()
        cust_repo = InMemoryCustomerRepository()
        xref_repo.add_xref(CardXrefRecord(
            card_num="4000123456789010",
            cust_id="000000001",
            acct_id="00000000002",
        ))
        result = view_account("2", acct_repo, xref_repo, cust_repo)
        self.assertFalse(result.success)
        self.assertIn("not found in Acct Master file", result.message)

    def test_customer_not_in_master(self):
        """Account exists but customer not found."""
        acct_repo = InMemoryAccountRepository()
        xref_repo = InMemoryCardXrefRepository()
        cust_repo = InMemoryCustomerRepository()
        acct_repo.add_account(AccountRecord(acct_id="00000000003"))
        xref_repo.add_xref(CardXrefRecord(
            card_num="4000123456789010",
            cust_id="999999999",
            acct_id="00000000003",
        ))
        result = view_account("3", acct_repo, xref_repo, cust_repo)
        self.assertFalse(result.success)
        self.assertIn("not found in customer master", result.message)

    def test_result_contains_account_details(self):
        """Verify all account fields are accessible on success."""
        acct_repo, xref_repo, cust_repo = _make_repos()
        result = view_account("1", acct_repo, xref_repo, cust_repo)

        self.assertTrue(result.success)
        self.assertEqual(result.account.active_status, "Y")
        self.assertAlmostEqual(result.account.curr_bal, 1500.75)
        self.assertAlmostEqual(result.account.credit_limit, 10000.00)
        self.assertEqual(result.account.open_date, "2020-01-15")
        self.assertEqual(result.account.group_id, "GRP001")

    def test_result_contains_customer_details(self):
        """Verify all customer fields are accessible on success."""
        acct_repo, xref_repo, cust_repo = _make_repos()
        result = view_account("1", acct_repo, xref_repo, cust_repo)

        self.assertTrue(result.success)
        self.assertEqual(result.customer.last_name, "DOE")
        self.assertEqual(result.customer.ssn, "123456789")
        self.assertEqual(result.customer.fico_credit_score, 750)
        self.assertEqual(result.customer.addr_state_cd, "WA")


# ===========================================================================
# 3. SSN formatting
# ===========================================================================

class TestFormatSSN(unittest.TestCase):
    """Tests for SSN display formatting."""

    def test_standard_9_digit(self):
        self.assertEqual(format_ssn("123456789"), "123-45-6789")

    def test_short_ssn_zero_padded(self):
        self.assertEqual(format_ssn("1234"), "000-00-1234")

    def test_already_padded(self):
        self.assertEqual(format_ssn("000000001"), "000-00-0001")

    def test_with_whitespace(self):
        self.assertEqual(format_ssn("  123456789  "), "123-45-6789")


# ===========================================================================
# 4. Header info helper
# ===========================================================================

class TestGetHeaderInfo(unittest.TestCase):
    """Tests for screen header information."""

    def test_contains_program_name(self):
        info = get_header_info()
        self.assertEqual(info["program_name"], "COACTVWC")

    def test_contains_transaction_id(self):
        info = get_header_info()
        self.assertEqual(info["transaction_id"], "CAVW")

    def test_contains_titles(self):
        info = get_header_info()
        self.assertIn("AWS Mainframe Modernization", info["title01"])
        self.assertIn("CardDemo", info["title02"])

    def test_contains_date_and_time(self):
        info = get_header_info()
        self.assertIn("current_date", info)
        self.assertIn("current_time", info)
        # Date format: MM/DD/YY
        self.assertEqual(len(info["current_date"]), 8)
        # Time format: HH:MM:SS
        self.assertEqual(len(info["current_time"]), 8)


# ===========================================================================
# 5. Repository implementations
# ===========================================================================

class TestInMemoryAccountRepository(unittest.TestCase):
    """Tests for InMemoryAccountRepository."""

    def test_add_and_get(self):
        repo = InMemoryAccountRepository()
        acct = _sample_account()
        repo.add_account(acct)
        result = repo.get_account("00000000001")
        self.assertIsNotNone(result)
        self.assertEqual(result.acct_id, "00000000001")

    def test_get_nonexistent(self):
        repo = InMemoryAccountRepository()
        result = repo.get_account("99999999999")
        self.assertIsNone(result)


class TestInMemoryCardXrefRepository(unittest.TestCase):
    """Tests for InMemoryCardXrefRepository."""

    def test_lookup_by_account(self):
        repo = InMemoryCardXrefRepository()
        xref = _sample_xref()
        repo.add_xref(xref)
        result = repo.lookup_by_account("00000000001")
        self.assertIsNotNone(result)
        self.assertEqual(result.card_num, "4000123456789010")

    def test_lookup_by_card(self):
        repo = InMemoryCardXrefRepository()
        xref = _sample_xref()
        repo.add_xref(xref)
        result = repo.lookup_by_card("4000123456789010")
        self.assertIsNotNone(result)
        self.assertEqual(result.acct_id, "00000000001")

    def test_lookup_nonexistent(self):
        repo = InMemoryCardXrefRepository()
        self.assertIsNone(repo.lookup_by_account("99999999999"))
        self.assertIsNone(repo.lookup_by_card("9999999999999999"))


class TestInMemoryCustomerRepository(unittest.TestCase):
    """Tests for InMemoryCustomerRepository."""

    def test_add_and_get(self):
        repo = InMemoryCustomerRepository()
        cust = _sample_customer()
        repo.add_customer(cust)
        result = repo.get_customer("000000001")
        self.assertIsNotNone(result)
        self.assertEqual(result.first_name, "JOHN")

    def test_get_nonexistent(self):
        repo = InMemoryCustomerRepository()
        result = repo.get_customer("999999999")
        self.assertIsNone(result)


# ===========================================================================
# 6. Edge cases
# ===========================================================================

class TestEdgeCases(unittest.TestCase):
    """Edge case tests."""

    def test_account_id_with_leading_zeros(self):
        """Leading zeros in account ID are preserved."""
        acct_repo, xref_repo, cust_repo = _make_repos()
        result = view_account("00000000001", acct_repo, xref_repo, cust_repo)
        self.assertTrue(result.success)

    def test_short_account_id_zero_padded(self):
        """Short numeric ID is zero-padded to 11 digits."""
        acct_repo, xref_repo, cust_repo = _make_repos()
        result = view_account("1", acct_repo, xref_repo, cust_repo)
        self.assertTrue(result.success)

    def test_account_with_spaces_around(self):
        """Leading/trailing spaces are trimmed."""
        acct_repo, xref_repo, cust_repo = _make_repos()
        result = view_account("  1  ", acct_repo, xref_repo, cust_repo)
        self.assertTrue(result.success)

    def test_zero_balances(self):
        """Account with zero balances."""
        acct_repo = InMemoryAccountRepository()
        xref_repo = InMemoryCardXrefRepository()
        cust_repo = InMemoryCustomerRepository()
        acct_repo.add_account(AccountRecord(
            acct_id="00000000004",
            curr_bal=0.0,
            credit_limit=0.0,
        ))
        xref_repo.add_xref(CardXrefRecord(
            card_num="4000000000000004",
            cust_id="000000004",
            acct_id="00000000004",
        ))
        cust_repo.add_customer(CustomerRecord(cust_id="000000004"))
        result = view_account("4", acct_repo, xref_repo, cust_repo)
        self.assertTrue(result.success)
        self.assertAlmostEqual(result.account.curr_bal, 0.0)


if __name__ == "__main__":
    unittest.main()
