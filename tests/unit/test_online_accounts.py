"""
Unit tests for Phase 3 — Account Management (accounts_mgmt app).

Tests cover:
- Form validation (dates, numeric, SSN, phone, state, zip, FICO)
- Change detection (only changed fields are updated)
- Business rule validation edge cases
- View @login_required enforcement
- Account detail view displays all fields
- Account update view processes changes

All test data is SYNTHETIC — never uses real customer data.
Account numbers are never logged in plain text (CPS 234 compliance).

Coverage target: 70% for standard functions.
"""

from __future__ import annotations

import os
import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Django test setup — must come before any Django imports
# ---------------------------------------------------------------------------
_python_root = Path(__file__).resolve().parent.parent.parent / "python"
if str(_python_root) not in sys.path:
    sys.path.insert(0, str(_python_root))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "carddemo_site.settings")

import django

django.setup()

from django.contrib.auth.models import User
from django.test import TestCase

from accounts_mgmt.forms import (
    AccountSearchForm,
    AccountUpdateForm,
    _validate_alpha_required,
    _validate_fico_score,
    _validate_phone_number,
    _validate_signed_decimal,
    _validate_ssn,
    _validate_state_and_zip,
    _validate_yes_no,
)
from accounts_mgmt.models import Account, CardXref, Customer
from accounts_mgmt.services import (
    ChangeSet,
    UpdateResult,
    _to_decimal,
    apply_account_updates,
    detect_changes,
    lookup_account_with_customer,
)
from accounts_mgmt.views import _parse_phone


# ---------------------------------------------------------------------------
# Synthetic test data factory — never uses real customer data
# ---------------------------------------------------------------------------

def _make_account(**overrides) -> Account:
    """Create a synthetic Account instance for testing."""
    defaults = {
        "acct_id": "00000012345",
        "acct_active_status": "Y",
        "acct_curr_bal": Decimal("1500.00"),
        "acct_credit_limit": Decimal("5000.00"),
        "acct_cash_credit_limit": Decimal("2000.00"),
        "acct_open_date": "2020-01-15",
        "acct_expiration_date": "2025-01-15",
        "acct_reissue_date": "",
        "acct_curr_cyc_credit": Decimal("200.00"),
        "acct_curr_cyc_debit": Decimal("100.00"),
        "acct_group_id": "GRP001",
    }
    defaults.update(overrides)
    return Account(**defaults)


def _make_customer(**overrides) -> Customer:
    """Create a synthetic Customer instance for testing."""
    defaults = {
        "cust_id": "000012345",
        "cust_first_name": "Jane",
        "cust_middle_name": "Marie",
        "cust_last_name": "Doe",
        "cust_addr_line_1": "123 Synthetic Street",
        "cust_addr_line_2": "Suite 100",
        "cust_addr_line_3": "Testville",
        "cust_addr_state_cd": "CA",
        "cust_addr_country_cd": "US",
        "cust_addr_zip": "90210",
        "cust_phone_num_1": "(213)555-0100",
        "cust_phone_num_2": "",
        "cust_ssn": "123456789",
        "cust_govt_issued_id": "DL123456",
        "cust_dob_yyyy_mm_dd": "1985-06-15",
        "cust_eft_account_id": "EFT001",
        "cust_pri_card_holder_ind": "Y",
        "cust_fico_credit_score": "750",
    }
    defaults.update(overrides)
    return Customer(**defaults)


