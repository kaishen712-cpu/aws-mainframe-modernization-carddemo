"""
Unit tests for string utilities and lookup codes.
"""

from python.utils.string_utils import (
    left_trim,
    right_trim,
    trim,
    pad_right,
    pad_left,
    safe_numeric,
    safe_decimal,
    format_amount,
)
from python.utils.lookup_codes import (
    VALID_US_STATE_CODES,
    VALID_PHONE_AREA_CODES,
    is_valid_us_state_code,
    is_valid_us_state_zip_combo,
    is_valid_phone_area_code,
)


# ===================================================================
# String Utilities
# ===================================================================

class TestLeftTrim:
    """Tests for left_trim."""

    def test_leading_spaces(self) -> None:
        assert left_trim("   hello") == "hello"

    def test_no_leading_spaces(self) -> None:
        assert left_trim("hello") == "hello"

    def test_trailing_preserved(self) -> None:
        assert left_trim("   hello   ") == "hello   "

    def test_empty_string(self) -> None:
        assert left_trim("") == ""

    def test_all_spaces(self) -> None:
        assert left_trim("     ") == ""


class TestRightTrim:
    """Tests for right_trim."""

    def test_trailing_spaces(self) -> None:
        assert right_trim("hello   ") == "hello"

    def test_no_trailing_spaces(self) -> None:
        assert right_trim("hello") == "hello"

    def test_leading_preserved(self) -> None:
        assert right_trim("   hello   ") == "   hello"

    def test_empty_string(self) -> None:
        assert right_trim("") == ""


class TestTrim:
    """Tests for trim."""

    def test_both_sides(self) -> None:
        assert trim("  hello  ") == "hello"

    def test_no_whitespace(self) -> None:
        assert trim("hello") == "hello"

    def test_empty_string(self) -> None:
        assert trim("") == ""


class TestPadRight:
    """Tests for pad_right."""

    def test_shorter_string(self) -> None:
        assert pad_right("hello", 10) == "hello     "

    def test_exact_length(self) -> None:
        assert pad_right("hello", 5) == "hello"

    def test_longer_string_truncated(self) -> None:
        assert pad_right("hello world", 5) == "hello"

    def test_custom_fill_char(self) -> None:
        assert pad_right("hi", 5, "*") == "hi***"


class TestPadLeft:
    """Tests for pad_left."""

    def test_shorter_string(self) -> None:
        assert pad_left("42", 5) == "00042"

    def test_exact_length(self) -> None:
        assert pad_left("12345", 5) == "12345"

    def test_longer_string_truncated_from_left(self) -> None:
        assert pad_left("123456", 5) == "23456"

    def test_custom_fill_char(self) -> None:
        assert pad_left("42", 5, " ") == "   42"


class TestSafeNumeric:
    """Tests for safe_numeric."""

    def test_valid_integer(self) -> None:
        assert safe_numeric("42") == 42

    def test_leading_spaces(self) -> None:
        assert safe_numeric("  42  ") == 42

    def test_positive_sign(self) -> None:
        assert safe_numeric("+42") == 42

    def test_negative_sign(self) -> None:
        assert safe_numeric("-42") == -42

    def test_non_numeric(self) -> None:
        assert safe_numeric("abc") == 0

    def test_empty_string(self) -> None:
        assert safe_numeric("") == 0

    def test_custom_default(self) -> None:
        assert safe_numeric("abc", -1) == -1


class TestSafeDecimal:
    """Tests for safe_decimal."""

    def test_valid_float(self) -> None:
        assert safe_decimal("3.14") == 3.14

    def test_integer_string(self) -> None:
        assert safe_decimal("42") == 42.0

    def test_non_numeric(self) -> None:
        assert safe_decimal("abc") == 0.0

    def test_empty_string(self) -> None:
        assert safe_decimal("") == 0.0

    def test_custom_default(self) -> None:
        assert safe_decimal("abc", -1.0) == -1.0


class TestFormatAmount:
    """Tests for format_amount."""

    def test_positive(self) -> None:
        assert format_amount(100.00) == "+00000100.00"

    def test_negative(self) -> None:
        assert format_amount(-50.25) == "-00000050.25"

    def test_zero(self) -> None:
        assert format_amount(0.0) == "+00000000.00"

    def test_large_amount(self) -> None:
        assert format_amount(99999999.99) == "+99999999.99"

    def test_small_amount(self) -> None:
        assert format_amount(0.01) == "+00000000.01"


# ===================================================================
# Lookup Codes
# ===================================================================

class TestUSStateCodes:
    """Tests for US state code lookups."""

    def test_valid_state_ny(self) -> None:
        assert is_valid_us_state_code("NY") is True

    def test_valid_state_ca(self) -> None:
        assert is_valid_us_state_code("CA") is True

    def test_valid_dc(self) -> None:
        assert is_valid_us_state_code("DC") is True

    def test_valid_territory_pr(self) -> None:
        assert is_valid_us_state_code("PR") is True

    def test_valid_territory_gu(self) -> None:
        assert is_valid_us_state_code("GU") is True

    def test_invalid_code(self) -> None:
        assert is_valid_us_state_code("ZZ") is False

    def test_lowercase_invalid(self) -> None:
        assert is_valid_us_state_code("ny") is False

    def test_empty_string(self) -> None:
        assert is_valid_us_state_code("") is False

    def test_total_count(self) -> None:
        assert len(VALID_US_STATE_CODES) == 56


class TestUSStateZipCombos:
    """Tests for US state+ZIP combination lookups."""

    def test_valid_ny10(self) -> None:
        assert is_valid_us_state_zip_combo("NY", "10") is True

    def test_valid_ca90(self) -> None:
        assert is_valid_us_state_zip_combo("CA", "90") is True

    def test_invalid_combo(self) -> None:
        assert is_valid_us_state_zip_combo("NY", "90") is False

    def test_empty_state(self) -> None:
        assert is_valid_us_state_zip_combo("", "10") is False


class TestPhoneAreaCodes:
    """Tests for phone area code lookups."""

    def test_valid_212(self) -> None:
        assert is_valid_phone_area_code("212") is True

    def test_valid_310(self) -> None:
        assert is_valid_phone_area_code("310") is True

    def test_valid_800(self) -> None:
        assert is_valid_phone_area_code("800") is True

    def test_invalid_code(self) -> None:
        assert is_valid_phone_area_code("000") is False

    def test_empty_string(self) -> None:
        assert is_valid_phone_area_code("") is False

    def test_area_codes_are_strings(self) -> None:
        for code in VALID_PHONE_AREA_CODES:
            assert isinstance(code, str)
            assert len(code) == 3
