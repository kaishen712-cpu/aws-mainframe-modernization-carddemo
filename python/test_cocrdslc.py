"""
Unit tests for cocrdslc.py — the Python translation of COCRDSLC.CBL.

These tests verify the business rules for the Credit Card View function
(read-only card details display).
"""

import unittest

from coactvwc import (
    AccountRecord,
    CardRecord,
    CardXrefRecord,
    CustomerRecord,
    InMemoryAccountRepository,
    InMemoryCardXrefRepository,
    InMemoryCustomerRepository,
)
from cocrdlic import InMemoryCardRepository
from cocrdslc import (
    get_header_info,
    validate_account_id,
    validate_card_number,
    view_card_details,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_card() -> CardRecord:
    """Return a sample card record."""
    return CardRecord(
        card_num="4000123456789010",
        acct_id="00000000001",
        cvv_cd="123",
        embossed_name="JOHN Q DOE",
        expiration_date="2025-12-31",
        active_status="Y",
    )


def _sample_account() -> AccountRecord:
    """Return a sample account record."""
    return AccountRecord(
        acct_id="00000000001",
        active_status="Y",
        curr_bal=1500.75,
        credit_limit=10000.00,
    )


def _sample_customer() -> CustomerRecord:
    """Return a sample customer record."""
    return CustomerRecord(
        cust_id="000000001",
        first_name="JOHN",
        middle_name="Q",
        last_name="DOE",
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
    card_repo = InMemoryCardRepository()
    acct_repo = InMemoryAccountRepository()
    xref_repo = InMemoryCardXrefRepository()
    cust_repo = InMemoryCustomerRepository()

    card_repo.add_card(_sample_card())
    acct_repo.add_account(_sample_account())
    xref_repo.add_xref(_sample_xref())
    cust_repo.add_customer(_sample_customer())

    return card_repo, acct_repo, xref_repo, cust_repo


# ===========================================================================
# 1. Account ID validation
# ===========================================================================

class TestValidateAccountId(unittest.TestCase):
    """Tests for account ID validation."""

    def test_valid_numeric(self):
        result = validate_account_id("00000000001")
        self.assertTrue(result.is_valid)

    def test_blank(self):
        result = validate_account_id("")
        self.assertFalse(result.is_valid)
        self.assertIn("Account ID not provided", result.error_message)

    def test_asterisk(self):
        result = validate_account_id("*")
        self.assertFalse(result.is_valid)

    def test_non_numeric(self):
        result = validate_account_id("ABC")
        self.assertFalse(result.is_valid)
        self.assertIn("11 digit number", result.error_message)

    def test_all_zeros(self):
        result = validate_account_id("00000000000")
        self.assertFalse(result.is_valid)


# ===========================================================================
# 2. Card number validation
# ===========================================================================

class TestValidateCardNumber(unittest.TestCase):
    """Tests for card number validation."""

    def test_valid_numeric(self):
        result = validate_card_number("4000123456789010")
        self.assertTrue(result.is_valid)

    def test_blank(self):
        result = validate_card_number("")
        self.assertFalse(result.is_valid)
        self.assertIn("Card number not provided", result.error_message)

    def test_asterisk(self):
        result = validate_card_number("*")
        self.assertFalse(result.is_valid)

    def test_non_numeric(self):
        result = validate_card_number("ABCDEF")
        self.assertFalse(result.is_valid)
        self.assertIn("16 digit number", result.error_message)

    def test_all_zeros(self):
        result = validate_card_number("0000000000000000")
        self.assertFalse(result.is_valid)


# ===========================================================================
# 3. Full view card details workflow
# ===========================================================================

class TestViewCardDetails(unittest.TestCase):
    """End-to-end tests for the view_card_details function."""

    def test_successful_view_by_card_number(self):
        """Happy path: card number provided, returns all data."""
        card_repo, acct_repo, xref_repo, cust_repo = _make_repos()
        result = view_card_details(
            "00000000001", "4000123456789010",
            card_repo, acct_repo, xref_repo, cust_repo,
        )
        self.assertTrue(result.success)
        self.assertIsNotNone(result.card)
        self.assertIsNotNone(result.account)
        self.assertIsNotNone(result.customer)
        self.assertEqual(result.card.embossed_name, "JOHN Q DOE")

    def test_successful_view_by_account_id(self):
        """Account ID provided but no card number — finds card via xref."""
        card_repo, acct_repo, xref_repo, cust_repo = _make_repos()
        result = view_card_details(
            "1", "",
            card_repo, acct_repo, xref_repo, cust_repo,
        )
        self.assertTrue(result.success)
        self.assertIsNotNone(result.card)

    def test_neither_provided(self):
        """Both account ID and card number blank."""
        card_repo, acct_repo, xref_repo, cust_repo = _make_repos()
        result = view_card_details(
            "", "",
            card_repo, acct_repo, xref_repo, cust_repo,
        )
        self.assertFalse(result.success)
        self.assertIn("provide account ID", result.message)

    def test_card_not_found(self):
        """Card number not in card file."""
        card_repo, acct_repo, xref_repo, cust_repo = _make_repos()
        result = view_card_details(
            "00000000001", "9999999999999999",
            card_repo, acct_repo, xref_repo, cust_repo,
        )
        self.assertFalse(result.success)
        self.assertIn("Did not find", result.message)

    def test_account_not_in_xref(self):
        """Account provided but not in xref, card number blank."""
        card_repo = InMemoryCardRepository()
        acct_repo = InMemoryAccountRepository()
        xref_repo = InMemoryCardXrefRepository()
        cust_repo = InMemoryCustomerRepository()
        result = view_card_details(
            "99999999999", "",
            card_repo, acct_repo, xref_repo, cust_repo,
        )
        self.assertFalse(result.success)
        self.assertIn("card xref", result.message)

    def test_card_found_but_no_customer(self):
        """Card found but customer record missing (graceful handling)."""
        card_repo = InMemoryCardRepository()
        acct_repo = InMemoryAccountRepository()
        xref_repo = InMemoryCardXrefRepository()
        cust_repo = InMemoryCustomerRepository()

        card_repo.add_card(CardRecord(
            card_num="4000000000000099",
            acct_id="00000000099",
            embossed_name="UNKNOWN",
        ))
        result = view_card_details(
            "00000000099", "4000000000000099",
            card_repo, acct_repo, xref_repo, cust_repo,
        )
        # Card found even if customer/account not found
        self.assertTrue(result.success)
        self.assertIsNotNone(result.card)
        self.assertIsNone(result.customer)

    def test_result_contains_card_details(self):
        """Verify all card fields are accessible on success."""
        card_repo, acct_repo, xref_repo, cust_repo = _make_repos()
        result = view_card_details(
            "1", "4000123456789010",
            card_repo, acct_repo, xref_repo, cust_repo,
        )
        self.assertTrue(result.success)
        self.assertEqual(result.card.card_num, "4000123456789010")
        self.assertEqual(result.card.active_status, "Y")
        self.assertEqual(result.card.cvv_cd, "123")
        self.assertEqual(result.card.expiration_date, "2025-12-31")

    def test_result_contains_account_details(self):
        """Verify account details are accessible on success."""
        card_repo, acct_repo, xref_repo, cust_repo = _make_repos()
        result = view_card_details(
            "1", "4000123456789010",
            card_repo, acct_repo, xref_repo, cust_repo,
        )
        self.assertTrue(result.success)
        self.assertIsNotNone(result.account)
        self.assertEqual(result.account.acct_id, "00000000001")
        self.assertAlmostEqual(result.account.credit_limit, 10000.00)


# ===========================================================================
# 4. Header info
# ===========================================================================

class TestGetHeaderInfo(unittest.TestCase):
    """Tests for screen header information."""

    def test_program_name(self):
        info = get_header_info()
        self.assertEqual(info["program_name"], "COCRDSLC")

    def test_transaction_id(self):
        info = get_header_info()
        self.assertEqual(info["transaction_id"], "CCDL")

    def test_contains_titles(self):
        info = get_header_info()
        self.assertIn("AWS Mainframe Modernization", info["title01"])
        self.assertIn("CardDemo", info["title02"])


if __name__ == "__main__":
    unittest.main()