def _make_valid_form_data(**overrides) -> dict:
    """Create a complete valid form data dict for AccountUpdateForm."""
    defaults = {
        "acct_active_status": "Y",
        "acct_credit_limit": "5000.00",
        "acct_cash_credit_limit": "2000.00",
        "acct_curr_bal": "1500.00",
        "acct_curr_cyc_credit": "200.00",
        "acct_curr_cyc_debit": "100.00",
        "acct_open_date": "2020-01-15",
        "acct_expiration_date": "2025-01-15",
        "acct_reissue_date": "",
        "acct_group_id": "GRP001",
        "cust_first_name": "Jane",
        "cust_middle_name": "Marie",
        "cust_last_name": "Doe",
        "cust_addr_line_1": "123 Synthetic Street",
        "cust_addr_line_2": "Suite 100",
        "cust_addr_line_3": "Testville",
        "cust_addr_state_cd": "CA",
        "cust_addr_country_cd": "US",
        "cust_addr_zip": "90210",
        "cust_phone_num_1_area": "213",
        "cust_phone_num_1_prefix": "555",
        "cust_phone_num_1_line": "0100",
        "cust_phone_num_2_area": "",
        "cust_phone_num_2_prefix": "",
        "cust_phone_num_2_line": "",
        "cust_ssn": "123456789",
        "cust_govt_issued_id": "DL123456",
        "cust_dob": "1985-06-15",
        "cust_eft_account_id": "EFT001",
        "cust_pri_card_holder_ind": "Y",
        "cust_fico_credit_score": "750",
    }
    defaults.update(overrides)
    return defaults


# ===========================================================================
# Form validation tests
# ===========================================================================


class TestYesNoValidation(TestCase):
    """Tests for _validate_yes_no (COACTUPC 1220-EDIT-YESNO)."""

    def test_valid_y(self) -> None:
        self.assertIsNone(_validate_yes_no("Y", "Status"))

    def test_valid_n(self) -> None:
        self.assertIsNone(_validate_yes_no("N", "Status"))

    def test_valid_lowercase(self) -> None:
        self.assertIsNone(_validate_yes_no("y", "Status"))

    def test_invalid_value(self) -> None:
        result = _validate_yes_no("X", "Status")
        self.assertIsNotNone(result)
        self.assertIn("Y or N", result)


class TestSignedDecimalValidation(TestCase):
    """Tests for _validate_signed_decimal (COACTUPC 1250-EDIT-SIGNED-9V2)."""

    def test_valid_positive(self) -> None:
        self.assertIsNone(_validate_signed_decimal("5000.00", "Limit"))

    def test_valid_negative(self) -> None:
        self.assertIsNone(_validate_signed_decimal("-100.50", "Balance"))

    def test_valid_with_comma(self) -> None:
        self.assertIsNone(_validate_signed_decimal("5,000.00", "Limit"))

    def test_valid_with_dollar(self) -> None:
        self.assertIsNone(_validate_signed_decimal("$5000", "Limit"))

    def test_empty_fails(self) -> None:
        result = _validate_signed_decimal("", "Limit")
        self.assertIsNotNone(result)
        self.assertIn("must be supplied", result)

    def test_non_numeric_fails(self) -> None:
        result = _validate_signed_decimal("abc", "Limit")
        self.assertIsNotNone(result)
        self.assertIn("not valid", result)


class TestAlphaRequiredValidation(TestCase):
    """Tests for _validate_alpha_required (COACTUPC 1225-EDIT-ALPHA-REQD)."""

    def test_valid_alpha(self) -> None:
        self.assertIsNone(_validate_alpha_required("Jane", "First Name"))

    def test_valid_with_spaces(self) -> None:
        self.assertIsNone(_validate_alpha_required("Mary Ann", "Name"))

    def test_empty_fails(self) -> None:
        result = _validate_alpha_required("", "First Name")
        self.assertIsNotNone(result)

    def test_numeric_fails(self) -> None:
        result = _validate_alpha_required("Jane123", "First Name")
        self.assertIsNotNone(result)
        self.assertIn("alphabets only", result)


