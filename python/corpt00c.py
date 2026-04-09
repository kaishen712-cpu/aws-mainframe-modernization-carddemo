"""
CORPT00C - Transaction Report Program (Python Translation)

Translated from the COBOL program CORPT00C.CBL in the AWS CardDemo
mainframe modernization project. This module implements the business
logic for submitting batch transaction report requests.

Original: CICS COBOL program using BMS maps, VSAM files, and JCL job
submission via a transient data queue. This translation replaces the
JCL submission with a validated ReportRequest dataclass.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Constants (from copybooks COTTL01Y, CSMSG01Y)
# ---------------------------------------------------------------------------

PROGRAM_NAME = "CORPT00C"
TRANSACTION_ID = "CR00"

TITLE_01 = "      AWS Mainframe Modernization       "
TITLE_02 = "              CardDemo                  "

MSG_INVALID_KEY = "Invalid key pressed. Please see below..."


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ReportRequest:
    """
    Validated report request object.

    Replaces the JCL job submission in the original COBOL program.
    Contains the validated parameters needed to generate the report.
    """
    report_type: str = ""       # 'Monthly', 'Yearly', or 'Custom'
    start_date: str = ""        # YYYYMMDD
    end_date: str = ""          # YYYYMMDD
    confirmed: bool = False


@dataclass
class ReportResult:
    """Outcome of a report submission request."""
    success: bool = False
    message: str = ""
    request: Optional[ReportRequest] = None


# ---------------------------------------------------------------------------
# Date validation (replaces CSUTLDTC subroutine)
# ---------------------------------------------------------------------------

def validate_date(year: str, month: str, day: str) -> tuple[bool, str]:
    """
    Validate a date given as separate YYYY, MM, DD strings.

    This replaces the CALL 'CSUTLDTC' in the original COBOL program.
    Returns:
        (is_valid, yyyymmdd_string_or_empty)
    """
    try:
        y = int(year)
        m = int(month)
        d = int(day)
    except (ValueError, TypeError):
        return (False, "")

    if y < 1 or m < 1 or m > 12 or d < 1:
        return (False, "")

    try:
        date(y, m, d)
    except ValueError:
        return (False, "")

    return (True, f"{y:04d}{m:02d}{d:02d}")


def validate_date_range(start_yyyymmdd: str, end_yyyymmdd: str) -> tuple[bool, str]:
    """
    Validate that start_date <= end_date.

    Returns:
        (is_valid, error_message)
    """
    if start_yyyymmdd > end_yyyymmdd:
        return (False, "Start date must not be after end date...")
    return (True, "")


# ---------------------------------------------------------------------------
# Confirmation validation
# ---------------------------------------------------------------------------

def validate_confirmation(confirm_input: str) -> tuple[str, str]:
    """
    Validate and classify the confirmation input.

    Business rules (from SUBMIT-JOB-TO-INTRDR):
    - Blank/empty: prompt for confirmation
    - 'Y'/'y': confirmed
    - 'N'/'n': cancelled
    - Other: invalid

    Returns:
        (status, error_message) where status is one of:
        'confirmed', 'cancelled', 'pending', 'invalid'
    """
    stripped = confirm_input.strip()

    if not stripped:
        return ("pending", "")

    upper = stripped.upper()
    if upper == "Y":
        return ("confirmed", "")
    if upper == "N":
        return ("cancelled", "")

    return ("invalid", f'"{stripped}" is not a valid value to confirm...')


# ---------------------------------------------------------------------------
# Core report request logic
# ---------------------------------------------------------------------------

def _compute_monthly_dates() -> tuple[str, str]:
    """
    Compute start/end dates for a monthly report.

    Start: first day of current month.
    End: current date.
    """
    today = date.today()
    start = f"{today.year:04d}{today.month:02d}01"
    end = f"{today.year:04d}{today.month:02d}{today.day:02d}"
    return (start, end)


def _compute_yearly_dates() -> tuple[str, str]:
    """
    Compute start/end dates for a yearly report.

    Start: January 1 of current year.
    End: current date.
    """
    today = date.today()
    start = f"{today.year:04d}0101"
    end = f"{today.year:04d}{today.month:02d}{today.day:02d}"
    return (start, end)


def process_report_request(
    monthly: str = "",
    yearly: str = "",
    custom: str = "",
    start_year: str = "",
    start_month: str = "",
    start_day: str = "",
    end_year: str = "",
    end_month: str = "",
    end_day: str = "",
    confirm: str = "",
) -> ReportResult:
    """
    Process a report request.

    Corresponds to the PROCESS-ENTER-KEY paragraph in CORPT00C.

    Args:
        monthly: 'M'/'m' to request a monthly report.
        yearly: 'Y'/'y' to request a yearly report.
        custom: 'C'/'c' to request a custom date-range report.
        start_year: Custom start year (YYYY).
        start_month: Custom start month (MM).
        start_day: Custom start day (DD).
        end_year: Custom end year (YYYY).
        end_month: Custom end month (MM).
        end_day: Custom end day (DD).
        confirm: Confirmation flag (Y/N/blank).

    Returns:
        ReportResult with validated request or error message.
    """
    # Determine report type
    report_type = ""
    start_date = ""
    end_date = ""

    if monthly.strip().upper() == "M":
        report_type = "Monthly"
        start_date, end_date = _compute_monthly_dates()

    elif yearly.strip().upper() == "Y":
        report_type = "Yearly"
        start_date, end_date = _compute_yearly_dates()

    elif custom.strip().upper() == "C":
        report_type = "Custom"

        # Validate start date
        valid, start_date = validate_date(start_year, start_month, start_day)
        if not valid:
            return ReportResult(
                success=False,
                message="Start Date - Not a valid date...",
            )

        # Validate end date
        valid, end_date = validate_date(end_year, end_month, end_day)
        if not valid:
            return ReportResult(
                success=False,
                message="End Date - Not a valid date...",
            )

        # Validate range
        valid, range_error = validate_date_range(start_date, end_date)
        if not valid:
            return ReportResult(
                success=False,
                message=range_error,
            )

    else:
        return ReportResult(
            success=False,
            message="Select a report type to print report...",
        )

    # Validate confirmation
    conf_status, conf_error = validate_confirmation(confirm)

    if conf_status == "invalid":
        return ReportResult(success=False, message=conf_error)

    if conf_status == "cancelled":
        return ReportResult(success=False, message="")

    if conf_status == "pending":
        return ReportResult(
            success=False,
            message=f"Please confirm to print the {report_type} report...",
            request=ReportRequest(
                report_type=report_type,
                start_date=start_date,
                end_date=end_date,
                confirmed=False,
            ),
        )

    # Confirmed — return the report request
    request = ReportRequest(
        report_type=report_type,
        start_date=start_date,
        end_date=end_date,
        confirmed=True,
    )

    return ReportResult(
        success=True,
        message=f"{report_type} report submitted for printing ...",
        request=request,
    )


# ---------------------------------------------------------------------------
# Screen / header helpers
# ---------------------------------------------------------------------------

def get_header_info() -> dict[str, str]:
    """
    Build header information for the screen.

    Corresponds to POPULATE-HEADER-INFO which fills in the title lines,
    program name, transaction ID, current date and current time.
    """
    now = datetime.now()
    return {
        "title01": TITLE_01,
        "title02": TITLE_02,
        "transaction_id": TRANSACTION_ID,
        "program_name": PROGRAM_NAME,
        "current_date": now.strftime("%m/%d/%y"),
        "current_time": now.strftime("%H:%M:%S"),
    }


def clear_all_fields() -> dict[str, str]:
    """
    Return a dictionary of blank fields.

    Corresponds to INITIALIZE-ALL-FIELDS / CLEAR-CURRENT-SCREEN (PF4).
    """
    return {
        "monthly": "",
        "yearly": "",
        "custom": "",
        "start_month": "",
        "start_day": "",
        "start_year": "",
        "end_month": "",
        "end_day": "",
        "end_year": "",
        "confirm": "",
    }
