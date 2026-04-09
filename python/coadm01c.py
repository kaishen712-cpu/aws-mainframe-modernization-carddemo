"""
COADM01C - Admin Menu Program (Python Translation)

Translated from the COBOL program COADM01C.CBL in the AWS CardDemo
mainframe modernization project. This module implements the business
logic for the admin menu: displaying admin-only options, validating
user selection, and routing to the selected program.

Original: CICS COBOL program using BMS map COADM1A and copybook COADM02Y.
This translation separates the pure business logic (option validation,
routing) from the CICS presentation layer so the rules can be tested
and reused independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Constants (from copybooks COTTL01Y, CSMSG01Y, and working storage)
# ---------------------------------------------------------------------------

PROGRAM_NAME = "COADM01C"
TRANSACTION_ID = "CA00"

TITLE_01 = "      AWS Mainframe Modernization       "
TITLE_02 = "              CardDemo                  "

MSG_INVALID_KEY = "Invalid key pressed. Please see below..."
SIGNON_PROGRAM = "COSGN00C"


# ---------------------------------------------------------------------------
# Data structures (from copybooks)
# ---------------------------------------------------------------------------

@dataclass
class AdminMenuOption:
    """A single admin menu option entry (from COADM02Y).

    Each entry defines a selectable function on the admin menu.
    Unlike the user menu (COMEN02Y), admin options do not have a
    user-type field since all options are admin-only.
    """
    opt_num: int             # CDEMO-ADMIN-OPT-NUM     PIC 9(02)
    opt_name: str            # CDEMO-ADMIN-OPT-NAME    PIC X(35)
    opt_pgmname: str         # CDEMO-ADMIN-OPT-PGMNAME PIC X(08)


@dataclass
class AdminMenuSelectionResult:
    """Outcome of processing an admin menu selection."""
    success: bool = False
    error_message: str = ""
    target_program: str = ""       # program to XCTL to on success
    is_not_installed: bool = False  # program not found (PGMIDERR)


@dataclass
class CommArea:
    """Communication area for CardDemo programs (COCOM01Y).

    Passed between programs via CICS COMMAREA to maintain session state.
    """
    cdemo_from_tranid: str = ""
    cdemo_from_program: str = ""
    cdemo_to_tranid: str = ""
    cdemo_to_program: str = ""
    cdemo_user_id: str = ""
    cdemo_user_type: str = ""      # 'A' or 'U'
    cdemo_pgm_context: int = 0     # 0=enter, 1=reenter


# ---------------------------------------------------------------------------
# Admin menu options data (from COADM02Y copybook)
# ---------------------------------------------------------------------------

# The 6 admin menu options, exactly as defined in COADM02Y.cpy
ADMIN_MENU_OPTIONS: list[AdminMenuOption] = [
    AdminMenuOption(1, "User List (Security)",                 "COUSR00C"),
    AdminMenuOption(2, "User Add (Security)",                  "COUSR01C"),
    AdminMenuOption(3, "User Update (Security)",               "COUSR02C"),
    AdminMenuOption(4, "User Delete (Security)",               "COUSR03C"),
    AdminMenuOption(5, "Transaction Type List/Update (Db2)",   "COTRTLIC"),
    AdminMenuOption(6, "Transaction Type Maintenance (Db2)",   "COTRTUPC"),
]

ADMIN_OPT_COUNT = len(ADMIN_MENU_OPTIONS)


# ---------------------------------------------------------------------------
# Validation and routing functions
# ---------------------------------------------------------------------------

def validate_admin_option(
    option_input: str,
    admin_options: Optional[list[AdminMenuOption]] = None,
) -> AdminMenuSelectionResult:
    """Validate an admin menu option selection.

    Business rules (from PROCESS-ENTER-KEY):
    1. The option must be numeric.
    2. The option must be > 0 and <= the option count (6).

    Args:
        option_input: Raw string from the option input field.
        admin_options: List of admin options. Defaults to ADMIN_MENU_OPTIONS.

    Returns:
        AdminMenuSelectionResult with validation outcome.
    """
    options = admin_options if admin_options is not None else ADMIN_MENU_OPTIONS
    opt_count = len(options)

    # Parse the option input, trimming and zero-padding like the COBOL
    # (INSPECT WS-OPTION-X REPLACING ALL ' ' BY '0')
    cleaned = option_input.strip()
    if cleaned == "":
        cleaned = "0"
    padded = cleaned.replace(" ", "0").zfill(2)

    # Check if numeric
    if not padded.isdigit():
        return AdminMenuSelectionResult(
            success=False,
            error_message="Please enter a valid option number...",
        )

    option_num = int(padded)

    # Check range: must be 1..opt_count
    if option_num == 0 or option_num > opt_count:
        return AdminMenuSelectionResult(
            success=False,
            error_message="Please enter a valid option number...",
        )

    # Look up the selected option (1-indexed)
    selected = options[option_num - 1]

    return AdminMenuSelectionResult(
        success=True,
        target_program=selected.opt_pgmname,
    )


def process_admin_menu_selection(
    option_input: str,
    admin_options: Optional[list[AdminMenuOption]] = None,
) -> AdminMenuSelectionResult:
    """Full admin menu selection workflow: validate and determine routing.

    This is the top-level entry point that mirrors the COBOL program's
    PROCESS-ENTER-KEY paragraph. After validation, it checks for DUMMY*
    programs (placeholders for unimplemented features).

    In the original COBOL, PGMIDERR is handled at the CICS level — if
    a program is not installed, the PGMIDERR handler shows a "not installed"
    message. Here we simulate this with the DUMMY prefix check.

    Args:
        option_input: Raw string from the option input field.
        admin_options: List of admin options. Defaults to ADMIN_MENU_OPTIONS.

    Returns:
        AdminMenuSelectionResult with routing outcome.
    """
    options = admin_options if admin_options is not None else ADMIN_MENU_OPTIONS

    # Step 1: Validate the option number
    result = validate_admin_option(option_input, options)
    if not result.success:
        return result

    pgm = result.target_program

    # Step 2: Check if the program is a DUMMY placeholder
    # In the original COBOL:
    #   IF CDEMO-ADMIN-OPT-PGMNAME(WS-OPTION)(1:5) NOT = 'DUMMY'
    #       ... XCTL ...
    #   END-IF
    #   (falls through to "not installed" message if DUMMY)
    if pgm[:5] == "DUMMY":
        return AdminMenuSelectionResult(
            success=False,
            is_not_installed=True,
            error_message="This option is not installed ...",
            target_program=pgm,
        )

    # Step 3: Normal program — route to it
    return AdminMenuSelectionResult(
        success=True,
        target_program=pgm,
    )


def build_commarea_for_transfer(
    commarea: CommArea,
) -> CommArea:
    """Update COMMAREA fields before transferring to a selected program.

    Corresponds to the MOVE statements before XCTL in PROCESS-ENTER-KEY:
    - CDEMO-FROM-TRANID ← CA00
    - CDEMO-FROM-PROGRAM ← COADM01C
    - CDEMO-PGM-CONTEXT ← 0
    """
    commarea.cdemo_from_tranid = TRANSACTION_ID
    commarea.cdemo_from_program = PROGRAM_NAME
    commarea.cdemo_pgm_context = 0
    return commarea


def build_admin_menu_display(
    admin_options: Optional[list[AdminMenuOption]] = None,
) -> list[str]:
    """Build the display text for each admin menu option line.

    Corresponds to BUILD-MENU-OPTIONS paragraph which creates strings
    like "01. User List (Security)" for each option.
    """
    options = admin_options if admin_options is not None else ADMIN_MENU_OPTIONS
    lines: list[str] = []
    for opt in options:
        lines.append(f"{opt.opt_num:02d}. {opt.opt_name}")
    return lines


# ---------------------------------------------------------------------------
# Screen / header helpers
# ---------------------------------------------------------------------------

def get_header_info() -> dict[str, str]:
    """Build header information for the admin menu screen.

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