class TestSSNValidation(TestCase):
    """Tests for _validate_ssn (COACTUPC 1265-EDIT-US-SSN)."""

    def test_valid_ssn(self) -> None:
        self.assertIsNone(_validate_ssn("123456789"))

    def test_valid_with_dashes(self) -> None:
        self.assertIsNone(_validate_ssn("123-45-6789"))

    def test_too_short(self) -> None:
        result = _validate_ssn("12345")
        self.assertIsNotNone(result)
        self.assertIn("9 digits", result)

    def test_non_numeric(self) -> None:
        result = _validate_ssn("12345678A")
        self.assertIsNotNone(result)

    def test_area_000_invalid(self) -> None:
        """SSN area 000 is invalid per COBOL rules."""
        result = _validate_ssn("000456789")
        self.assertIsNotNone(result)
        self.assertIn("000", result)

    def test_area_666_invalid(self) -> None:
        """SSN area 666 is invalid per COBOL rules."""
        result = _validate_ssn("666456789")
        self.assertIsNotNone(result)
        self.assertIn("666", result)

    def test_area_900_range_invalid(self) -> None:
        """SSN area 900-999 is invalid per COBOL rules."""
        result = _validate_ssn("900456789")
        self.assertIsNotNone(result)
        self.assertIn("900", result)

    def test_area_999_invalid(self) -> None:
        result = _validate_ssn("999456789")
        self.assertIsNotNone(result)

    def test_group_00_invalid(self) -> None:
        """SSN group 00 is invalid per COBOL rules."""
        result = _validate_ssn("123006789")
        self.assertIsNotNone(result)
        self.assertIn("4th & 5th", result)

    def test_serial_0000_invalid(self) -> None:
        """SSN serial 0000 is invalid per COBOL rules."""
        result = _validate_ssn("123450000")
        self.assertIsNotNone(result)
        self.assertIn("Last 4", result)


class TestPhoneValidation(TestCase):
    """Tests for _validate_phone_number (COACTUPC 1260-EDIT-US-PHONE-NUM)."""

    def test_valid_phone(self) -> None:
        self.assertIsNone(
            _validate_phone_number("213", "555", "0100", "Phone 1")
        )

    def test_all_blank_is_valid(self) -> None:
        """Phone is optional per COBOL — all blank is accepted."""
        self.assertIsNone(
            _validate_phone_number("", "", "", "Phone 1")
        )

    def test_partial_area_only_fails(self) -> None:
        result = _validate_phone_number("213", "", "", "Phone 1")
        self.assertIsNotNone(result)
        self.assertIn("Prefix", result)

    def test_invalid_area_code(self) -> None:
        result = _validate_phone_number("000", "555", "0100", "Phone 1")
        self.assertIsNotNone(result)
        self.assertIn("zero", result)

    def test_non_numeric_area(self) -> None:
        result = _validate_phone_number("abc", "555", "0100", "Phone 1")
        self.assertIsNotNone(result)
        self.assertIn("3 digit", result)

    def test_invalid_prefix_zero(self) -> None:
        result = _validate_phone_number("213", "000", "0100", "Phone 1")
        self.assertIsNotNone(result)
        self.assertIn("Prefix", result)

    def test_invalid_line_zero(self) -> None:
        result = _validate_phone_number("213", "555", "0000", "Phone 1")
        self.assertIsNotNone(result)
        self.assertIn("Line number", result)

    def test_area_code_not_in_lookup(self) -> None:
        """Area code not in VALID_PHONE_AREA_CODES lookup."""
        result = _validate_phone_number("001", "555", "0100", "Phone 1")
        self.assertIsNotNone(result)
        self.assertIn("area code", result.lower())


class TestFICOScoreValidation(TestCase):
    """Tests for _validate_fico_score (COACTUPC 1275-EDIT-FICO-SCORE)."""

    def test_valid_score_300(self) -> None:
        """Minimum valid FICO score."""
        self.assertIsNone(_validate_fico_score("300"))

    def test_valid_score_850(self) -> None:
        """Maximum valid FICO score."""
        self.assertIsNone(_validate_fico_score("850"))

    def test_valid_score_750(self) -> None:
        self.assertIsNone(_validate_fico_score("750"))

    def test_below_range_fails(self) -> None:
        """HARDCODED THRESHOLD: FICO must be >= 300."""
        result = _validate_fico_score("299")
        self.assertIsNotNone(result)
        self.assertIn("300", result)

    def test_above_range_fails(self) -> None:
        """HARDCODED THRESHOLD: FICO must be <= 850."""
        result = _validate_fico_score("851")
        self.assertIsNotNone(result)
        self.assertIn("850", result)

    def test_zero_fails(self) -> None:
        result = _validate_fico_score("000")
        self.assertIsNotNone(result)
        self.assertIn("zero", result)

    def test_empty_fails(self) -> None:
        result = _validate_fico_score("")
        self.assertIsNotNone(result)

    def test_non_numeric_fails(self) -> None:
        result = _validate_fico_score("abc")
        self.assertIsNotNone(result)
        self.assertIn("numeric", result)


