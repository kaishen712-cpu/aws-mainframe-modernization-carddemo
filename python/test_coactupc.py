"""
Unit tests for coactupc.py — the Python translation of COACTUPC.CBL.

These tests verify the business rules for the Account Update function,
the largest and most complex program in the CardDemo application.
"""

import unittest

from coactvwc import (
    AccountRecord,
    CardXrefRecord,
    CustomerRecord,
    InMemoryAccountRepository,
    InMemoryCardXrefRepository,
    InMemoryCustomerRepository,
)
from coactupc import (
    AccountUpdateInput,
    detect_account_changes,
    get_header_info,
    lookup_account_for_update,
    update_account,
    validate_account_fields,
    validate_account_id,
    validate_active_status,
    validate_currency_field,
    validate_customer_name,
    validate_date_field,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_account() -> AccountRecord:
    """Return a sample account record for testing."""
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
    )


def _sample_xref() -> CardXrefRecord:
    """Return a sample cross-reference record."""
    return CardXrefRecord(
        card_num="4000123456789010",
        cust_id="000000001",
        acct_id="00000000001",
    )


def _make_repos():
    """Return pre-loaded repositories."""
    acct_repo = InMemoryAccountRepository()
    xref_repo = InMemoryCardXrefRepository()
    cust_repo = InMemoryCustomerRepository()
    acct_repo.add_account(_sample_account())
    xref_repo.add_xref(_sample_xref())
    cust_repo.add_customer(_sample_customer())
    return acct_repo, xref_repo, cust_repo


def _valid_update_input() -> AccountUpdateInput:
    """Return a valid update input that changes the active status."""
    return AccountUpdateInput(
        acct_id="00000000001",
        active_status="N",
        curr_bal="1500.75",
        credit_limit="10000.00",
        cash_credit_limit="5000.00",
        open_date="2020-01-15",
        expiration_date="2025-12-31",
        reissue_date="2024-06-01",
        curr_cyc_credit="500.00",
        curr_cyc_debit="200.00",
        group_id="GRP001",
    )


# ===========================================================================
# 1. Account ID validation
# ===========================================================================

class TestValidateAccountId(unittest.TestCase):
    """Tests for account ID validation."""

    def test_valid_id(self):
        result = validate_account_id("00000000001")
        self.assertTrue(result.is_valid)

    def test_short_numeric(self):
        result = validate_account_id("1")
        self.assertTrue(result.is_valid)

    def test_blank(self):
        result = validate_account_id("")
        self.assertFalse(result.is_valid)
        self.assertIn("Account number not provided", result.error_message)

    def test_spaces(self):
        result = validate_account_id("   ")
        self.assertFalse(result.is_valid)

    def test_asterisk(self):
        result = validate_account_id("*")
        self.assertFalse(result.is_valid)

    def test_non_numeric(self):
        result = validate_account_id("ABC")
        self.assertFalse(result.is_valid)
        self.assertIn("non zero 11 digit number", result.error_message)

    def test_all_zeros(self):
        result = validate_account_id("00000000000")
        self.assertFalse(result.is_valid)


# ===========================================================================
# 2. Active status validation
# ===========================================================================

class TestValidateActiveStatus(unittest.TestCase):
    """Tests for active status validation."""

    def test_Y_valid(self):
        self.assertTrue(validate_active_status("Y").is_valid)

    def test_N_valid(self):
        self.assertTrue(validate_active_status("N").is_valid)

    def test_lowercase_y_valid(self):
        self.assertTrue(validate_active_status("y").is_valid)

    def test_lowercase_n_valid(self):
        self.assertTrue(validate_active_status("n").is_valid)

    def test_invalid_value(self):
        result = validate_active_status("X")
        self.assertFalse(result.is_valid)
        self.assertIn("Account Active Status must be Y or N",
                       result.error_message)

    def test_blank(self):
        result = validate_active_status("")
        self.assertFalse(result.is_valid)

    def test_digit(self):
        result = validate_active_status("1")
        self.assertFalse(result.is_valid)


