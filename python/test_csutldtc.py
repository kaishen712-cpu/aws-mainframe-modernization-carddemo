"""
Unit tests for csutldtc.py — the Python translation of CSUTLDTC.CBL.

These tests verify date validation logic equivalent to the IBM LE
CEEDAYS service used in the original COBOL subroutine.
"""

import unittest

from csutldtc import (
    DateValidationResult,
    format_validation_message,
    validate_date,
)


# ===========================================================================
# 1. Valid dates
# ===========================================================================

class TestValidDates(unittest.TestCase):
    """Dates that should pass validation (severity 0)."""

    def test_valid_date_yyyy_mm_dd(self) -> None:
        result = validate_date("2024-06-15", "YYYY-MM-DD")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.severity, 0)
        self.assertEqual(result.result_text, "Date is valid")

    def test_valid_date_yyyymmdd(self) -> None:
        result = validate_date("20240615", "YYYYMMDD")
        self.assertTrue(result.is_valid)

    def test_valid_date_mm_dd_yyyy(self) -> None:
        result = validate_date("06/15/2024", "MM/DD/YYYY")
        self.assertTrue(result.is_valid)

    def test_valid_date_dd_mm_yyyy(self) -> None:
        result = validate_date("15/06/2024", "DD/MM/YYYY")
        self.assertTrue(result.is_valid)

    def test_leap_year_feb_29(self) -> None:
        result = validate_date("2024-02-29", "YYYY-MM-DD")
        self.assertTrue(result.is_valid)

    def test_jan_31(self) -> None:
        result = validate_date("2024-01-31", "YYYY-MM-DD")
        self.assertTrue(result.is_valid)

    def test_dec_31(self) -> None:
        result = validate_date("2024-12-31", "YYYY-MM-DD")
        self.assertTrue(result.is_valid)

    def test_first_day_of_year(self) -> None:
        result = validate_date("2024-01-01", "YYYY-MM-DD")
        self.assertTrue(result.is_valid)

    def test_year_2000(self) -> None:
        result = validate_date("2000-02-29", "YYYY-MM-DD")
        self.assertTrue(result.is_valid)

    def test_mmddyyyy_format(self) -> None:
        result = validate_date("06152024", "MMDDYYYY")
        self.assertTrue(result.is_valid)

    def test_ddmmyyyy_format(self) -> None:
        result = validate_date("15062024", "DDMMYYYY")
        self.assertTrue(result.is_valid)


# ===========================================================================
# 2. Invalid dates — bad calendar values
# ===========================================================================

class TestInvalidCalendarDates(unittest.TestCase):
    """Dates with valid format but invalid calendar values."""

    def test_feb_30(self) -> None:
        result = validate_date("2024-02-30", "YYYY-MM-DD")
        self.assertFalse(result.is_valid)
        self.assertGreater(result.severity, 0)
        self.assertEqual(result.result_text, "Datevalue error")

    def test_feb_29_non_leap_year(self) -> None:
        result = validate_date("2023-02-29", "YYYY-MM-DD")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.result_text, "Datevalue error")

    def test_month_13(self) -> None:
        result = validate_date("2024-13-01", "YYYY-MM-DD")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.result_text, "Invalid month")

    def test_month_00(self) -> None:
        result = validate_date("2024-00-15", "YYYY-MM-DD")
        self.assertFalse(result.is_valid)

    def test_day_32(self) -> None:
        result = validate_date("2024-01-32", "YYYY-MM-DD")
        self.assertFalse(result.is_valid)

    def test_day_00(self) -> None:
        result = validate_date("2024-01-00", "YYYY-MM-DD")
        self.assertFalse(result.is_valid)

    def test_apr_31(self) -> None:
        """April has only 30 days."""
        result = validate_date("2024-04-31", "YYYY-MM-DD")
        self.assertFalse(result.is_valid)

    def test_jun_31(self) -> None:
        """June has only 30 days."""
        result = validate_date("2024-06-31", "YYYY-MM-DD")
        self.assertFalse(result.is_valid)

    def test_century_not_leap(self) -> None:
        """1900 is not a leap year (divisible by 100 but not 400)."""
        result = validate_date("1900-02-29", "YYYY-MM-DD")
        self.assertFalse(result.is_valid)


# ===========================================================================
# 3. Invalid dates — non-numeric data
# ===========================================================================

class TestNonNumericDates(unittest.TestCase):
    """Dates with non-numeric characters where digits are expected."""

    def test_letters_in_date(self) -> None:
        result = validate_date("ABCD-EF-GH", "YYYY-MM-DD")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.result_text, "Nonnumeric data")

    def test_partial_letters(self) -> None:
        result = validate_date("2024-0A-15", "YYYY-MM-DD")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.result_text, "Nonnumeric data")


