"""
COUSR00C - User List Program (Python Translation)

Translated from the COBOL program COUSR00C.CBL in the AWS CardDemo
mainframe modernization project. This module implements the business
logic for listing users from the USRSEC file with pagination.

Original: CICS COBOL program using BMS maps and VSAM files.
This translation separates the pure business logic (browsing, selection,
pagination) from the CICS presentation layer so the rules can be tested
and reused independently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from user_security_repository import (
    UserSecurityRepository,
)


# ---------------------------------------------------------------------------
# Constants (from copybooks COTTL01Y, CSMSG01Y)
# ---------------------------------------------------------------------------

PROGRAM_NAME = "COUSR00C"
TRANSACTION_ID = "CU00"

TITLE_01 = "      AWS Mainframe Modernization       "
TITLE_02 = "              CardDemo                  "

MSG_INVALID_KEY = "Invalid key pressed. Please see below..."
MSG_THANK_YOU = "Thank you for using CardDemo application..."
MSG_TOP_OF_PAGE = "You are already at the top of the page..."
MSG_BOTTOM_OF_PAGE = "You are already at the bottom of the page..."
MSG_INVALID_SELECTION = "Invalid selection. Valid values are U and D"

PAGE_SIZE = 10


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class UserListRow:
    """A single row in the user list display."""
    user_id: str = ""
    first_name: str = ""
    last_name: str = ""
    user_type: str = ""
    selection: str = ""


@dataclass
class UserListPage:
    """State for one page of the user list screen."""
    rows: list[UserListRow] = field(default_factory=list)
    page_num: int = 0
    has_next_page: bool = False
    first_user_id: str = ""
    last_user_id: str = ""
    message: str = ""
    is_error: bool = False


@dataclass
class UserSelectionResult:
    """Outcome of processing a user selection from the list."""
    action: str = ""          # 'update', 'delete', or ''
    selected_user_id: str = ""
    error_message: str = ""


@dataclass
class ValidationResult:
    """Outcome of a validation step."""
    is_valid: bool = True
    error_message: str = ""


# ---------------------------------------------------------------------------
# User selection logic
# ---------------------------------------------------------------------------

def process_user_selection(
    selection_flag: str,
    selected_user_id: str,
) -> UserSelectionResult:
    """
    Process a user selection from the list screen.

    Business rules (from PROCESS-ENTER-KEY):
    - 'U' or 'u' → transfer to Update User (COUSR02C)
    - 'D' or 'd' → transfer to Delete User (COUSR03C)
    - Anything else with a selection → invalid selection error
    - No selection → just refresh the list
    """
    if not selection_flag or not selection_flag.strip():
        return UserSelectionResult()

    if not selected_user_id or not selected_user_id.strip():
        return UserSelectionResult()

    flag_upper = selection_flag.strip().upper()

    if flag_upper == "U":
        return UserSelectionResult(
            action="update",
            selected_user_id=selected_user_id.strip(),
        )
    elif flag_upper == "D":
        return UserSelectionResult(
            action="delete",
            selected_user_id=selected_user_id.strip(),
        )
    else:
        return UserSelectionResult(
            error_message=MSG_INVALID_SELECTION,
        )


# ---------------------------------------------------------------------------
# Pagination / browsing logic
# ---------------------------------------------------------------------------

def browse_users_forward(
    repo: UserSecurityRepository,
    start_user_id: str = "",
    current_page_num: int = 0,
) -> UserListPage:
    """
    Browse users forward from *start_user_id*.

    Corresponds to PROCESS-PAGE-FORWARD in the COBOL program.
    Uses STARTBR + READNEXT to fill up to PAGE_SIZE rows.
    """
    page = repo.browse_users_forward(
        start_user_id=start_user_id,
        page_size=PAGE_SIZE,
    )

    rows: list[UserListRow] = []
    for rec in page.users:
        rows.append(UserListRow(
            user_id=rec.user_id,
            first_name=rec.first_name,
            last_name=rec.last_name,
            user_type=rec.user_type,
        ))

    page_num = current_page_num
    if rows:
        page_num += 1

    first_id = rows[0].user_id if rows else ""
    last_id = rows[-1].user_id if rows else ""

    return UserListPage(
        rows=rows,
        page_num=page_num,
        has_next_page=page.has_next,
        first_user_id=first_id,
        last_user_id=last_id,
    )


def browse_users_backward(
    repo: UserSecurityRepository,
    start_user_id: str = "",
    current_page_num: int = 0,
) -> UserListPage:
    """
    Browse users backward from *start_user_id*.

    Corresponds to PROCESS-PAGE-BACKWARD in the COBOL program.
    Uses STARTBR + READPREV to fill up to PAGE_SIZE rows (returned
    in ascending order).
    """
    page = repo.browse_users_backward(
        start_user_id=start_user_id,
        page_size=PAGE_SIZE,
    )

    rows: list[UserListRow] = []
    for rec in page.users:
        rows.append(UserListRow(
            user_id=rec.user_id,
            first_name=rec.first_name,
            last_name=rec.last_name,
            user_type=rec.user_type,
        ))

    page_num = max(1, current_page_num - 1) if page.has_prev else 1

    first_id = rows[0].user_id if rows else ""
    last_id = rows[-1].user_id if rows else ""

    return UserListPage(
        rows=rows,
        page_num=page_num,
        has_next_page=True,  # going backward always means forward is possible
        first_user_id=first_id,
        last_user_id=last_id,
    )


def process_page_forward(
    repo: UserSecurityRepository,
    last_user_id: str,
    current_page_num: int,
    has_next_page: bool,
) -> UserListPage:
    """
    Handle PF8 (page forward) key press.

    Corresponds to PROCESS-PF8-KEY in the COBOL program.
    """
    if not has_next_page:
        return UserListPage(
            message=MSG_BOTTOM_OF_PAGE,
            is_error=False,
            page_num=current_page_num,
        )

    start_id = last_user_id if last_user_id.strip() else ""
    # Move past the last displayed record
    if start_id:
        start_id = _next_key(start_id)

    return browse_users_forward(repo, start_id, current_page_num)


def process_page_backward(
    repo: UserSecurityRepository,
    first_user_id: str,
    current_page_num: int,
) -> UserListPage:
    """
    Handle PF7 (page backward) key press.

    Corresponds to PROCESS-PF7-KEY in the COBOL program.
    """
    if current_page_num <= 1:
        return UserListPage(
            message=MSG_TOP_OF_PAGE,
            is_error=False,
            page_num=current_page_num,
        )

    start_id = first_user_id if first_user_id.strip() else ""
    # Move before the first displayed record
    if start_id:
        start_id = _prev_key(start_id)

    return browse_users_backward(repo, start_id, current_page_num)


def get_initial_page(repo: UserSecurityRepository) -> UserListPage:
    """
    Get the first page of users (initial display).

    Corresponds to the initial PROCESS-ENTER-KEY → PROCESS-PAGE-FORWARD
    call when the program first enters.
    """
    return browse_users_forward(repo, "", 0)


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


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _next_key(key: str) -> str:
    """Return the lexicographically next key (for forward browsing past a key)."""
    if not key:
        return key
    last_char = ord(key[-1])
    if last_char < 0x10FFFF:
        return key[:-1] + chr(last_char + 1)
    return key + "\x00"


def _prev_key(key: str) -> str:
    """Return the lexicographically previous key (for backward browsing before a key)."""
    if not key:
        return key
    last_char = ord(key[-1])
    if last_char > 0:
        return key[:-1] + chr(last_char - 1) + "\uffff"
    if len(key) > 1:
        return key[:-1]
    return key