class TestStateAndZipValidation(TestCase):
    """Tests for _validate_state_and_zip (COACTUPC 1270/1280)."""

    def test_valid_ca_90(self) -> None:
        self.assertIsNone(_validate_state_and_zip("CA", "90210"))

    def test_valid_ny_10(self) -> None:
        self.assertIsNone(_validate_state_and_zip("NY", "10001"))

    def test_blank_state_is_valid(self) -> None:
        """Empty state passes (field optional check at form level)."""
        self.assertIsNone(_validate_state_and_zip("", "90210"))

    def test_invalid_state_code(self) -> None:
        result = _validate_state_and_zip("XX", "90210")
        self.assertIsNotNone(result)
        self.assertIn("state code", result.lower())

    def test_invalid_state_zip_combo(self) -> None:
        """CA with NY zip prefix 10 should fail."""
        result = _validate_state_and_zip("CA", "10001")
        self.assertIsNotNone(result)
        self.assertIn("zip", result.lower())


# ===========================================================================
# Account search form tests
# ===========================================================================


class TestAccountSearchForm(TestCase):
    """Tests for AccountSearchForm (COACTVWC 2210-EDIT-ACCOUNT)."""

    def test_valid_11_digit_id(self) -> None:
        form = AccountSearchForm(data={"acct_id": "00000012345"})
        self.assertTrue(form.is_valid())

    def test_non_numeric_fails(self) -> None:
        form = AccountSearchForm(data={"acct_id": "0000001234A"})
        self.assertFalse(form.is_valid())

    def test_too_short_fails(self) -> None:
        form = AccountSearchForm(data={"acct_id": "12345"})
        self.assertFalse(form.is_valid())

    def test_all_zeros_fails(self) -> None:
        form = AccountSearchForm(data={"acct_id": "00000000000"})
        self.assertFalse(form.is_valid())

    def test_empty_fails(self) -> None:
        form = AccountSearchForm(data={"acct_id": ""})
        self.assertFalse(form.is_valid())


# ===========================================================================
# Account update form tests
# ===========================================================================


