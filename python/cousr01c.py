"""
COUSR01C - Add User Program (Python Translation)

Translated from the COBOL program COUSR01C.CBL in the AWS CardDemo
mainframe modernization project. This module implements the business
logic for adding a new user to the USRSEC file.

Original: CICS COBOL program using BMS maps and VSAM files.
This translation separates the pure business logic (validation, record
creation) from the CICS presentation layer so the rules can be tested
and reused independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from user_security_repository import (
    UserSecurityRecord,
    UserSecurityRepository,
)


# ---------------------------------------------------------------------------
# Constants (from copybooks COTTL01Y, CSMSG01Y)
# ---------------------------------------------------------------------------

PROGRAM_NAME = "COUSR01C"
TRANSACTION_ID = "CU01"

TITLE_01 = "      AWS Mainframe Modernization       "
TITLE_02 = "              CardDemo                  "

MSG_INVALID_KEY = "Invalid key pressed. Please see below..."
MSG_THANK_YOU = "Thank you for using CardDemo application..."


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class UserAddInput:
    """All user-supplied fields from the Add User screen (COUSR1AI)."""
    user_id: str = ""         # USERIDI  PIC X(08)
    first_name: str = ""      # FNAMEI   PIC X(20)
    last_name: str = ""       # LNAMEI   PIC X(20)
    password: str = ""        # PASSWDI  PIC X(08)
    user_type: str = ""       # USRTYPEI PIC X(01) — 'A' or 'U'


@dataclass
class ValidationResult:
    """Outcome of a validation step."""
    is_valid: bool = True
    error_message: str = ""
    error_field: str = ""


@dataclass
class AddUserResult:
    """Outcome of the add-user operation."""
    success: bool = False
    message: str = ""


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_user_input(user_input: UserAddInput) -> ValidationResult:
    """
    Validate all fields for adding a new user.

    Business rules (from PROCESS-ENTER-KEY):
    - First Name must not be empty
    - Last Name must not be empty
    - User ID must not be empty
    - Password must not be empty
    - User Type must not be empty

    Note: The COBOL validates in the order: fname, lname, userid, password,
    usertype — and stops at the first error.
    """
    required_fields = [
        ("first_name", "First Name can NOT be empty..."),
        ("last_name", "Last Name can NOT be empty..."),
        ("user_id", "User ID can NOT be empty..."),
        ("password", "Password can NOT be empty..."),
        ("user_type", "User Type can NOT be empty..."),
    ]

    for field_name, error_msg in required_fields:
        value = ""
        if field_name == "first_name":
            value = user_input.first_name
        elif field_name == "last_name":
            value = user_input.last_name
        elif field_name == "user_id":
            value = user_input.user_id
        elif field_name == "password":
            value = user_input.password
        elif field_name == "user_type":
            value = user_input.user_type

        if not value or not value.strip():
            return ValidationResult(
                is_valid=False,
                error_message=error_msg,
                error_field=field_name,
            )

    return ValidationResult(is_valid=True)


# ---------------------------------------------------------------------------
# Core add-user logic
# ---------------------------------------------------------------------------

def add_user(
    user_input: UserAddInput,
    repo: UserSecurityRepository,
) -> AddUserResult:
    """
    Full add-user workflow: validate fields, then write to repository.

    This is the top-level entry point that mirrors the COBOL program's
    PROCESS-ENTER-KEY paragraph when the user presses Enter.

    Returns an AddUserResult indicating success or the first validation
    error encountered.
    """
    # Step 1: Validate input fields
    validation = validate_user_input(user_input)
    if not validation.is_valid:
        return AddUserResult(
            success=False,
            message=validation.error_message,
        )

    # Step 2: Build the record
    record = UserSecurityRecord(
        user_id=user_input.user_id.strip(),
        first_name=user_input.first_name.strip(),
        last_name=user_input.last_name.strip(),
        password=user_input.password.strip(),
        user_type=user_input.user_type.strip(),
    )

    # Step 3: Write to the repository
    written = repo.add_user(record)
    if not written:
        return AddUserResult(
            success=False,
            message="User ID already exist...",
        )

    # Success — mirrors the STRING statement in WRITE-USER-SEC-FILE
    user_id_display = record.user_id.rstrip()
    return AddUserResult(
        success=True,
        message=f"User {user_id_display} has been added ...",
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


def clear_all_fields() -> UserAddInput:
    """
    Return a blank UserAddInput.

    Corresponds to INITIALIZE-ALL-FIELDS / CLEAR-CURRENT-SCREEN (PF4).
    """
    return UserAddInput()
