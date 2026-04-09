"""
Unit tests for corpt00c.py — the Python translation of CORPT00C.CBL.

These tests verify the same business rules that the original COBOL program
enforces, organised by functional area.
"""

import calendar
import unittest
from datetime import date

from corpt00c import (
    clear_all_fields,
    get_header_info,
    process_report_request,
    validate_confirmation,
    validate_date,
    validate_date_range,
)


# ===========================================================================
# 1. Date validation (replaces CSUTLDTC subroutine)
# ===========================================================================

class TestValidateDate(unittest.TestCase):
    """Tests for individual date validation."""

    def test_valid_date(self):
        is_valid, yyyymmdd = validate_date("2024", "06", "15")
        self.assertTrue(is_valid)
        self.assertEqual(yyyymmdd, "20240615")

    def test_valid_leap_day(self):
        is_valid, yyyymmdd = validate_date("2024", "02", "29")
        self.assertTrue(is_valid)
        self.assertEqual(yyyymmdd, "20240229")

    def test_invalid_leap_day(self):
        is_valid, _ = validate_date("2023", "02", "29")
        self.assertFalse(is_valid)

    def test_invalid_month_zero(self):
        is_valid, _ = validate_date("2024", "00", "15")
        self.assertFalse(is_valid)

    def test_invalid_month_thirteen(self):
        is_valid, _ = validate_date("2024", "13", "15")
        self.assertFalse(is_valid)

    def test_invalid_day_zero(self):
        is_valid, _ = validate_date("2024", "06", "00")
        self.assertFalse(is_valid)

    def test_invalid_day_32(self):
        is_valid, _ = validate_date("2024", "01", "32")
        self.assertFalse(is_valid)

    def test_non_numeric_year(self):
        is_valid, _ = validate_date("ABCD", "06", "15")
        self.assertFalse(is_valid)

    def test_non_numeric_month(self):
        is_valid, _ = validate_date("2024", "XX", "15")
        self.assertFalse(is_valid)

    def test_non_numeric_day(self):
        is_valid, _ = validate_date("2024", "06", "XX")
        self.assertFalse(is_valid)

    def test_empty_fields(self):
        is_valid, _ = validate_date("", "", "")
        self.assertFalse(is_valid)

    def test_january_31(self):
        is_valid, yyyymmdd = validate_date("2024", "01", "31")
        self.assertTrue(is_valid)
        self.assertEqual(yyyymmdd, "20240131")

    def test_april_30(self):
        is_valid, _ = validate_date("2024", "04", "30")
        self.assertTrue(is_valid)

    def test_april_31_invalid(self):
        is_valid, _ = validate_date("2024", "04", "31")
        self.assertFalse(is_valid)


# ===========================================================================
# 2. Date range validation
# ===========================================================================

class TestValidateDateRange(unittest.TestCase):
    """Tests for date range validation."""

    def test_valid_range(self):
        is_valid, err = validate_date_range("20240101", "20240630")
        self.assertTrue(is_valid)
        self.assertEqual(err, "")

    def test_same_dates(self):
        is_valid, err = validate_date_range("20240615", "20240615")
        self.assertTrue(is_valid)

    def test_inverted_range(self):
        is_valid, err = validate_date_range("20240630", "20240101")
        self.assertFalse(is_valid)
        self.assertIn("Start date must not be after end date", err)


# ===========================================================================
# 3. Confirmation validation
# ===========================================================================

class TestValidateConfirmation(unittest.TestCase):
    """Tests for confirmation flag validation."""

    def test_Y_is_confirmed(self):
        status, err = validate_confirmation("Y")
        self.assertEqual(status, "confirmed")

    def test_y_is_confirmed(self):
        status, err = validate_confirmation("y")
        self.assertEqual(status, "confirmed")

    def test_N_is_cancelled(self):
        status, err = validate_confirmation("N")
        self.assertEqual(status, "cancelled")

    def test_n_is_cancelled(self):
        status, err = validate_confirmation("n")
        self.assertEqual(status, "cancelled")

    def test_blank_is_pending(self):
        status, err = validate_confirmation("")
        self.assertEqual(status, "pending")

    def test_spaces_is_pending(self):
        status, err = validate_confirmation("   ")
        self.assertEqual(status, "pending")

    def test_invalid_value(self):
        status, err = validate_confirmation("X")
        self.assertEqual(status, "invalid")
        self.assertIn('"X"', err)
        self.assertIn("not a valid value", err)