class TestAccountUpdateForm(TestCase):
    """Tests for AccountUpdateForm (COACTUPC full form validation)."""

    def test_valid_form(self) -> None:
        """Complete valid form data should pass all validation."""
        form = AccountUpdateForm(data=_make_valid_form_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_status(self) -> None:
        data = _make_valid_form_data(acct_active_status="X")
        form = AccountUpdateForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("acct_active_status", form.errors)

    def test_invalid_credit_limit(self) -> None:
        data = _make_valid_form_data(acct_credit_limit="abc")
        form = AccountUpdateForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("acct_credit_limit", form.errors)

    def test_invalid_ssn(self) -> None:
        data = _make_valid_form_data(cust_ssn="000456789")
        form = AccountUpdateForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("cust_ssn", form.errors)

    def test_invalid_fico(self) -> None:
        data = _make_valid_form_data(cust_fico_credit_score="100")
        form = AccountUpdateForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("cust_fico_credit_score", form.errors)

    def test_invalid_first_name_numeric(self) -> None:
        data = _make_valid_form_data(cust_first_name="Jane123")
        form = AccountUpdateForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("cust_first_name", form.errors)

    def test_invalid_phone_partial(self) -> None:
        """Partial phone number should fail cross-field validation."""
        data = _make_valid_form_data(
            cust_phone_num_1_area="213",
            cust_phone_num_1_prefix="",
            cust_phone_num_1_line="",
        )
        form = AccountUpdateForm(data=data)
        self.assertFalse(form.is_valid())

    def test_invalid_state_code(self) -> None:
        data = _make_valid_form_data(cust_addr_state_cd="XX")
        form = AccountUpdateForm(data=data)
        self.assertFalse(form.is_valid())

    def test_invalid_date(self) -> None:
        data = _make_valid_form_data(acct_open_date="2020-13-01")
        form = AccountUpdateForm(data=data)
        self.assertFalse(form.is_valid())

    def test_future_dob_invalid(self) -> None:
        """Date of birth in the future should fail."""
        data = _make_valid_form_data(cust_dob="2099-01-01")
        form = AccountUpdateForm(data=data)
        self.assertFalse(form.is_valid())

    def test_optional_middle_name_blank(self) -> None:
        """Middle name is optional — blank should pass."""
        data = _make_valid_form_data(cust_middle_name="")
        form = AccountUpdateForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_middle_name_numeric_invalid(self) -> None:
        data = _make_valid_form_data(cust_middle_name="Marie5")
        form = AccountUpdateForm(data=data)
        self.assertFalse(form.is_valid())

    def test_optional_phone_all_blank(self) -> None:
        """All phone fields blank should pass."""
        data = _make_valid_form_data(
            cust_phone_num_1_area="",
            cust_phone_num_1_prefix="",
            cust_phone_num_1_line="",
        )
        form = AccountUpdateForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)


# ===========================================================================
# Change detection tests
# ===========================================================================


class TestChangeDetection(TestCase):
    """Tests for change detection logic (COACTUPC 1205-COMPARE-OLD-NEW)."""

    def test_no_changes_detected(self) -> None:
        """Identical old and new data → no changes."""
        account = _make_account()
        customer = _make_customer()
        form_data = _make_valid_form_data()
        changes = detect_changes(account, customer, form_data)
        self.assertFalse(changes.has_changes)

    def test_credit_limit_change_detected(self) -> None:
        """Changed credit limit should appear in account_changes."""
        account = _make_account()
        customer = _make_customer()
        form_data = _make_valid_form_data(acct_credit_limit="7500.00")
        changes = detect_changes(account, customer, form_data)
        self.assertTrue(changes.has_changes)
        self.assertIn("acct_credit_limit", changes.account_changes)

    def test_customer_name_change_detected(self) -> None:
        """Changed customer name should appear in customer_changes."""
        account = _make_account()
        customer = _make_customer()
        form_data = _make_valid_form_data(cust_first_name="Alice")
        changes = detect_changes(account, customer, form_data)
        self.assertTrue(changes.has_changes)
        self.assertIn("cust_first_name", changes.customer_changes)

    def test_phone_change_detected(self) -> None:
        """Changed phone number should be detected."""
        account = _make_account()
        customer = _make_customer()
        form_data = _make_valid_form_data(
            cust_phone_num_1_area="310",
            cust_phone_num_1_prefix="555",
            cust_phone_num_1_line="0200",
        )
        changes = detect_changes(account, customer, form_data)
        self.assertTrue(changes.has_changes)
        self.assertIn("cust_phone_num_1", changes.customer_changes)

    def test_only_changed_fields_detected(self) -> None:
        """Only the specific changed fields should be in the set."""
        account = _make_account()
        customer = _make_customer()
        form_data = _make_valid_form_data(
            acct_active_status="N",
            acct_credit_limit="5000.00",  # Same value
        )
        changes = detect_changes(account, customer, form_data)
        self.assertIn("acct_active_status", changes.account_changes)
        self.assertNotIn("acct_credit_limit", changes.account_changes)

    def test_decimal_comparison_precision(self) -> None:
        """Decimal comparison should handle string vs Decimal correctly."""
        account = _make_account(acct_curr_bal=Decimal("1500.00"))
        customer = _make_customer()
        form_data = _make_valid_form_data(acct_curr_bal="1500.00")
        changes = detect_changes(account, customer, form_data)
        # Same value — should NOT be in changes
        self.assertNotIn("acct_curr_bal", changes.account_changes)

    def test_case_insensitive_string_compare(self) -> None:
        """String comparison should be case-insensitive (COBOL UPPER)."""
        account = _make_account(acct_group_id="GRP001")
        customer = _make_customer()
        form_data = _make_valid_form_data(acct_group_id="grp001")
        changes = detect_changes(account, customer, form_data)
        self.assertNotIn("acct_group_id", changes.account_changes)


