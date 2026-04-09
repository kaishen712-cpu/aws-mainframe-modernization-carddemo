"""
Unit tests for cocrdupc.py — the Python translation of COCRDUPC.CBL.

These tests verify the business rules for the Credit Card Update function
including validation, change detection, confirmation workflow, and updates.
"""

import unittest

from coactvwc import (
    CardRecord,
    InMemoryCardXrefRepository,
)
from cocrdlic import InMemoryCardRepository
from cocrdupc import (
    CardUpdateInput,
    detect_card_changes,
    get_header_info,
    lookup_card_for_update,
    update_card,
    validate_account_id,
    validate_card_number,
    validate_card_status,
    validate_card_update_fields,
    validate_embossed_name,
    validate_expiry_month,
    validate_expiry_year,
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


def _valid_update_input() -> CardUpdateInput:
    """Return a valid update input that changes the embossed name."""
    return CardUpdateInput(
        acct_id="00000000001",
        card_num="4000123456789010",
        embossed_name="JANE Q DOE",
        expiry_month="12",
        expiry_year="2025",
        active_status="Y",
    )


def _make_card_repo() -> InMemoryCardRepository:
    """Return a card repo pre-loaded with a sample card."""
    repo = InMemoryCardRepository()
    repo.add_card(_sample_card())
    return repo


# ===========================================================================
# 1. Account ID validation
# ===========================================================================

class TestValidateAccountId(unittest.TestCase):
    """Tests for account ID validation."""

    def test_valid(self):
        self.assertTrue(validate_account_id("00000000001").is_valid)

    def test_blank(self):
        result = validate_account_id("")
        self.assertFalse(result.is_valid)
        self.assertIn("Account ID not provided", result.error_message)

    def test_asterisk(self):
        self.assertFalse(validate_account_id("*").is_valid)

    def test_non_numeric(self):
        result = validate_account_id("ABC")
        self.assertFalse(result.is_valid)
        self.assertIn("11 digit number", result.error_message)

    def test_all_zeros(self):
        self.assertFalse(validate_account_id("00000000000").is_valid)


# ===========================================================================
# 2. Card number validation
# ===========================================================================

class TestValidateCardNumber(unittest.TestCase):
    """Tests for card number validation."""

    def test_valid(self):
        self.assertTrue(validate_card_number("4000123456789010").is_valid)

    def test_blank(self):
        result = validate_card_number("")
        self.assertFalse(result.is_valid)
        self.assertIn("Card number not provided", result.error_message)

    def test_non_numeric(self):
        result = validate_card_number("ABCDEF")
        self.assertFalse(result.is_valid)
        self.assertIn("16 digit number", result.error_message)

    def test_all_zeros(self):
        self.assertFalse(validate_card_number("0000000000000000").is_valid)


# ===========================================================================
# 3. Embossed name validation
# ===========================================================================

class TestValidateEmbossedName(unittest.TestCase):
    """Tests for embossed name validation."""

    def test_valid_name(self):
        self.assertTrue(validate_embossed_name("JOHN DOE").is_valid)

    def test_blank(self):
        result = validate_embossed_name("")
        self.assertFalse(result.is_valid)
        self.assertIn("Card holder name is required", result.error_message)

    def test_spaces_only(self):
        result = validate_embossed_name("   ")
        self.assertFalse(result.is_valid)

    def test_name_with_special_chars(self):
        """Special characters are allowed in embossed name."""
        self.assertTrue(validate_embossed_name("O'BRIEN").is_valid)


# ===========================================================================
# 4. Card status validation
# ===========================================================================

class TestValidateCardStatus(unittest.TestCase):
    """Tests for card status validation."""

    def test_Y_valid(self):
        self.assertTrue(validate_card_status("Y").is_valid)

    def test_N_valid(self):
        self.assertTrue(validate_card_status("N").is_valid)

    def test_lowercase_valid(self):
        self.assertTrue(validate_card_status("y").is_valid)

    def test_invalid(self):
        result = validate_card_status("X")
        self.assertFalse(result.is_valid)
        self.assertIn("Card status must be Y or N", result.error_message)

    def test_blank(self):
        self.assertFalse(validate_card_status("").is_valid)


# ===========================================================================
# 5. Expiry month validation
# ===========================================================================

class TestValidateExpiryMonth(unittest.TestCase):
    """Tests for expiry month validation."""

    def test_valid_month(self):
        self.assertTrue(validate_expiry_month("01").is_valid)

    def test_december(self):
        self.assertTrue(validate_expiry_month("12").is_valid)

    def test_single_digit(self):
        self.assertTrue(validate_expiry_month("1").is_valid)

    def test_blank(self):
        result = validate_expiry_month("")
        self.assertFalse(result.is_valid)
        self.assertIn("Expiry month is required", result.error_message)

    def test_non_numeric(self):
        result = validate_expiry_month("AB")
        self.assertFalse(result.is_valid)
        self.assertIn("numeric", result.error_message)

    def test_zero(self):
        result = validate_expiry_month("0")
        self.assertFalse(result.is_valid)
        self.assertIn("between 1 and 12", result.error_message)

    def test_thirteen(self):
        result = validate_expiry_month("13")
        self.assertFalse(result.is_valid)
        self.assertIn("between 1 and 12", result.error_message)


# ===========================================================================
# 6. Expiry year validation
# ===========================================================================

class TestValidateExpiryYear(unittest.TestCase):
    """Tests for expiry year validation."""

    def test_valid_year(self):
        self.assertTrue(validate_expiry_year("2025").is_valid)

    def test_blank(self):
        result = validate_expiry_year("")
        self.assertFalse(result.is_valid)
        self.assertIn("Expiry year is required", result.error_message)

    def test_non_numeric(self):
        result = validate_expiry_year("ABCD")
        self.assertFalse(result.is_valid)
        self.assertIn("numeric", result.error_message)

    def test_two_digit_year(self):
        result = validate_expiry_year("25")
        self.assertFalse(result.is_valid)
        self.assertIn("4-digit year", result.error_message)

    def test_too_small(self):
        result = validate_expiry_year("0999")
        self.assertFalse(result.is_valid)
        self.assertIn("Invalid", result.error_message)


# ===========================================================================
# 7. Combined field validation
# ===========================================================================

class TestValidateCardUpdateFields(unittest.TestCase):
    """Tests for full card field validation."""

    def test_valid_input(self):
        inp = _valid_update_input()
        result = validate_card_update_fields(inp)
        self.assertTrue(result.is_valid)

    def test_invalid_name(self):
        inp = _valid_update_input()
        inp.embossed_name = ""
        result = validate_card_update_fields(inp)
        self.assertFalse(result.is_valid)
        self.assertIn("name", result.error_message.lower())

    def test_invalid_status(self):
        inp = _valid_update_input()
        inp.active_status = "X"
        result = validate_card_update_fields(inp)
        self.assertFalse(result.is_valid)
        self.assertIn("status", result.error_message.lower())

    def test_invalid_month(self):
        inp = _valid_update_input()
        inp.expiry_month = "13"
        result = validate_card_update_fields(inp)
        self.assertFalse(result.is_valid)

    def test_invalid_year(self):
        inp = _valid_update_input()
        inp.expiry_year = "AB"
        result = validate_card_update_fields(inp)
        self.assertFalse(result.is_valid)


# ===========================================================================
# 8. Change detection
# ===========================================================================

class TestDetectCardChanges(unittest.TestCase):
    """Tests for change detection logic."""

    def test_no_changes(self):
        old = _sample_card()
        inp = CardUpdateInput(
            embossed_name="JOHN Q DOE",
            active_status="Y",
            expiry_month="12",
            expiry_year="2025",
        )
        changes = detect_card_changes(old, inp)
        self.assertEqual(len(changes), 0)

    def test_name_change(self):
        old = _sample_card()
        inp = CardUpdateInput(
            embossed_name="JANE Q DOE",
            active_status="Y",
            expiry_month="12",
            expiry_year="2025",
        )
        changes = detect_card_changes(old, inp)
        self.assertIn("embossed_name", changes)

    def test_status_change(self):
        old = _sample_card()
        inp = CardUpdateInput(
            embossed_name="JOHN Q DOE",
            active_status="N",
            expiry_month="12",
            expiry_year="2025",
        )
        changes = detect_card_changes(old, inp)
        self.assertIn("active_status", changes)
        self.assertEqual(changes["active_status"], ("Y", "N"))

    def test_month_change(self):
        old = _sample_card()
        inp = CardUpdateInput(
            embossed_name="JOHN Q DOE",
            active_status="Y",
            expiry_month="06",
            expiry_year="2025",
        )
        changes = detect_card_changes(old, inp)
        self.assertIn("expiry_month", changes)

    def test_year_change(self):
        old = _sample_card()
        inp = CardUpdateInput(
            embossed_name="JOHN Q DOE",
            active_status="Y",
            expiry_month="12",
            expiry_year="2026",
        )
        changes = detect_card_changes(old, inp)
        self.assertIn("expiry_year", changes)

    def test_case_insensitive_name(self):
        """Name comparison is case-insensitive per COBOL UPPER-CASE."""
        old = _sample_card()
        inp = CardUpdateInput(
            embossed_name="john q doe",
            active_status="Y",
            expiry_month="12",
            expiry_year="2025",
        )
        changes = detect_card_changes(old, inp)
        self.assertNotIn("embossed_name", changes)

    def test_blank_new_value_not_a_change(self):
        old = _sample_card()
        inp = CardUpdateInput(
            embossed_name="JOHN Q DOE",
            active_status="",
            expiry_month="",
            expiry_year="",
        )
        changes = detect_card_changes(old, inp)
        self.assertEqual(len(changes), 0)


# ===========================================================================
# 9. Lookup card for update
# ===========================================================================

class TestLookupCardForUpdate(unittest.TestCase):
    """Tests for the initial card lookup flow."""

    def test_successful_lookup(self):
        card_repo = _make_card_repo()
        xref_repo = InMemoryCardXrefRepository()
        result = lookup_card_for_update(
            "00000000001", "4000123456789010", card_repo, xref_repo,
        )
        self.assertTrue(result.success)

    def test_invalid_account_id(self):
        card_repo = _make_card_repo()
        xref_repo = InMemoryCardXrefRepository()
        result = lookup_card_for_update("ABC", "4000123456789010",
                                        card_repo, xref_repo)
        self.assertFalse(result.success)

    def test_invalid_card_number(self):
        card_repo = _make_card_repo()
        xref_repo = InMemoryCardXrefRepository()
        result = lookup_card_for_update("00000000001", "XYZ",
                                        card_repo, xref_repo)
        self.assertFalse(result.success)

    def test_card_not_found(self):
        card_repo = InMemoryCardRepository()
        xref_repo = InMemoryCardXrefRepository()
        result = lookup_card_for_update(
            "00000000001", "9999999999999999", card_repo, xref_repo,
        )
        self.assertFalse(result.success)
        self.assertIn("Did not find", result.message)


# ===========================================================================
# 10. Full update workflow
# ===========================================================================

class TestUpdateCard(unittest.TestCase):
    """End-to-end tests for the update_card function."""

    def test_successful_update_with_confirmation(self):
        card_repo = _make_card_repo()
        old = _sample_card()
        inp = _valid_update_input()
        result = update_card("4000123456789010", inp, old, card_repo,
                             confirmed=True)
        self.assertTrue(result.success)
        self.assertIn("committed", result.info_message)
        # Verify the record was updated
        updated = card_repo.get_card("4000123456789010")
        self.assertEqual(updated.embossed_name, "JANE Q DOE")

    def test_needs_confirmation(self):
        card_repo = _make_card_repo()
        old = _sample_card()
        inp = _valid_update_input()
        result = update_card("4000123456789010", inp, old, card_repo,
                             confirmed=False)
        self.assertFalse(result.success)
        self.assertTrue(result.needs_confirmation)
        self.assertIn("F5 to confirm", result.info_message)

    def test_no_changes(self):
        card_repo = _make_card_repo()
        old = _sample_card()
        inp = CardUpdateInput(
            embossed_name="JOHN Q DOE",
            active_status="Y",
            expiry_month="12",
            expiry_year="2025",
        )
        result = update_card("4000123456789010", inp, old, card_repo,
                             confirmed=True)
        self.assertFalse(result.success)
        self.assertIn("No changes detected", result.message)

    def test_validation_error(self):
        card_repo = _make_card_repo()
        old = _sample_card()
        inp = _valid_update_input()
        inp.embossed_name = ""
        result = update_card("4000123456789010", inp, old, card_repo,
                             confirmed=True)
        self.assertFalse(result.success)
        self.assertIn("name", result.message.lower())

    def test_status_update(self):
        card_repo = _make_card_repo()
        old = _sample_card()
        inp = _valid_update_input()
        inp.embossed_name = "JOHN Q DOE"
        inp.active_status = "N"
        result = update_card("4000123456789010", inp, old, card_repo,
                             confirmed=True)
        self.assertTrue(result.success)
        updated = card_repo.get_card("4000123456789010")
        self.assertEqual(updated.active_status, "N")


# ===========================================================================
# 11. Header info
# ===========================================================================

class TestGetHeaderInfo(unittest.TestCase):
    """Tests for screen header information."""

    def test_program_name(self):
        info = get_header_info()
        self.assertEqual(info["program_name"], "COCRDUPC")

    def test_transaction_id(self):
        info = get_header_info()
        self.assertEqual(info["transaction_id"], "CCUP")


if __name__ == "__main__":
    unittest.main()