# ===========================================================================
# 4. Monthly report
# ===========================================================================

class TestMonthlyReport(unittest.TestCase):
    """Tests for monthly report requests."""

    def test_monthly_confirmed(self):
        result = process_report_request(monthly="M", confirm="Y")
        self.assertTrue(result.success)
        self.assertIn("Monthly", result.message)
        self.assertIn("submitted", result.message)
        self.assertIsNotNone(result.request)
        self.assertEqual(result.request.report_type, "Monthly")
        self.assertTrue(result.request.confirmed)

        # Date range should be current month (1st to last day)
        today = date.today()
        last_day = calendar.monthrange(today.year, today.month)[1]
        expected_start = f"{today.year:04d}{today.month:02d}01"
        expected_end = f"{today.year:04d}{today.month:02d}{last_day:02d}"
        self.assertEqual(result.request.start_date, expected_start)
        self.assertEqual(result.request.end_date, expected_end)

    def test_monthly_lowercase(self):
        result = process_report_request(monthly="m", confirm="Y")
        self.assertTrue(result.success)

    def test_monthly_pending(self):
        result = process_report_request(monthly="M", confirm="")
        self.assertFalse(result.success)
        self.assertIn("confirm", result.message.lower())
        self.assertIn("Monthly", result.message)

    def test_monthly_cancelled(self):
        result = process_report_request(monthly="M", confirm="N")
        self.assertFalse(result.success)
        self.assertEqual(result.message, "")


# ===========================================================================
# 5. Yearly report
# ===========================================================================

class TestYearlyReport(unittest.TestCase):
    """Tests for yearly report requests."""

    def test_yearly_confirmed(self):
        result = process_report_request(yearly="Y", confirm="Y")
        self.assertTrue(result.success)
        self.assertIn("Yearly", result.message)
        self.assertIsNotNone(result.request)
        self.assertEqual(result.request.report_type, "Yearly")

        # Date range should be full current year (Jan 1 to Dec 31)
        today = date.today()
        expected_start = f"{today.year:04d}0101"
        expected_end = f"{today.year:04d}1231"
        self.assertEqual(result.request.start_date, expected_start)
        self.assertEqual(result.request.end_date, expected_end)

    def test_yearly_lowercase(self):
        result = process_report_request(yearly="y", confirm="Y")
        self.assertTrue(result.success)

    def test_yearly_pending(self):
        result = process_report_request(yearly="Y", confirm="")
        self.assertFalse(result.success)
        self.assertIn("confirm", result.message.lower())


# ===========================================================================
# 6. Custom report
# ===========================================================================

class TestCustomReport(unittest.TestCase):
    """Tests for custom date-range report requests."""

    def test_custom_confirmed(self):
        result = process_report_request(
            custom="C",
            start_year="2024", start_month="01", start_day="01",
            end_year="2024", end_month="06", end_day="30",
            confirm="Y",
        )
        self.assertTrue(result.success)
        self.assertIn("Custom", result.message)
        self.assertEqual(result.request.start_date, "20240101")
        self.assertEqual(result.request.end_date, "20240630")

    def test_custom_lowercase(self):
        result = process_report_request(
            custom="c",
            start_year="2024", start_month="03", start_day="15",
            end_year="2024", end_month="03", end_day="31",
            confirm="Y",
        )
        self.assertTrue(result.success)

    def test_custom_invalid_start_date(self):
        result = process_report_request(
            custom="C",
            start_year="2024", start_month="13", start_day="01",
            end_year="2024", end_month="06", end_day="30",
            confirm="Y",
        )
        self.assertFalse(result.success)
        self.assertIn("Start Date", result.message)

    def test_custom_invalid_end_date(self):
        result = process_report_request(
            custom="C",
            start_year="2024", start_month="01", start_day="01",
            end_year="2024", end_month="02", end_day="30",
            confirm="Y",
        )
        self.assertFalse(result.success)
        self.assertIn("End Date", result.message)

    def test_custom_inverted_range(self):
        result = process_report_request(
            custom="C",
            start_year="2024", start_month="06", start_day="30",
            end_year="2024", end_month="01", end_day="01",
            confirm="Y",
        )
        self.assertFalse(result.success)
        self.assertIn("Start date must not be after end date", result.message)

    def test_custom_same_date(self):
        result = process_report_request(
            custom="C",
            start_year="2024", start_month="06", start_day="15",
            end_year="2024", end_month="06", end_day="15",
            confirm="Y",
        )
        self.assertTrue(result.success)

    def test_custom_pending(self):
        result = process_report_request(
            custom="C",
            start_year="2024", start_month="01", start_day="01",
            end_year="2024", end_month="06", end_day="30",
            confirm="",
        )
        self.assertFalse(result.success)
        self.assertIn("confirm", result.message.lower())
        self.assertIsNotNone(result.request)
        self.assertFalse(result.request.confirmed)