# ===========================================================================
# 3. Currency field validation
# ===========================================================================

class TestValidateCurrencyField(unittest.TestCase):
    """Tests for currency/numeric field validation."""

    def test_valid_number(self):
        result = validate_currency_field("10000.00", "credit_limit",
                                         "Credit Limit")
        self.assertTrue(result.is_valid)

    def test_valid_with_commas(self):
        result = validate_currency_field("10,000.00", "credit_limit",
                                         "Credit Limit")
        self.assertTrue(result.is_valid)

    def test_valid_negative(self):
        result = validate_currency_field("-500.00", "credit_limit",
                                         "Credit Limit")
        self.assertTrue(result.is_valid)

    def test_blank(self):
        result = validate_currency_field("", "credit_limit", "Credit Limit")
        self.assertFalse(result.is_valid)
        self.assertIn("Credit Limit must be supplied", result.error_message)

    def test_non_numeric(self):
        result = validate_currency_field("ABC", "credit_limit",
                                         "Credit Limit")
        self.assertFalse(result.is_valid)
        self.assertIn("Credit Limit is not valid", result.error_message)

    def test_spaces_only(self):
        result = validate_currency_field("   ", "credit_limit",
                                         "Credit Limit")
        self.assertFalse(result.is_valid)


# ===========================================================================
# 4. Date field validation
# ===========================================================================

class TestValidateDateField(unittest.TestCase):
    """Tests for date field validation."""

    def test_valid_date(self):
        result = validate_date_field("2025-12-31", "expiration_date",
                                     "expiration date")
        self.assertTrue(result.is_valid)

    def test_blank(self):
        result = validate_date_field("", "expiration_date",
                                     "expiration date")
        self.assertFalse(result.is_valid)
        self.assertIn("must be supplied", result.error_message)

    def test_wrong_format(self):
        result = validate_date_field("12/31/2025", "expiration_date",
                                     "expiration date")
        self.assertFalse(result.is_valid)
        self.assertIn("expected YYYY-MM-DD", result.error_message)

    def test_invalid_calendar_date(self):
        result = validate_date_field("2025-02-30", "expiration_date",
                                     "expiration date")
        self.assertFalse(result.is_valid)

    def test_invalid_month(self):
        result = validate_date_field("2025-13-01", "expiration_date",
                                     "expiration date")
        self.assertFalse(result.is_valid)

    def test_leap_year_valid(self):
        result = validate_date_field("2024-02-29", "expiration_date",
                                     "expiration date")
        self.assertTrue(result.is_valid)


# ===========================================================================
# 5. Customer name validation
# ===========================================================================

class TestValidateCustomerName(unittest.TestCase):
    """Tests for customer name validation."""

    def test_valid_name(self):
        result = validate_customer_name("JOHN", "Last name")
        self.assertTrue(result.is_valid)

    def test_name_with_spaces(self):
        result = validate_customer_name("JOHN DOE", "Last name")
        self.assertTrue(result.is_valid)

    def test_blank_name(self):
        result = validate_customer_name("", "Last name")
        self.assertFalse(result.is_valid)
        self.assertIn("not provided", result.error_message)

    def test_name_with_numbers(self):
        result = validate_customer_name("JOHN123", "Last name")
        self.assertFalse(result.is_valid)
        self.assertIn("alphabets and spaces", result.error_message)

    def test_name_with_special_chars(self):
        result = validate_customer_name("JOHN@DOE", "Last name")
        self.assertFalse(result.is_valid)


# ===========================================================================
# 6. Combined account field validation
# ===========================================================================

