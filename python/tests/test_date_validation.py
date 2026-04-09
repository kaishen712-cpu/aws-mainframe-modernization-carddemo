"""
Unit tests for date validation utilities.

Covers valid dates, invalid formats, leap years, future dates,
century boundaries, and edge cases.
"""

from datetime import date

from python.utils.date_validation import (
    validate_year,
    validate_month,
    validate_day,
    validate_day_month_year,
    validate_date_ccyymmdd,
    is_valid_calendar_date,
    validate_date_of_birth,
)


# ===================================================================
# validate_year
# ===================================================================

class TestValidateYear:
    """Tests for validate_year (EDIT-YEAR-CCYY)."""

    def test_valid_20th_century(self) -> None:
        result = validate_year("1999")
        assert result.is_valid is True

    def test_valid_21st_century(self) -> None:
        result = validate_year("2024")
        assert result.is_valid is True

    def test_blank_year(self) -> None:
        result = validate_year("")
        assert result.is_valid is False
        assert result.year_flag == "B"

    def test_spaces_year(self) -> None:
        result = validate_year("    ")
        assert result.is_valid is False
        assert result.year_flag == "B"

    def test_non_numeric_year(self) -> None:
        result = validate_year("ABCD")
        assert result.is_valid is False
        assert result.year_flag == "0"

    def test_invalid_century_18(self) -> None:
        result = validate_year("1899")
        assert result.is_valid is False
        assert result.year_flag == "0"

    def test_invalid_century_21(self) -> None:
        result = validate_year("2100")
        assert result.is_valid is False
        assert result.year_flag == "0"

    def test_short_year(self) -> None:
        result = validate_year("99")
        assert result.is_valid is False

    def test_boundary_1900(self) -> None:
        result = validate_year("1900")
        assert result.is_valid is True

    def test_boundary_2099(self) -> None:
        result = validate_year("2099")
        assert result.is_valid is True


# ===================================================================
# validate_month
# ===================================================================

class TestValidateMonth:
    """Tests for validate_month (EDIT-MONTH)."""

    def test_valid_january(self) -> None:
        assert validate_month("01").is_valid is True

    def test_valid_december(self) -> None:
        assert validate_month("12").is_valid is True

    def test_blank_month(self) -> None:
        result = validate_month("")
        assert result.is_valid is False
        assert result.month_flag == "B"

    def test_month_zero(self) -> None:
        result = validate_month("00")
        assert result.is_valid is False
        assert result.month_flag == "0"

    def test_month_13(self) -> None:
        result = validate_month("13")
        assert result.is_valid is False
        assert result.month_flag == "0"

    def test_non_numeric(self) -> None:
        result = validate_month("AB")
        assert result.is_valid is False
        assert result.month_flag == "0"


# ===================================================================
# validate_day
# ===================================================================

class TestValidateDay:
    """Tests for validate_day (EDIT-DAY)."""

    def test_valid_day_1(self) -> None:
        assert validate_day("01").is_valid is True

    def test_valid_day_31(self) -> None:
        assert validate_day("31").is_valid is True

    def test_blank_day(self) -> None:
        result = validate_day("")
        assert result.is_valid is False
        assert result.day_flag == "B"

    def test_day_zero(self) -> None:
        result = validate_day("00")
        assert result.is_valid is False
        assert result.day_flag == "0"

    def test_day_32(self) -> None:
        result = validate_day("32")
        assert result.is_valid is False
        assert result.day_flag == "0"

    def test_non_numeric(self) -> None:
        result = validate_day("XY")
        assert result.is_valid is False
        assert result.day_flag == "0"


# ===================================================================
# validate_day_month_year
# ===================================================================

