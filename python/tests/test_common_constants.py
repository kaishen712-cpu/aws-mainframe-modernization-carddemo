"""
Unit tests for common/constants.py.

Covers screen title constants, common messages, AbendData dataclass,
date/time formatting functions, and the timestamp format constant.
"""

from python.common.constants import (
    TITLE_LINE_1,
    TITLE_LINE_2,
    TITLE_THANK_YOU,
    MSG_THANK_YOU,
    MSG_INVALID_KEY,
    AbendData,
    DATE_FORMAT_CCYYMMDD,
    format_date_mm_dd_yy,
    format_time_hh_mm_ss,
    format_timestamp,
)


# ===================================================================
# Screen Title Constants
# ===================================================================

class TestScreenTitles:
    """Tests for COTTL01Y.cpy screen title constants."""

    def test_title_line_1_contains_aws(self) -> None:
        assert "AWS" in TITLE_LINE_1

    def test_title_line_2_contains_carddemo(self) -> None:
        assert "CardDemo" in TITLE_LINE_2

    def test_title_thank_you_contains_ccda(self) -> None:
        assert "CCDA" in TITLE_THANK_YOU


# ===================================================================
# Common Messages
# ===================================================================

class TestCommonMessages:
    """Tests for CSMSG01Y.cpy common message constants."""

    def test_msg_thank_you(self) -> None:
        assert "CardDemo" in MSG_THANK_YOU

    def test_msg_invalid_key(self) -> None:
        assert "Invalid key" in MSG_INVALID_KEY


# ===================================================================
# AbendData
# ===================================================================

class TestAbendData:
    """Tests for AbendData dataclass (CSMSG02Y.cpy)."""

    def test_defaults(self) -> None:
        ad = AbendData()
        assert ad.abend_code == ""
        assert ad.abend_culprit == ""
        assert ad.abend_reason == ""
        assert ad.abend_msg == ""

    def test_construction(self) -> None:
        ad = AbendData(
            abend_code="ASRA",
            abend_culprit="COSGN00C",
            abend_reason="Addressing exception",
            abend_msg="Program COSGN00C abended with code ASRA",
        )
        assert ad.abend_code == "ASRA"
        assert ad.abend_culprit == "COSGN00C"
        assert ad.abend_reason == "Addressing exception"
        assert "ASRA" in ad.abend_msg

    def test_field_count(self) -> None:
        assert len(AbendData.__dataclass_fields__) == 4


# ===================================================================
# Date Format Constant
# ===================================================================

class TestDateFormatConstant:
    """Tests for the CSDAT01Y.cpy date format constant."""

    def test_date_format_value(self) -> None:
        assert DATE_FORMAT_CCYYMMDD == "YYYYMMDD"


# ===================================================================
# format_date_mm_dd_yy
# ===================================================================

class TestFormatDateMmDdYy:
    """Tests for format_date_mm_dd_yy (WS-CURDATE-MM-DD-YY)."""

    def test_typical_date(self) -> None:
        assert format_date_mm_dd_yy(2024, 3, 15) == "03/15/24"

    def test_single_digit_month_day(self) -> None:
        assert format_date_mm_dd_yy(2024, 1, 5) == "01/05/24"

    def test_century_boundary_1999(self) -> None:
        assert format_date_mm_dd_yy(1999, 12, 31) == "12/31/99"

    def test_century_boundary_2000(self) -> None:
        assert format_date_mm_dd_yy(2000, 1, 1) == "01/01/00"

    def test_december_31(self) -> None:
        assert format_date_mm_dd_yy(2024, 12, 31) == "12/31/24"

    def test_january_1(self) -> None:
        assert format_date_mm_dd_yy(2024, 1, 1) == "01/01/24"


# ===================================================================
# format_time_hh_mm_ss
# ===================================================================

class TestFormatTimeHhMmSs:
    """Tests for format_time_hh_mm_ss (WS-CURTIME-HH-MM-SS)."""

    def test_typical_time(self) -> None:
        assert format_time_hh_mm_ss(14, 30, 5) == "14:30:05"

    def test_midnight(self) -> None:
        assert format_time_hh_mm_ss(0, 0, 0) == "00:00:00"

    def test_end_of_day(self) -> None:
        assert format_time_hh_mm_ss(23, 59, 59) == "23:59:59"

    def test_single_digit_padding(self) -> None:
        assert format_time_hh_mm_ss(1, 2, 3) == "01:02:03"


# ===================================================================
# format_timestamp
# ===================================================================

class TestFormatTimestamp:
    """Tests for format_timestamp (WS-TIMESTAMP)."""

    def test_typical_timestamp(self) -> None:
        result = format_timestamp(2024, 3, 15, 14, 30, 5, 123456)
        assert result == "2024-03-15 14:30:05.123456"

    def test_default_microseconds(self) -> None:
        result = format_timestamp(2024, 3, 15, 14, 30, 5)
        assert result == "2024-03-15 14:30:05.000000"

    def test_midnight_new_year(self) -> None:
        result = format_timestamp(2000, 1, 1, 0, 0, 0, 0)
        assert result == "2000-01-01 00:00:00.000000"

    def test_end_of_year(self) -> None:
        result = format_timestamp(1999, 12, 31, 23, 59, 59, 999999)
        assert result == "1999-12-31 23:59:59.999999"

    def test_timestamp_format_length(self) -> None:
        result = format_timestamp(2024, 3, 15, 14, 30, 5, 0)
        assert len(result) == 26