class TestValidateAccountFields(unittest.TestCase):
    """Tests for full account field validation."""

    def test_valid_input(self):
        inp = _valid_update_input()
        result = validate_account_fields(inp)
        self.assertTrue(result.is_valid)

    def test_invalid_status(self):
        inp = _valid_update_input()
        inp.active_status = "X"
        result = validate_account_fields(inp)
        self.assertFalse(result.is_valid)
        self.assertIn("Active Status", result.error_message)

    def test_invalid_credit_limit(self):
        inp = _valid_update_input()
        inp.credit_limit = "ABC"
        result = validate_account_fields(inp)
        self.assertFalse(result.is_valid)
        self.assertIn("Credit Limit", result.error_message)

    def test_invalid_cash_credit_limit(self):
        inp = _valid_update_input()
        inp.cash_credit_limit = ""
        result = validate_account_fields(inp)
        self.assertFalse(result.is_valid)
        self.assertIn("Cash Credit Limit", result.error_message)

    def test_invalid_expiration_date(self):
        inp = _valid_update_input()
        inp.expiration_date = "2025-13-01"
        result = validate_account_fields(inp)
        self.assertFalse(result.is_valid)

    def test_invalid_reissue_date(self):
        inp = _valid_update_input()
        inp.reissue_date = "not-a-date"
        result = validate_account_fields(inp)
        self.assertFalse(result.is_valid)


# ===========================================================================
# 7. Change detection
# ===========================================================================

class TestDetectAccountChanges(unittest.TestCase):
    """Tests for change detection logic."""

    def test_no_changes(self):
        old = _sample_account()
        inp = AccountUpdateInput(
            active_status="Y",
            credit_limit="10000.00",
            cash_credit_limit="5000.00",
            expiration_date="2025-12-31",
            reissue_date="2024-06-01",
            group_id="GRP001",
        )
        changes = detect_account_changes(old, inp)
        self.assertEqual(len(changes), 0)

    def test_status_change(self):
        old = _sample_account()
        inp = AccountUpdateInput(
            active_status="N",
            credit_limit="10000.00",
            cash_credit_limit="5000.00",
            expiration_date="2025-12-31",
            reissue_date="2024-06-01",
            group_id="GRP001",
        )
        changes = detect_account_changes(old, inp)
        self.assertIn("active_status", changes)
        self.assertEqual(changes["active_status"], ("Y", "N"))

    def test_multiple_changes(self):
        old = _sample_account()
        inp = AccountUpdateInput(
            active_status="N",
            credit_limit="20000.00",
            cash_credit_limit="5000.00",
            expiration_date="2025-12-31",
            reissue_date="2024-06-01",
            group_id="GRP002",
        )
        changes = detect_account_changes(old, inp)
        self.assertIn("active_status", changes)
        self.assertIn("credit_limit", changes)
        self.assertIn("group_id", changes)

    def test_blank_new_value_not_a_change(self):
        old = _sample_account()
        inp = AccountUpdateInput(
            active_status="Y",
            credit_limit="",
            cash_credit_limit="",
            expiration_date="",
            reissue_date="",
            group_id="",
        )
        changes = detect_account_changes(old, inp)
        self.assertEqual(len(changes), 0)


# ===========================================================================
# 8. Lookup account for update
# ===========================================================================

