"""
COUSR02C - Update User Program (Python Translation)

Translated from the COBOL program COUSR02C.CBL in the AWS CardDemo
mainframe modernization project. This module implements the business
logic for updating an existing user in the USRSEC file.

Original: CICS COBOL program using BMS maps and VSAM files.
This translation separates the pure business logic (validation, change
detection, record update) from the CICS presentation layer so the rules
can be tested and reused independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from user_security_repository import (
    UserSecurityRecord,
    UserSecurityRepository,
)


# ---------------------------------------------------------------------------
# Constants (from copybooks COTTL01Y, CSMSG01Y)
# ---------------------------------------------------------------------------

PROGRAM_NAME = "COUSR02C"
TRANSACTION_ID = "CU02"

TITLE_01 = "      AWS Mainframe Modernization       "
TITLE_02 = "              CardDemo                  "

MSG_INVALID_KEY = "Invalid key pressed. Please see below..."
MSG_THANK_YOU = "Thank you for using CardDemo application..."
MSG_PRESS_PF5 = "Press PF5 key to save your updates ..."
MSG_NO_MODIFICATION = "Please modify to update ..."


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class UserUpdateInput:
    """All user-supplied fields from the Update User screen (COUSR2AI)."""
    user_id: str = ""         # USRIDINI PIC X(08) — read-only key
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
class LookupUserResult:
    """Outcome of looking up a user for editing."""
    success: bool = False
    message: str = ""
    record: Optional[UserSecurityRecord] = None


@dataclass
class UpdateUserResult:
    """Outcome of the update-user operation."""
    success: bool = False
    message: str = ""
    modified: bool = False


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_user_id(user_id: str) -> ValidationResult:
    """
    Validate that a user ID was provided.

    Business rule (from PROCESS-ENTER-KEY):
    - User ID must not be empty.
    """
    if not user_id or not user_id.strip():
        return ValidationResult(
            is_valid=False,
            error_message="User ID can NOT be empty...",
            error_field="user_id",
        )
    return ValidationResult(is_valid=True)


def validate_update_fields(user_input: UserUpdateInput) -> ValidationResult:
    """
    Validate all fields for updating a user.

    Business rules (from UPDATE-USER-INFO):
    - User ID must not be empty
    - First Name must not be empty
    - Last Name must not be empty
    - Password must not be empty
    - User Type must not be empty

    Validates in COBOL order, stops at first error.
    """
    required_fields = [
        ("user_id", "User ID can NOT be empty..."),
        ("first_name", "First Name can NOT be empty..."),
        ("last_name", "Last Name can NOT be empty..."),
        ("password", "Password can NOT be empty..."),
        ("user_type", "User Type can NOT be empty..."),
    ]

    for field_name, error_msg in required_fields:
        value = ""
        if field_name == "user_id":
            value = user_input.user_id
        elif field_name == "first_name":
            value = user_input.first_name
        elif field_name == "last_name":
            value = user_input.last_name
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
# Lookup user for editing
# ---------------------------------------------------------------------------

def lookup_user_for_update(
    user_id: str,
    repo: UserSecurityRepository,
) -> LookupUserResult:
    """
    Look up a user record for updating.

    Corresponds to PROCESS-ENTER-KEY: validate user ID, read the record,
    populate the screen fields.
    """
    # Validate user ID
    id_result = validate_user_id(user_id)
    if not id_result.is_valid:
        return LookupUserResult(
            success=False,
            message=id_result.error_message,
        )

    # Read the user record
    record = repo.lookup_user(user_id.strip())
    if record is None:
        return LookupUserResult(
            success=False,
            message="User ID NOT found...",
        )

    return LookupUserResult(
        success=True,
        message=MSG_PRESS_PF5,
        record=record,
    )


# ---------------------------------------------------------------------------
# Core update-user logic
# ---------------------------------------------------------------------------

def update_user(
    user_input: UserUpdateInput,
    repo: UserSecurityRepository,
) -> UpdateUserResult:
    """
    Full update-user workflow: validate, detect changes, write update.

    This is the top-level entry point that mirrors the COBOL program's
    UPDATE-USER-INFO paragraph (triggered by PF5 or PF3).

    Returns an UpdateUserResult indicating success, no-modification,
    or the first validation error encountered.
    """
    # Step 1: Validate all fields
    validation = validate_update_fields(user_input)
    if not validation.is_valid:
        return UpdateUserResult(
            success=False,
            message=validation.error_message,
        )

    # Step 2: Read the existing record
    existing = repo.lookup_user(user_input.user_id.strip())
    if existing is None:
        return UpdateUserResult(
            success=False,
            message="User ID NOT found...",
        )

    # Step 3: Detect changes (mirrors the individual IF comparisons in COBOL)
    modified = False
    if user_input.first_name.strip() != existing.first_name.strip():
        existing.first_name = user_input.first_name.strip()
        modified = True
    if user_input.last_name.strip() != existing.last_name.strip():
        existing.last_name = user_input.last_name.strip()
        modified = True
    if user_input.password.strip() != existing.password.strip():
        existing.password = user_input.password.strip()
        modified = True
    if user_input.user_type.strip() != existing.user_type.strip():
        existing.user_type = user_input.user_type.strip()
        modified = True

    if not modified:
        return UpdateUserResult(
            success=False,
            message=MSG_NO_MODIFICATION,
            modified=False,
        )

    # Step 4: Write the update
    updated = repo.update_user(existing)
    if not updated:
        return UpdateUserResult(
            success=False,
            message="Unable to Update User...",
        )

    # Success — mirrors the STRING statement in UPDATE-USER-SEC-FILE
    user_id_display = existing.user_id.rstrip()
    return UpdateUserResult(
        success=True,
        message=f"User {user_id_display} has been updated ...",
        modified=True,
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


def clear_all_fields() -> UserUpdateInput:
    """
    Return a blank UserUpdateInput.

    Corresponds to INITIALIZE-ALL-FIELDS / CLEAR-CURRENT-SCREEN (PF4).
    """
    return UserUpdateInput()