class TestValidateDayMonthYear:
    """Tests for validate_day_month_year (EDIT-DAY-MONTH-YEAR)."""

    def test_valid_date(self) -> None:
        assert validate_day_month_year(2024, 3, 15).is_valid is True

    def test_31_days_in_30_day_month(self) -> None:
        result = validate_day_month_year(2024, 4, 31)
        assert result.is_valid is False
        assert "31 days" in result.error_message

    def test_30_days_in_february(self) -> None:
        result = validate_day_month_year(2024, 2, 30)
        assert result.is_valid is False
        assert "30 days" in result.error_message

    def test_29_feb_leap_year(self) -> None:
        assert validate_day_month_year(2024, 2, 29).is_valid is True

    def test_29_feb_non_leap_year(self) -> None:
        result = validate_day_month_year(2023, 2, 29)
        assert result.is_valid is False
        assert "leap year" in result.error_message.lower()

    def test_29_feb_century_non_leap(self) -> None:
        result = validate_day_month_year(1900, 2, 29)
        assert result.is_valid is False

    def test_29_feb_century_leap(self) -> None:
        assert validate_day_month_year(2000, 2, 29).is_valid is True

    def test_31_jan(self) -> None:
        assert validate_day_month_year(2024, 1, 31).is_valid is True

    def test_31_mar(self) -> None:
        assert validate_day_month_year(2024, 3, 31).is_valid is True

    def test_31_jun(self) -> None:
        result = validate_day_month_year(2024, 6, 31)
        assert result.is_valid is False

    def test_28_feb_any_year(self) -> None:
        assert validate_day_month_year(2023, 2, 28).is_valid is True


# ===================================================================
# validate_date_ccyymmdd
# ===================================================================

class TestValidateDateCCYYMMDD:
    """Tests for validate_date_ccyymmdd (full pipeline)."""

    def test_valid_date(self) -> None:
        assert validate_date_ccyymmdd("20240315").is_valid is True

    def test_valid_date_with_field_name(self) -> None:
        result = validate_date_ccyymmdd("20240315", "Open Date")
        assert result.is_valid is True

    def test_empty_string(self) -> None:
        result = validate_date_ccyymmdd("")
        assert result.is_valid is False

    def test_too_short(self) -> None:
        result = validate_date_ccyymmdd("202403")
        assert result.is_valid is False

    def test_too_long(self) -> None:
        result = validate_date_ccyymmdd("202403151")
        assert result.is_valid is False

    def test_invalid_century(self) -> None:
        result = validate_date_ccyymmdd("18990101")
        assert result.is_valid is False

    def test_invalid_month(self) -> None:
        result = validate_date_ccyymmdd("20241301")
        assert result.is_valid is False

    def test_invalid_day(self) -> None:
        result = validate_date_ccyymmdd("20240332")
        assert result.is_valid is False

    def test_feb_29_leap(self) -> None:
        assert validate_date_ccyymmdd("20240229").is_valid is True

    def test_feb_29_non_leap(self) -> None:
        result = validate_date_ccyymmdd("20230229")
        assert result.is_valid is False

    def test_error_message_includes_field_name(self) -> None:
        result = validate_date_ccyymmdd("20241301", "Expiry Date")
        assert "Expiry Date" in result.error_message


# ===================================================================
# is_valid_calendar_date
# ===================================================================

class TestIsValidCalendarDate:
    """Tests for the is_valid_calendar_date convenience wrapper."""

    def test_valid(self) -> None:
        assert is_valid_calendar_date("20240101") is True

    def test_invalid(self) -> None:
        assert is_valid_calendar_date("20241301") is False

    def test_empty(self) -> None:
        assert is_valid_calendar_date("") is False


# ===================================================================
# validate_date_of_birth
# ===================================================================

class TestValidateDateOfBirth:
    """Tests for validate_date_of_birth (EDIT-DATE-OF-BIRTH)."""

    def test_past_date(self) -> None:
        result = validate_date_of_birth("19900515")
        assert result.is_valid is True

    def test_today(self) -> None:
        today = date.today()
        date_str = f"{today.year:04d}{today.month:02d}{today.day:02d}"
        result = validate_date_of_birth(date_str)
        assert result.is_valid is True

    def test_future_date(self) -> None:
        result = validate_date_of_birth("20991231")
        assert result.is_valid is False
        assert "future" in result.error_message.lower()

    def test_invalid_date_format(self) -> None:
        result = validate_date_of_birth("BADDATE!")
        assert result.is_valid is False

    def test_field_name_in_message(self) -> None:
        result = validate_date_of_birth("20991231", "Customer DOB")
        assert "Customer DOB" in result.error_message