class TestLookupAccountForUpdate(unittest.TestCase):
    """Tests for the initial account lookup flow."""

    def test_successful_lookup(self):
        acct_repo, xref_repo, cust_repo = _make_repos()
        result = lookup_account_for_update("1", acct_repo, xref_repo,
                                           cust_repo)
        self.assertTrue(result.success)

    def test_invalid_id(self):
        acct_repo, xref_repo, cust_repo = _make_repos()
        result = lookup_account_for_update("ABC", acct_repo, xref_repo,
                                           cust_repo)
        self.assertFalse(result.success)

    def test_not_in_xref(self):
        acct_repo, xref_repo, cust_repo = _make_repos()
        result = lookup_account_for_update("99999999999", acct_repo,
                                           xref_repo, cust_repo)
        self.assertFalse(result.success)
        self.assertIn("account card xref", result.message)

    def test_not_in_master(self):
        acct_repo = InMemoryAccountRepository()
        xref_repo = InMemoryCardXrefRepository()
        cust_repo = InMemoryCustomerRepository()
        xref_repo.add_xref(CardXrefRecord(
            card_num="4000000000000002",
            cust_id="000000002",
            acct_id="00000000002",
        ))
        result = lookup_account_for_update("2", acct_repo, xref_repo,
                                           cust_repo)
        self.assertFalse(result.success)
        self.assertIn("account master file", result.message)

    def test_customer_not_found(self):
        acct_repo = InMemoryAccountRepository()
        xref_repo = InMemoryCardXrefRepository()
        cust_repo = InMemoryCustomerRepository()
        acct_repo.add_account(AccountRecord(acct_id="00000000003"))
        xref_repo.add_xref(CardXrefRecord(
            card_num="4000000000000003",
            cust_id="999999999",
            acct_id="00000000003",
        ))
        result = lookup_account_for_update("3", acct_repo, xref_repo,
                                           cust_repo)
        self.assertFalse(result.success)
        self.assertIn("customer in master file", result.message)


# ===========================================================================
# 9. Full update workflow
# ===========================================================================

class TestUpdateAccount(unittest.TestCase):
    """End-to-end tests for the update_account function."""

    def test_successful_update_with_confirmation(self):
        acct_repo, _, _ = _make_repos()
        old = _sample_account()
        inp = _valid_update_input()  # changes status to N
        result = update_account("00000000001", inp, old, acct_repo,
                                confirmed=True)
        self.assertTrue(result.success)
        self.assertIn("committed", result.info_message)
        # Verify the record was updated
        updated = acct_repo.get_account("00000000001")
        self.assertEqual(updated.active_status, "N")

    def test_needs_confirmation(self):
        acct_repo, _, _ = _make_repos()
        old = _sample_account()
        inp = _valid_update_input()
        result = update_account("00000000001", inp, old, acct_repo,
                                confirmed=False)
        self.assertFalse(result.success)
        self.assertTrue(result.needs_confirmation)
        self.assertIn("F5 to save", result.info_message)

    def test_no_changes_detected(self):
        acct_repo, _, _ = _make_repos()
        old = _sample_account()
        inp = AccountUpdateInput(
            active_status="Y",
            credit_limit="10000.00",
            cash_credit_limit="5000.00",
            expiration_date="2025-12-31",
            reissue_date="2024-06-01",
            group_id="GRP001",
        )
        result = update_account("00000000001", inp, old, acct_repo,
                                confirmed=True)
        self.assertFalse(result.success)
        self.assertIn("No change detected", result.message)

    def test_validation_error(self):
        acct_repo, _, _ = _make_repos()
        old = _sample_account()
        inp = _valid_update_input()
        inp.active_status = "X"
        result = update_account("00000000001", inp, old, acct_repo,
                                confirmed=True)
        self.assertFalse(result.success)
        self.assertIn("Active Status", result.message)

    def test_credit_limit_change(self):
        acct_repo, _, _ = _make_repos()
        old = _sample_account()
        inp = _valid_update_input()
        inp.active_status = "Y"
        inp.credit_limit = "20000.00"
        result = update_account("00000000001", inp, old, acct_repo,
                                confirmed=True)
        self.assertTrue(result.success)
        updated = acct_repo.get_account("00000000001")
        self.assertAlmostEqual(updated.credit_limit, 20000.00)


# ===========================================================================
# 10. Header info
# ===========================================================================

class TestGetHeaderInfo(unittest.TestCase):
    """Tests for screen header information."""

    def test_program_name(self):
        info = get_header_info()
        self.assertEqual(info["program_name"], "COACTUPC")

    def test_transaction_id(self):
        info = get_header_info()
        self.assertEqual(info["transaction_id"], "CAUP")


if __name__ == "__main__":
    unittest.main()