# ===========================================================================
# 7. No report type selected
# ===========================================================================

class TestNoReportType(unittest.TestCase):
    """Tests for missing report type."""

    def test_no_selection(self):
        result = process_report_request(confirm="Y")
        self.assertFalse(result.success)
        self.assertIn("Select a report type", result.message)

    def test_empty_strings(self):
        result = process_report_request(
            monthly="", yearly="", custom="", confirm="Y"
        )
        self.assertFalse(result.success)
        self.assertIn("Select a report type", result.message)

    def test_invalid_selection_letter(self):
        result = process_report_request(monthly="X", confirm="Y")
        self.assertFalse(result.success)
        self.assertIn("Select a report type", result.message)


# ===========================================================================
# 8. Confirmation edge cases
# ===========================================================================

class TestConfirmationEdgeCases(unittest.TestCase):
    """Tests for confirmation edge cases in report workflow."""

    def test_invalid_confirmation_value(self):
        result = process_report_request(monthly="M", confirm="X")
        self.assertFalse(result.success)
        self.assertIn('"X"', result.message)
        self.assertIn("not a valid value", result.message)

    def test_confirmation_with_spaces(self):
        result = process_report_request(monthly="M", confirm="  Y  ")
        self.assertTrue(result.success)


# ===========================================================================
# 9. Clear fields and header
# ===========================================================================

class TestClearAndHeader(unittest.TestCase):
    """Tests for clear fields and header helpers."""

    def test_clear_returns_blank(self):
        fields = clear_all_fields()
        expected_keys = [
            "monthly", "yearly", "custom",
            "start_month", "start_day", "start_year",
            "end_month", "end_day", "end_year",
            "confirm",
        ]
        for key in expected_keys:
            self.assertIn(key, fields)
            self.assertEqual(fields[key], "")

    def test_header_contains_required_fields(self):
        info = get_header_info()
        self.assertEqual(info["program_name"], "CORPT00C")
        self.assertEqual(info["transaction_id"], "CR00")
        self.assertIn("title01", info)
        self.assertIn("current_date", info)
        self.assertIn("current_time", info)


# ===========================================================================
# 10. Edge cases
# ===========================================================================

class TestEdgeCases(unittest.TestCase):
    """Edge case tests."""

    def test_leap_year_custom_report(self):
        result = process_report_request(
            custom="C",
            start_year="2024", start_month="02", start_day="29",
            end_year="2024", end_month="02", end_day="29",
            confirm="Y",
        )
        self.assertTrue(result.success)
        self.assertEqual(result.request.start_date, "20240229")

    def test_non_leap_year_feb_29(self):
        result = process_report_request(
            custom="C",
            start_year="2023", start_month="02", start_day="29",
            end_year="2023", end_month="03", end_day="01",
            confirm="Y",
        )
        self.assertFalse(result.success)
        self.assertIn("Start Date", result.message)

    def test_custom_non_numeric_dates(self):
        result = process_report_request(
            custom="C",
            start_year="ABCD", start_month="EF", start_day="GH",
            end_year="2024", end_month="06", end_day="30",
            confirm="Y",
        )
        self.assertFalse(result.success)
        self.assertIn("Start Date", result.message)


if __name__ == "__main__":
    unittest.main()