# ===========================================================================
# Service layer tests
# ===========================================================================


class TestToDecimal(TestCase):
    """Tests for _to_decimal helper."""

    def test_string_conversion(self) -> None:
        self.assertEqual(_to_decimal("1500.00"), Decimal("1500.00"))

    def test_already_decimal(self) -> None:
        self.assertEqual(_to_decimal(Decimal("99.99")), Decimal("99.99"))

    def test_with_comma(self) -> None:
        self.assertEqual(_to_decimal("5,000.00"), Decimal("5000.00"))

    def test_with_dollar(self) -> None:
        self.assertEqual(_to_decimal("$100"), Decimal("100"))

    def test_invalid_returns_zero(self) -> None:
        self.assertEqual(_to_decimal("abc"), Decimal("0"))


class TestApplyAccountUpdates(TestCase):
    """Tests for apply_account_updates (COACTUPC 9600-WRITE-PROCESSING)."""

    def test_no_changes_returns_error(self) -> None:
        """When no fields changed, service returns error message."""
        account = _make_account()
        customer = _make_customer()
        account.save = MagicMock()
        customer.save = MagicMock()
        form_data = _make_valid_form_data()
        result = apply_account_updates(account, customer, form_data)
        self.assertFalse(result.success)
        self.assertIn("No change detected", result.error_message)
        account.save.assert_not_called()

    def test_successful_update(self) -> None:
        """Changed fields are saved successfully."""
        account = _make_account()
        customer = _make_customer()
        account.save = MagicMock()
        customer.save = MagicMock()
        form_data = _make_valid_form_data(acct_credit_limit="8000.00")
        result = apply_account_updates(account, customer, form_data)
        self.assertTrue(result.success)
        account.save.assert_called_once()
        # Credit limit should be updated to Decimal
        self.assertEqual(account.acct_credit_limit, Decimal("8000.00"))

    def test_save_failure_returns_error(self) -> None:
        """Database save failure returns error result."""
        account = _make_account()
        customer = _make_customer()
        account.save = MagicMock(side_effect=Exception("DB error"))
        customer.save = MagicMock()
        form_data = _make_valid_form_data(acct_credit_limit="8000.00")
        result = apply_account_updates(account, customer, form_data)
        self.assertFalse(result.success)
        self.assertIn("failed", result.error_message.lower())


class TestLookupAccountWithCustomer(TestCase):
    """Tests for lookup_account_with_customer (COACTVWC 9000-READ-ACCT)."""

    def test_account_not_found(self) -> None:
        account, customer, error = lookup_account_with_customer(
            "99999999999"
        )
        self.assertIsNone(account)
        self.assertIn("account master file", error.lower())

    def test_found_account_no_xref(self) -> None:
        """Account exists but no card xref → returns account + error."""
        Account.objects.create(
            acct_id="00000099999",
            acct_active_status="Y",
        )
        account, customer, error = lookup_account_with_customer(
            "00000099999"
        )
        self.assertIsNotNone(account)
        self.assertIsNone(customer)
        self.assertIn("xref", error.lower())

    def test_full_lookup_success(self) -> None:
        """Account + xref + customer all found."""
        Account.objects.create(
            acct_id="00000088888",
            acct_active_status="Y",
        )
        Customer.objects.create(
            cust_id="000088888",
            cust_first_name="Test",
            cust_last_name="User",
        )
        CardXref.objects.create(
            xref_card_num="1234567890123456",
            xref_cust_id="000088888",
            xref_acct_id="00000088888",
        )
        account, customer, error = lookup_account_with_customer(
            "00000088888"
        )
        self.assertIsNotNone(account)
        self.assertIsNotNone(customer)
        self.assertEqual(error, "")
        self.assertEqual(customer.cust_first_name, "Test")


