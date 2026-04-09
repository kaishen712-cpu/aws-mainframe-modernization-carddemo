"""
Date validation utilities for the CardDemo application.

Translated from CSUTLDTC.cbl + CSUTLDPY.cpy + CSUTLDWY.cpy.
Validates dates in CCYYMMDD format with century, month, day, leap-year,
and date-of-birth (not-in-the-future) checks.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date


@dataclass
class DateValidationResult:
    """Outcome of a date validation check."""

    is_valid: bool = False
    error_message: str = ""
    year_flag: str = ""      # '' = valid, '0' = invalid, 'B' = blank
    month_flag: str = ""     # '' = valid, '0' = invalid, 'B' = blank
    day_flag: str = ""       # '' = valid, '0' = invalid, 'B' = blank


def validate_year(year_str: str) -> DateValidationResult:
    """Validate a 4-digit year string (century must be 19 or 20).

    Translated from EDIT-YEAR-CCYY in CSUTLDPY.cpy.

    Args:
        year_str: A 4-character year string, e.g. ``"2024"``.

    Returns:
        A DateValidationResult indicating success or the specific error.
    """
    if not year_str or year_str.strip() == "":
        return DateValidationResult(
            is_valid=False,
            error_message="Year must be supplied.",
            year_flag="B",
        )

    if not year_str.isdigit() or len(year_str) != 4:
        return DateValidationResult(
            is_valid=False,
            error_message="Year must be a 4-digit number.",
            year_flag="0",
        )

    century = int(year_str[:2])
    if century not in (19, 20):
        return DateValidationResult(
            is_valid=False,
            error_message="Century is not valid.",
            year_flag="0",
        )

    return DateValidationResult(is_valid=True)


def validate_month(month_str: str) -> DateValidationResult:
    """Validate a 2-digit month string (1-12).

    Translated from EDIT-MONTH in CSUTLDPY.cpy.

    Args:
        month_str: A 2-character month string, e.g. ``"03"``.

    Returns:
        A DateValidationResult indicating success or the specific error.
    """
    if not month_str or month_str.strip() == "":
        return DateValidationResult(
            is_valid=False,
            error_message="Month must be supplied.",
            month_flag="B",
        )

    if not month_str.isdigit():
        return DateValidationResult(
            is_valid=False,
            error_message="Month must be a number between 1 and 12.",
            month_flag="0",
        )

    month_n = int(month_str)
    if month_n < 1 or month_n > 12:
        return DateValidationResult(
            is_valid=False,
            error_message="Month must be a number between 1 and 12.",
            month_flag="0",
        )

    return DateValidationResult(is_valid=True)


def validate_day(day_str: str) -> DateValidationResult:
    """Validate a 2-digit day string (1-31).

    Translated from EDIT-DAY in CSUTLDPY.cpy.

    Args:
        day_str: A 2-character day string, e.g. ``"15"``.

    Returns:
        A DateValidationResult indicating success or the specific error.
    """
    if not day_str or day_str.strip() == "":
        return DateValidationResult(
            is_valid=False,
            error_message="Day must be supplied.",
            day_flag="B",
        )

    if not day_str.isdigit():
        return DateValidationResult(
            is_valid=False,
            error_message="Day must be a number between 1 and 31.",
            day_flag="0",
        )

    day_n = int(day_str)
    if day_n < 1 or day_n > 31:
        return DateValidationResult(
            is_valid=False,
            error_message="Day must be a number between 1 and 31.",
            day_flag="0",
        )

    return DateValidationResult(is_valid=True)


def validate_day_month_year(year: int, month: int, day: int) -> DateValidationResult:
    """Combined day/month/year validation including leap-year checks.

    Translated from EDIT-DAY-MONTH-YEAR in CSUTLDPY.cpy.

    Args:
        year:  4-digit integer year (e.g. 2024).
        month: Integer month (1-12).
        day:   Integer day (1-31).

    Returns:
        A DateValidationResult indicating success or the specific error.
    """
    months_with_31 = {1, 3, 5, 7, 8, 10, 12}

    if day == 31 and month not in months_with_31:
        return DateValidationResult(
            is_valid=False,
            error_message="Cannot have 31 days in this month.",
            day_flag="0",
            month_flag="0",
        )

    if month == 2 and day >= 30:
        return DateValidationResult(
            is_valid=False,
            error_message="Cannot have 30 days in this month.",
            day_flag="0",
            month_flag="0",
        )

    if month == 2 and day == 29:
        if not calendar.isleap(year):
            return DateValidationResult(
                is_valid=False,
                error_message="Not a leap year. Cannot have 29 days in this month.",
                year_flag="0",
                day_flag="0",
                month_flag="0",
            )

    return DateValidationResult(is_valid=True)


def validate_date_ccyymmdd(
    date_str: str, field_name: str = "Date"
) -> DateValidationResult:
    """Full CCYYMMDD date validation pipeline.

    Runs year, month, day, and combined checks in sequence, matching
    the COBOL EDIT-DATE-CCYYMMDD flow.

    Args:
        date_str:   An 8-character date string in CCYYMMDD format.
        field_name: Human-readable name used in error messages.

    Returns:
        A DateValidationResult indicating success or the first error found.
    """
    if not date_str or len(date_str) != 8:
        return DateValidationResult(
            is_valid=False,
            error_message=f"{field_name}: Date must be 8 characters (CCYYMMDD).",
        )

    year_str = date_str[0:4]
    month_str = date_str[4:6]
    day_str = date_str[6:8]

    yr = validate_year(year_str)
    if not yr.is_valid:
        return DateValidationResult(
            is_valid=False,
            error_message=f"{field_name}: {yr.error_message}",
            year_flag=yr.year_flag,
        )

    mo = validate_month(month_str)
    if not mo.is_valid:
        return DateValidationResult(
            is_valid=False,
            error_message=f"{field_name}: {mo.error_message}",
            month_flag=mo.month_flag,
        )

    dy = validate_day(day_str)
    if not dy.is_valid:
        return DateValidationResult(
            is_valid=False,
            error_message=f"{field_name}: {dy.error_message}",
            day_flag=dy.day_flag,
        )

    year_n = int(year_str)
    month_n = int(month_str)
    day_n = int(day_str)

    combo = validate_day_month_year(year_n, month_n, day_n)
    if not combo.is_valid:
        return DateValidationResult(
            is_valid=False,
            error_message=f"{field_name}: {combo.error_message}",
            year_flag=combo.year_flag,
            month_flag=combo.month_flag,
            day_flag=combo.day_flag,
        )

    return DateValidationResult(is_valid=True)


def is_valid_calendar_date(date_str: str) -> bool:
    """Convenience wrapper — returns True if ``date_str`` is a valid CCYYMMDD date.

    Args:
        date_str: An 8-character date string in CCYYMMDD format.
    """
    return validate_date_ccyymmdd(date_str).is_valid


def validate_date_of_birth(
    date_str: str, field_name: str = "Date of Birth"
) -> DateValidationResult:
    """Validate a date of birth — must be a valid date and strictly before today.

    Translated from EDIT-DATE-OF-BIRTH in CSUTLDPY.cpy.  The COBOL source
    compares ``WS-CURRENT-DATE-BINARY > WS-EDIT-DATE-BINARY``, meaning
    today's date is *not* accepted as a valid date of birth.

    Args:
        date_str:   An 8-character date string in CCYYMMDD format.
        field_name: Human-readable name used in error messages.

    Returns:
        A DateValidationResult indicating success or the specific error.
    """
    result = validate_date_ccyymmdd(date_str, field_name)
    if not result.is_valid:
        return result

    year_n = int(date_str[0:4])
    month_n = int(date_str[4:6])
    day_n = int(date_str[6:8])

    dob = date(year_n, month_n, day_n)
    today = date.today()

    if dob >= today:
        return DateValidationResult(
            is_valid=False,
            error_message=f"{field_name}: cannot be in the future.",
            year_flag="0",
            month_flag="0",
            day_flag="0",
        )

    return DateValidationResult(is_valid=True)
