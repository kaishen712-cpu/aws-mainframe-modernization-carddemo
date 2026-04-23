"""
COMEN01C - Main Menu Program for Regular Users (Python Translation)

Translated from the COBOL program COMEN01C.CBL in the AWS CardDemo
mainframe modernization project. This module implements the business
logic for the regular-user main menu: displaying options, validating
user selection, and routing to the selected program.

Original: CICS COBOL program using BMS map COMEN1A and copybook COMEN02Y.
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

PROGRAM_NAME = "COMEN01C"
TRANSACTION_ID = "CM00"

TITLE_01 = "      AWS Mainframe Modernization       "
TITLE_02 = "              CardDemo                  "

MSG_INVALID_KEY = "Invalid key pressed. Please see below..."
SIGNON_PROGRAM = "COSGN00C"


# ---------------------------------------------------------------------------
# Data structures (from copybooks)
# ---------------------------------------------------------------------------

@dataclass
class MenuOption:
    """A single menu option entry (from COMEN02Y).

    Each entry defines a selectable function on the main menu.
    """
    opt_num: int             # CDEMO-MENU-OPT-NUM     PIC 9(02)
    opt_name: str            # CDEMO-MENU-OPT-NAME    PIC X(35)
    opt_pgmname: str         # CDEMO-MENU-OPT-PGMNAME PIC X(08)
    opt_usrtype: str         # CDEMO-MENU-OPT-USRTYPE PIC X(01) 'U' or 'A'


@dataclass
class MenuSelectionResult:
    """Outcome of processing a menu selection."""
    success: bool = False
    error_message: str = ""
    target_program: str = ""     # program to XCTL to on success
    is_not_installed: bool = False  # COPAUS0C not installed
    is_coming_soon: bool = False   # DUMMY* program


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
# Menu options data (from COMEN02Y copybook)
# ---------------------------------------------------------------------------

# The 11 menu options for regular users, exactly as defined in COMEN02Y.cpy
MENU_OPTIONS: list[MenuOption] = [
    MenuOption(1,  "Account View",                  "COACTVWC", "U"),
    MenuOption(2,  "Account Update",                "COACTUPC", "U"),
    MenuOption(3,  "Credit Card List",              "COCRDLIC", "U"),
    MenuOption(4,  "Credit Card View",              "COCRDSLC", "U"),
    MenuOption(5,  "Credit Card Update",            "COCRDUPC", "U"),
    MenuOption(6,  "Transaction List",              "COTRN00C", "U"),
    MenuOption(7,  "Transaction View",              "COTRN01C", "U"),
    MenuOption(8,  "Transaction Add",               "COTRN02C", "U"),
    MenuOption(9,  "Transaction Reports",           "CORPT00C", "U"),
    MenuOption(10, "Bill Payment",                  "COBIL00C", "U"),
    MenuOption(11, "Pending Authorization View",    "COPAUS0C", "U"),
]

MENU_OPT_COUNT = len(MENU_OPTIONS)


# ---------------------------------------------------------------------------
# Installed-program checker interface
# ---------------------------------------------------------------------------

class ProgramChecker:
    """Abstract interface to check whether a CICS program is installed.

    In the original COBOL, CICS INQUIRE PROGRAM is used to verify that
    COPAUS0C is available before attempting XCTL. Concrete implementations
    can check an actual deployment, a registry, or a simple set.
    """

    def is_installed(self, program_name: str) -> bool:
        """Return True if the program is installed and available."""
        raise NotImplementedError


class AllInstalledProgramChecker(ProgramChecker):
    """Default implementation that assumes all programs are installed."""

    def is_installed(self, program_name: str) -> bool:
        return True


class ConfigurableProgramChecker(ProgramChecker):
    """Implementation that checks against a configurable set of programs."""

    def __init__(self, installed_programs: Optional[set[str]] = None) -> None:
        self.installed_programs: set[str] = installed_programs or set()

    def is_installed(self, program_name: str) -> bool:
        return program_name in self.installed_programs


# ---------------------------------------------------------------------------
# Validation and routing functions
# ---------------------------------------------------------------------------

def validate_menu_option(
    option_input: str,
    user_type: str,
    menu_options: Optional[list[MenuOption]] = None,
) -> MenuSelectionResult:
    """Validate a menu option selection.

    Business rules (from PROCESS-ENTER-KEY):
    1. The option must be numeric.
    2. The option must be > 0 and <= the option count.
    3. If the user is a regular user (type 'U') and the option requires
       admin access (usrtype 'A'), deny access.

    Args:
        option_input: Raw string from the option input field.
        user_type: Current user's type ('A' or 'U').
        menu_options: List of menu options. Defaults to MENU_OPTIONS.

    Returns:
        MenuSelectionResult with validation outcome.
    """
    options = menu_options if menu_options is not None else MENU_OPTIONS
    opt_count = len(options)

    # Parse the option input, trimming and zero-padding like the COBOL
    # (INSPECT WS-OPTION-X REPLACING ALL ' ' BY '0')
    cleaned = option_input.strip()
    if cleaned == "":
        cleaned = "0"
    padded = cleaned.replace(" ", "0").zfill(2)

    # Check if numeric
    if not padded.isdigit():
        return MenuSelectionResult(
            success=False,
            error_message="Please enter a valid option number...",
        )

    option_num = int(padded)

    # Check range: must be 1..opt_count
    if option_num == 0 or option_num > opt_count:
        return MenuSelectionResult(
            success=False,
            error_message="Please enter a valid option number...",
        )

    # Look up the selected option (1-indexed)
    selected = options[option_num - 1]

    # Check user-type access: regular users cannot access admin-only options
    if user_type == "U" and selected.opt_usrtype == "A":
        return MenuSelectionResult(
            success=False,
            error_message="No access - Admin Only option... ",
        )

    return MenuSelectionResult(
        success=True,
        target_program=selected.opt_pgmname,
    )


def process_menu_selection(
    option_input: str,
    user_type: str,
    program_checker: Optional[ProgramChecker] = None,
    menu_options: Optional[list[MenuOption]] = None,
) -> MenuSelectionResult:
    """Full menu selection workflow: validate and determine routing.

    This is the top-level entry point that mirrors the COBOL program's
    PROCESS-ENTER-KEY paragraph. After validation, it checks for special
    program handling:
    - COPAUS0C: verify the program is installed before routing.
    - DUMMY* programs: return a "coming soon" message.

    Args:
        option_input: Raw string from the option input field.
        user_type: Current user's type ('A' or 'U').
        program_checker: Optional checker for program availability.
        menu_options: List of menu options. Defaults to MENU_OPTIONS.

    Returns:
        MenuSelectionResult with routing outcome.
    """
    options = menu_options if menu_options is not None else MENU_OPTIONS
    checker = program_checker or AllInstalledProgramChecker()

    # Step 1: Validate the option number and user access
    result = validate_menu_option(option_input, user_type, options)
    if not result.success:
        return result

    pgm = result.target_program

    # Step 2: Handle special programs

    # COPAUS0C requires an installation check (CICS INQUIRE PROGRAM)
    if pgm == "COPAUS0C":
        if not checker.is_installed(pgm):
            # Find the option name for the error message
            opt_name = _find_option_name(pgm, options)
            return MenuSelectionResult(
                success=False,
                is_not_installed=True,
                error_message=f"This option {opt_name}is not installed...",
                target_program=pgm,
            )

    # DUMMY* programs are placeholders for future features
    if pgm.startswith("DUMMY"):
        opt_name = _find_option_name(pgm, options)
        return MenuSelectionResult(
            success=False,
            is_coming_soon=True,
            error_message=f"This option {opt_name}is coming soon ...",
            target_program=pgm,
        )

    # Step 3: Normal program — route to it
    return MenuSelectionResult(
        success=True,
        target_program=pgm,
    )


def build_commarea_for_transfer(
    commarea: CommArea,
) -> CommArea:
    """Update COMMAREA fields before transferring to a selected program.

    Corresponds to the MOVE statements before XCTL in PROCESS-ENTER-KEY:
    - CDEMO-FROM-TRANID ← CM00
    - CDEMO-FROM-PROGRAM ← COMEN01C
    - CDEMO-PGM-CONTEXT ← 0
    """
    commarea.cdemo_from_tranid = TRANSACTION_ID
    commarea.cdemo_from_program = PROGRAM_NAME
    commarea.cdemo_pgm_context = 0
    return commarea


def build_menu_display(
    menu_options: Optional[list[MenuOption]] = None,
) -> list[str]:
    """Build the display text for each menu option line.

    Corresponds to BUILD-MENU-OPTIONS paragraph which creates strings
    like "01. Account View" for each option.
    """
    options = menu_options if menu_options is not None else MENU_OPTIONS
    lines: list[str] = []
    for opt in options:
        lines.append(f"{opt.opt_num:02d}. {opt.opt_name}")
    return lines


# ---------------------------------------------------------------------------
# Screen / header helpers
# ---------------------------------------------------------------------------

def get_header_info() -> dict[str, str]:
    """Build header information for the menu screen.

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


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_option_name(pgm_name: str, options: list[MenuOption]) -> str:
    """Find the display name for a program in the options list."""
    for opt in options:
        if opt.opt_pgmname == pgm_name:
            return opt.opt_name
    return ""