# ===========================================================================
# Phone parsing tests
# ===========================================================================


class TestParsePhone(TestCase):
    """Tests for _parse_phone helper in views.py."""

    def test_standard_format(self) -> None:
        area, prefix, line = _parse_phone("(213)555-0100")
        self.assertEqual(area, "213")
        self.assertEqual(prefix, "555")
        self.assertEqual(line, "0100")

    def test_empty_string(self) -> None:
        area, prefix, line = _parse_phone("")
        self.assertEqual(area, "")

    def test_too_short(self) -> None:
        area, prefix, line = _parse_phone("12345")
        self.assertEqual(area, "")


# ===========================================================================
# View tests (login_required enforcement)
# ===========================================================================


class TestViewLoginRequired(TestCase):
    """Tests for @login_required enforcement on all views."""

    def test_search_requires_login(self) -> None:
        """Account search should redirect unauthenticated users."""
        response = self.client.get("/accounts/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_detail_requires_login(self) -> None:
        """Account detail should redirect unauthenticated users."""
        response = self.client.get("/accounts/00000012345/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_update_requires_login(self) -> None:
        """Account update should redirect unauthenticated users."""
        response = self.client.get("/accounts/00000012345/update/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_search_accessible_when_logged_in(self) -> None:
        """Authenticated user can access search page."""
        User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get("/accounts/")
        self.assertEqual(response.status_code, 200)


class TestAccountDetailView(TestCase):
    """Tests for account_detail view (COACTVWC)."""

    def setUp(self) -> None:
        self.user = User.objects.create_user(
            username="viewuser", password="testpass123"
        )
        self.client.login(username="viewuser", password="testpass123")
        self.account = Account.objects.create(
            acct_id="00000077777",
            acct_active_status="Y",
            acct_credit_limit=Decimal("10000.00"),
            acct_curr_bal=Decimal("2500.00"),
            acct_cash_credit_limit=Decimal("3000.00"),
            acct_open_date="2019-06-01",
            acct_expiration_date="2024-06-01",
            acct_curr_cyc_credit=Decimal("500.00"),
            acct_curr_cyc_debit=Decimal("150.00"),
            acct_group_id="GRP002",
        )
        self.customer = Customer.objects.create(
            cust_id="000077777",
            cust_first_name="Alice",
            cust_last_name="Smith",
            cust_addr_line_1="456 Test Ave",
            cust_addr_state_cd="NY",
            cust_addr_zip="10001",
            cust_phone_num_1="(212)555-0200",
            cust_ssn="987654321",
            cust_fico_credit_score="800",
            cust_dob_yyyy_mm_dd="1990-03-20",
        )
        CardXref.objects.create(
            xref_card_num="9876543210123456",
            xref_cust_id="000077777",
            xref_acct_id="00000077777",
        )

    def test_detail_displays_account_fields(self) -> None:
        """Detail view should display all account fields."""
        response = self.client.get("/accounts/00000077777/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("00000077777", content)
        self.assertIn("10000.00", content)
        self.assertIn("2500.00", content)
        self.assertIn("2019-06-01", content)

    def test_detail_displays_customer_fields(self) -> None:
        """Detail view should display customer fields."""
        response = self.client.get("/accounts/00000077777/")
        content = response.content.decode()
        self.assertIn("Alice", content)
        self.assertIn("Smith", content)
        self.assertIn("800", content)

    def test_detail_masks_ssn(self) -> None:
        """SSN should be partially masked (show last 4 only)."""
        response = self.client.get("/accounts/00000077777/")
        content = response.content.decode()
        # Should show masked SSN, not full 9 digits
        self.assertIn("4321", content)
        self.assertNotIn("987654321", content)

    def test_detail_not_found_redirects(self) -> None:
        """Non-existent account should redirect to search."""
        response = self.client.get("/accounts/99999999999/")
        self.assertEqual(response.status_code, 302)


class TestAccountUpdateView(TestCase):
    """Tests for account_update view (COACTUPC)."""

    def setUp(self) -> None:
        self.user = User.objects.create_user(
            username="updateuser", password="testpass123"
        )
        self.client.login(username="updateuser", password="testpass123")
        self.account = Account.objects.create(
            acct_id="00000066666",
            acct_active_status="Y",
            acct_credit_limit=Decimal("5000.00"),
            acct_curr_bal=Decimal("1000.00"),
            acct_cash_credit_limit=Decimal("2000.00"),
            acct_open_date="2020-01-15",
            acct_expiration_date="2025-01-15",
            acct_curr_cyc_credit=Decimal("200.00"),
            acct_curr_cyc_debit=Decimal("100.00"),
            acct_group_id="GRP001",
        )
        self.customer = Customer.objects.create(
            cust_id="000066666",
            cust_first_name="Jane",
            cust_middle_name="Marie",
            cust_last_name="Doe",
            cust_addr_line_1="123 Synthetic Street",
            cust_addr_line_2="Suite 100",
            cust_addr_line_3="Testville",
            cust_addr_state_cd="CA",
            cust_addr_country_cd="US",
            cust_addr_zip="90210",
            cust_phone_num_1="(213)555-0100",
            cust_ssn="123456789",
            cust_govt_issued_id="DL123456",
            cust_dob_yyyy_mm_dd="1985-06-15",
            cust_eft_account_id="EFT001",
            cust_pri_card_holder_ind="Y",
            cust_fico_credit_score="750",
        )
        CardXref.objects.create(
            xref_card_num="1111222233334444",
            xref_cust_id="000066666",
            xref_acct_id="00000066666",
        )

    def test_get_update_form(self) -> None:
        """GET request should render the update form."""
        response = self.client.get("/accounts/00000066666/update/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Account Update")

    def test_post_update_success(self) -> None:
        """POST with changed data should save and redirect."""
        data = _make_valid_form_data(acct_credit_limit="8000.00")
        response = self.client.post(
            "/accounts/00000066666/update/", data=data,
        )
        self.assertEqual(response.status_code, 302)
        self.account.refresh_from_db()
        self.assertEqual(
            self.account.acct_credit_limit, Decimal("8000.00"),
        )

    def test_post_invalid_data(self) -> None:
        """POST with invalid data should re-render form with errors."""
        data = _make_valid_form_data(cust_ssn="000456789")
        response = self.client.post(
            "/accounts/00000066666/update/", data=data,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "error")

    def test_update_not_found_redirects(self) -> None:
        """Non-existent account should redirect to search."""
        response = self.client.get("/accounts/99999999999/update/")
        self.assertEqual(response.status_code, 302)


# ===========================================================================
# ChangeSet / UpdateResult dataclass tests
# ===========================================================================


class TestChangeSetDataclass(TestCase):
    """Tests for ChangeSet and UpdateResult data structures."""

    def test_empty_changeset_has_no_changes(self) -> None:
        cs = ChangeSet()
        self.assertFalse(cs.has_changes)

    def test_changeset_with_account_changes(self) -> None:
        cs = ChangeSet(
            account_changes={"acct_credit_limit": ("5000", "8000")}
        )
        self.assertTrue(cs.has_changes)

    def test_changeset_with_customer_changes(self) -> None:
        cs = ChangeSet(
            customer_changes={"cust_first_name": ("Jane", "Alice")}
        )
        self.assertTrue(cs.has_changes)

    def test_update_result_defaults(self) -> None:
        result = UpdateResult()
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "")
        self.assertFalse(result.concurrent_modification)