# ===========================================================================
# 4. Empty / missing inputs
# ===========================================================================

class TestEmptyInputs(unittest.TestCase):
    """Tests for empty or blank input values."""

    def test_empty_date_string(self) -> None:
        result = validate_date("", "YYYY-MM-DD")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.result_text, "Insufficient")

    def test_blank_date_string(self) -> None:
        result = validate_date("          ", "YYYY-MM-DD")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.result_text, "Insufficient")

    def test_empty_format_string(self) -> None:
        result = validate_date("2024-06-15", "")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.result_text, "Bad Pic String")

    def test_unsupported_format(self) -> None:
        result = validate_date("2024-06-15", "DD-MMM-YYYY")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.result_text, "Bad Pic String")


# ===========================================================================
# 5. Result structure
# ===========================================================================

class TestResultStructure(unittest.TestCase):
    """Tests for the DateValidationResult dataclass."""

    def test_valid_result_fields(self) -> None:
        result = validate_date("2024-06-15", "YYYY-MM-DD")
        self.assertEqual(result.severity, 0)
        self.assertEqual(result.msg_no, 0)
        self.assertEqual(result.date_tested, "2024-06-15")
        self.assertEqual(result.date_format_used, "YYYY-MM-DD")

    def test_invalid_result_has_severity(self) -> None:
        result = validate_date("2024-02-30", "YYYY-MM-DD")
        self.assertEqual(result.severity, 3)
        self.assertGreater(result.msg_no, 0)

    def test_is_valid_property(self) -> None:
        valid = DateValidationResult(severity=0)
        invalid = DateValidationResult(severity=3)
        self.assertTrue(valid.is_valid)
        self.assertFalse(invalid.is_valid)


# ===========================================================================
# 6. Format validation message
# ===========================================================================

class TestFormatValidationMessage(unittest.TestCase):
    """Tests for the COBOL-compatible message formatting."""

    def test_valid_date_message(self) -> None:
        result = validate_date("2024-06-15", "YYYY-MM-DD")
        msg = format_validation_message(result)
        self.assertEqual(len(msg), 80)
        self.assertIn("0000", msg)
        self.assertIn("Date is valid", msg)
        self.assertIn("2024-06-15", msg)
        self.assertIn("YYYY-MM-DD", msg)

    def test_invalid_date_message(self) -> None:
        result = validate_date("2024-02-30", "YYYY-MM-DD")
        msg = format_validation_message(result)
        self.assertEqual(len(msg), 80)
        self.assertIn("0003", msg[:4])  # severity
        self.assertIn("Datevalue error", msg)

    def test_message_contains_mesg_code(self) -> None:
        result = validate_date("2024-06-15", "YYYY-MM-DD")
        msg = format_validation_message(result)
        self.assertIn("Mesg Code:", msg)

    def test_message_contains_test_date(self) -> None:
        result = validate_date("2024-06-15", "YYYY-MM-DD")
        msg = format_validation_message(result)
        self.assertIn("TstDate:", msg)

    def test_message_contains_mask(self) -> None:
        result = validate_date("2024-06-15", "YYYY-MM-DD")
        msg = format_validation_message(result)
        self.assertIn("Mask used:", msg)


# ===========================================================================
# 7. Edge cases
# ===========================================================================

class TestEdgeCases(unittest.TestCase):
    """Edge cases and boundary conditions."""

    def test_whitespace_padded_date(self) -> None:
        """Date with leading/trailing spaces should still validate."""
        result = validate_date("  2024-06-15  ", "YYYY-MM-DD")
        self.assertTrue(result.is_valid)

    def test_format_case_insensitive(self) -> None:
        """Format mask should be case-insensitive."""
        result = validate_date("2024-06-15", "yyyy-mm-dd")
        self.assertTrue(result.is_valid)

    def test_yyyymmdd_compact(self) -> None:
        result = validate_date("20240229", "YYYYMMDD")
        self.assertTrue(result.is_valid)

    def test_yyyymmdd_invalid(self) -> None:
        result = validate_date("20240230", "YYYYMMDD")
        self.assertFalse(result.is_valid)

    def test_slash_format_valid(self) -> None:
        result = validate_date("2024/06/15", "YYYY/MM/DD")
        self.assertTrue(result.is_valid)

    def test_slash_format_invalid(self) -> None:
        result = validate_date("2024/13/15", "YYYY/MM/DD")
        self.assertFalse(result.is_valid)


if __name__ == "__main__":
    unittest.main()
