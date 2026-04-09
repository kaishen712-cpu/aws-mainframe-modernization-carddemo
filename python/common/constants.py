"""
Application-wide constants for the CardDemo application.

Consolidates values from several COBOL copybooks:
- COTTL01Y.cpy  — screen titles
- CSMSG01Y.cpy  — common user-facing messages
- CSMSG02Y.cpy  — abend/error structures
- CSDAT01Y.cpy  — date/time formatting patterns
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Screen titles (COTTL01Y.cpy — CCDA-SCREEN-TITLE)
# ---------------------------------------------------------------------------

TITLE_LINE_1 = "      AWS Mainframe Modernization       "
TITLE_LINE_2 = "              CardDemo                  "
TITLE_THANK_YOU = "Thank you for using CCDA application... "


# ---------------------------------------------------------------------------
# Common messages (CSMSG01Y.cpy — CCDA-COMMON-MESSAGES)
# ---------------------------------------------------------------------------

MSG_THANK_YOU = "Thank you for using CardDemo application..."
MSG_INVALID_KEY = "Invalid key pressed. Please see below..."


# ---------------------------------------------------------------------------
# Abend / error data (CSMSG02Y.cpy — ABEND-DATA)
# ---------------------------------------------------------------------------

@dataclass
class AbendData:
    """Work-area structure for the abend routine (CSMSG02Y.cpy).

    Captures error context when a CICS program needs to abnormally end.
    """

    abend_code: str = ""        # ABEND-CODE     PIC X(4)
    abend_culprit: str = ""     # ABEND-CULPRIT  PIC X(8)
    abend_reason: str = ""      # ABEND-REASON   PIC X(50)
    abend_msg: str = ""         # ABEND-MSG      PIC X(72)


# ---------------------------------------------------------------------------
# Date / time formatting (CSDAT01Y.cpy — WS-DATE-TIME)
# ---------------------------------------------------------------------------

DATE_FORMAT_CCYYMMDD = "YYYYMMDD"

# Display formats
DATE_DISPLAY_MM_DD_YY = "{month:02d}/{day:02d}/{year:02d}"
TIME_DISPLAY_HH_MM_SS = "{hours:02d}:{minutes:02d}:{seconds:02d}"

# Timestamp format:  YYYY-MM-DD HH:MM:SS.MMMMMM
TIMESTAMP_FORMAT = "{year:04d}-{month:02d}-{day:02d} {hours:02d}:{minutes:02d}:{seconds:02d}.{microseconds:06d}"


def format_date_mm_dd_yy(year: int, month: int, day: int) -> str:
    """Format a date as MM/DD/YY (WS-CURDATE-MM-DD-YY).

    Args:
        year:  Full 4-digit year (only the last 2 digits are used).
        month: Month (1-12).
        day:   Day (1-31).

    Returns:
        A string like ``"03/15/24"``.
    """
    return f"{month:02d}/{day:02d}/{year % 100:02d}"


def format_time_hh_mm_ss(hours: int, minutes: int, seconds: int) -> str:
    """Format a time as HH:MM:SS (WS-CURTIME-HH-MM-SS).

    Args:
        hours:   Hour (0-23).
        minutes: Minute (0-59).
        seconds: Second (0-59).

    Returns:
        A string like ``"14:30:05"``.
    """
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def format_timestamp(
    year: int,
    month: int,
    day: int,
    hours: int,
    minutes: int,
    seconds: int,
    microseconds: int = 0,
) -> str:
    """Format a full timestamp (WS-TIMESTAMP).

    Args:
        year:         4-digit year.
        month:        Month (1-12).
        day:          Day (1-31).
        hours:        Hour (0-23).
        minutes:      Minute (0-59).
        seconds:      Second (0-59).
        microseconds: Microseconds (0-999999).

    Returns:
        A string like ``"2024-03-15 14:30:05.000000"``.
    """
    return (
        f"{year:04d}-{month:02d}-{day:02d} "
        f"{hours:02d}:{minutes:02d}:{seconds:02d}.{microseconds:06d}"
    )
