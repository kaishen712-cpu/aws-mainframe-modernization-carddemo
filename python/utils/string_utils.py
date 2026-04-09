"""
String utility functions for the CardDemo application.

Provides COBOL-style string trimming, padding, and formatting helpers
inspired by the patterns in CSSTRPFY.cpy and general COBOL string
handling conventions.
"""

from __future__ import annotations


def left_trim(value: str) -> str:
    """Remove leading whitespace (COBOL UNSTRING ... LEADING SPACES).

    Args:
        value: The string to trim.

    Returns:
        The string with leading whitespace removed.
    """
    return value.lstrip()


def right_trim(value: str) -> str:
    """Remove trailing whitespace.

    Args:
        value: The string to trim.

    Returns:
        The string with trailing whitespace removed.
    """
    return value.rstrip()


def trim(value: str) -> str:
    """Remove both leading and trailing whitespace (FUNCTION TRIM equivalent).

    Args:
        value: The string to trim.

    Returns:
        The string with leading and trailing whitespace removed.
    """
    return value.strip()


def pad_right(value: str, length: int, fill_char: str = " ") -> str:
    """Pad a string on the right to the specified length.

    Equivalent to COBOL ``MOVE value TO field`` where ``field`` is
    PIC X(length) — the value is left-justified and padded with spaces.

    Args:
        value:     The string to pad.
        length:    The desired total length.
        fill_char: Character to use for padding (default: space).

    Returns:
        The padded string, truncated if longer than ``length``.
    """
    return value[:length].ljust(length, fill_char)


def pad_left(value: str, length: int, fill_char: str = "0") -> str:
    """Pad a string on the left to the specified length.

    Equivalent to right-justifying a numeric string in a PIC 9(n) field.

    Args:
        value:     The string to pad.
        length:    The desired total length.
        fill_char: Character to use for padding (default: ``'0'``).

    Returns:
        The padded string, truncated from the left if longer than ``length``.
    """
    return value[-length:].rjust(length, fill_char)


def safe_numeric(value: str, default: int = 0) -> int:
    """Parse a string as an integer, returning ``default`` on failure.

    Mirrors the COBOL ``NUMVAL`` / ``TEST-NUMVAL`` pattern.

    Args:
        value:   The string to parse.
        default: Value returned when parsing fails.

    Returns:
        The parsed integer or the default.
    """
    stripped = value.strip()
    if stripped.isdigit():
        return int(stripped)
    # Handle leading sign
    if stripped and stripped[0] in ("+", "-") and stripped[1:].isdigit():
        return int(stripped)
    return default


def safe_decimal(value: str, default: float = 0.0) -> float:
    """Parse a string as a float, returning ``default`` on failure.

    Args:
        value:   The string to parse.
        default: Value returned when parsing fails.

    Returns:
        The parsed float or the default.
    """
    try:
        return float(value.strip())
    except (ValueError, AttributeError):
        return default


def format_amount(amount: float) -> str:
    """Format an amount in the COBOL signed-amount style (+/-NNNNNNNN.NN).

    Matches the PIC +99999999.99 / PIC S9(09)V99 display format used
    throughout CardDemo screens.

    Args:
        amount: The numeric amount to format.

    Returns:
        A 12-character string like ``"+00000100.00"`` or ``"-00000050.25"``.
    """
    sign = "+" if amount >= 0 else "-"
    return f"{sign}{abs(amount):011.2f}"
