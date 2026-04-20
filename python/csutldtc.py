"""
CSUTLDTC - Date Validation Utility (Python Translation)

Translated from the COBOL subroutine CSUTLDTC.CBL in the AWS CardDemo
mainframe modernization project. This module provides date validation
functionality equivalent to the IBM Language Environment CEEDAYS service.

Original: COBOL subroutine called by COTRN02C, CORPT00C, COACTUPC.
This translation uses Python's datetime.strptime for validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class DateValidationResult:
    """
    Result of a date validation call.

    Mirrors the COBOL WS-MESSAGE structure returned via LS-RESULT.

    Attributes:
        severity: Severity code — 0 means valid, non-zero means error.
        msg_no: Message number from the validation.
        result_text: Human-readable result description (up to 15 chars).
        date_tested: The date string that was tested.
        date_format_used: The format mask that was used.
    """
    severity: int = 0
    msg_no: int = 0
    result_text: str = ""
    date_tested: str = ""
    date_format_used: str = ""

    @property
    def is_valid(self) -> bool:
        """Return True if the date passed validation."""
        return self.severity == 0


# ---------------------------------------------------------------------------
# Format mapping: COBOL date format masks → Python strptime codes
# ---------------------------------------------------------------------------

_COBOL_TO_PYTHON_FORMAT: dict[str, str] = {
    "YYYYMMDD": "%Y%m%d",
    "YYYY-MM-DD": "%Y-%m-%d",
    "YYYY/MM/DD": "%Y/%m/%d",
    "MM/DD/YYYY": "%m/%d/%Y",
    "DD/MM/YYYY": "%d/%m/%Y",
    "MMDDYYYY": "%m%d%Y",
    "DDMMYYYY": "%d%m%Y",
}


def _cobol_format_to_python(cobol_format: str) -> str:
    """
    Convert a COBOL date format mask to a Python strptime format string.

    Args:
        cobol_format: COBOL-style format mask (e.g., 'YYYYMMDD').

    Returns:
        Python strptime format string (e.g., '%Y%m%d').

    Raises:
        ValueError: If the format mask is not recognized.
    """
    fmt = cobol_format.strip().upper()
    if fmt in _COBOL_TO_PYTHON_FORMAT:
        return _COBOL_TO_PYTHON_FORMAT[fmt]
    raise ValueError(f"Unsupported date format mask: {cobol_format!r}")


# ---------------------------------------------------------------------------
# Main validation function
# ---------------------------------------------------------------------------

def validate_date(date_string: str, date_format: str) -> DateValidationResult:
    """
    Validate a date string against a format mask.

    This is the Python equivalent of calling the CSUTLDTC COBOL subroutine.
    It replaces the IBM LE CEEDAYS service with Python's datetime parsing.

    Args:
        date_string: The date string to validate (e.g., '2024-06-15').
        date_format: The COBOL-style format mask (e.g., 'YYYY-MM-DD').

    Returns:
        A DateValidationResult with severity 0 if valid, non-zero otherwise.

    Examples:
        >>> result = validate_date('2024-06-15', 'YYYY-MM-DD')
        >>> result.is_valid
        True

        >>> result = validate_date('2024-02-30', 'YYYY-MM-DD')
        >>> result.is_valid
        False
    """
    result = DateValidationResult(
        date_tested=date_string.strip(),
        date_format_used=date_format.strip(),
    )

    # Check for empty inputs
    if not date_string.strip():
        result.severity = 3
        result.msg_no = 2507
        result.result_text = "Insufficient"
        return result

    if not date_format.strip():
        result.severity = 3
        result.msg_no = 2510
        result.result_text = "Bad Pic String"
        return result

    # Convert COBOL format to Python format
    try:
        py_format = _cobol_format_to_python(date_format)
    except ValueError:
        result.severity = 3
        result.msg_no = 2510
        result.result_text = "Bad Pic String"
        return result

    # Attempt to parse the date
    try:
        parsed = datetime.strptime(date_string.strip(), py_format)
    except ValueError:
        # Determine the specific error type
        result.severity = 3
        result.result_text = "Date is invalid"

        # Try to distinguish between bad value and non-numeric data
        stripped = date_string.strip()
        digits_only = stripped.replace("-", "").replace("/", "")
        if not digits_only.isdigit():
            result.msg_no = 2512
            result.result_text = "Nonnumeric data"
        else:
            # Check for invalid month
            try:
                _extract_month(stripped, date_format)
            except _InvalidMonth:
                result.msg_no = 2509
                result.result_text = "Invalid month"
                return result
            # General bad date value (e.g., Feb 30)
            result.msg_no = 2508
            result.result_text = "Datevalue error"
        return result

    # Extra safeguard: verify the parsed date round-trips correctly
    # This catches cases like strptime silently accepting out-of-range values
    if parsed.strftime(py_format) != date_string.strip():
        result.severity = 3
        result.msg_no = 2508
        result.result_text = "Datevalue error"
        return result

    # Date is valid
    result.severity = 0
    result.msg_no = 0
    result.result_text = "Date is valid"
    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

class _InvalidMonth(Exception):
    """Raised when the month value is out of range."""


def _extract_month(date_str: str, cobol_format: str) -> int:
    """
    Extract and validate the month from a date string.

    Raises _InvalidMonth if the month is not 1-12.
    """
    fmt = cobol_format.strip().upper()
    month = -1

    if fmt in ("YYYYMMDD", "YYYY-MM-DD", "YYYY/MM/DD"):
        sep_positions = {"YYYYMMDD": (4, 6), "YYYY-MM-DD": (5, 7),
                         "YYYY/MM/DD": (5, 7)}
        start, end = sep_positions[fmt]
        try:
            month = int(date_str[start:end])
        except (ValueError, IndexError):
            pass
    elif fmt in ("MMDDYYYY", "MM/DD/YYYY"):
        try:
            month = int(date_str[0:2])
        except (ValueError, IndexError):
            pass
    elif fmt in ("DDMMYYYY", "DD/MM/YYYY"):
        sep_positions = {"DDMMYYYY": (2, 4), "DD/MM/YYYY": (3, 5)}
        start, end = sep_positions[fmt]
        try:
            month = int(date_str[start:end])
        except (ValueError, IndexError):
            pass

    if month < 1 or month > 12:
        raise _InvalidMonth(f"Month {month} is out of range")
    return month


def format_validation_message(result: DateValidationResult) -> str:
    """
    Format a validation result into the 80-character message string
    matching the COBOL WS-MESSAGE layout.

    This is provided for compatibility with programs that parse the
    raw result string.

    Args:
        result: The validation result to format.

    Returns:
        An 80-character string matching the COBOL WS-MESSAGE layout.
    """
    severity_str = str(result.severity).zfill(4)
    msg_no_str = str(result.msg_no).zfill(4)
    result_text = result.result_text.ljust(15)
    date_tested = result.date_tested.ljust(10)
    date_fmt = result.date_format_used.ljust(10)

    msg = (
        f"{severity_str}"
        f"Mesg Code:{msg_no_str} "
        f"{result_text} "
        f"TstDate:{date_tested} "
        f"Mask used:{date_fmt} "
        f"   "
    )
    return msg[:80].ljust(80)
