"""
COUSR03C - Delete User Program (Python Translation)

Translated from the COBOL program COUSR03C.CBL in the AWS CardDemo
mainframe modernization project. This module implements the business
logic for deleting a user from the USRSEC file.

Original: CICS COBOL program using BMS maps and VSAM files.
This translation separates the pure business logic (validation,
confirmation, deletion) from the CICS presentation layer so the rules
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

PROGRAM_NAME = "COUSR03C"
TRANSACTION_ID = "CU03"

TITLE_01 = "      AWS Mainframe Modernization       "
TITLE_02 = "              CardDemo                  "

MSG_INVALID_KEY = "Invalid key pressed. Please see below..."
MSG_THANK_YOU = "Thank you for using CardDemo application..."
MSG_PRESS_PF5 = "Press PF5 key to delete this user ..."
MSG_CANNOT_DELETE_SELF = "Cannot delete the currently signed-in user..."


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class UserDeleteInput:
    """Fields from the Delete User screen (COUSR3AI)."""
    user_id: str = ""         # USRIDINI PIC X(08) — user to delete
    first_name: str = ""      # FNAMEI   PIC X(20) — display only
    last_name: str = ""       # LNAMEI   PIC X(20) — display only
    user_type: str = ""       # USRTYPEI PIC X(01) — display only


@dataclass
class ValidationResult:
    """Outcome of a validation step."""
    is_valid: bool = True
    error_message: str = ""
    error_field: str = ""


@dataclass
class LookupUserResult:
    """Outcome of looking up a user for deletion confirmation."""
    success: bool = False
    message: str = ""
    record: Optional[UserSecurityRecord] = None


@dataclass
class DeleteUserResult:
    """Outcome of the delete-user operation."""
    success: bool = False
    message: str = ""


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_user_id(user_id: str) -> ValidationResult:
    """
    Validate that a user ID was provided.

    Business rule (from PROCESS-ENTER-KEY / DELETE-USER-INFO):
    - User ID must not be empty.
    """
    if not user_id or not user_id.strip():
        return ValidationResult(
            is_valid=False,
            error_message="User ID can NOT be empty...",
            error_field="user_id",
        )
    return ValidationResult(is_valid=True)


# ---------------------------------------------------------------------------
# Lookup user for deletion confirmation
# ---------------------------------------------------------------------------

def lookup_user_for_delete(
    user_id: str,
    repo: UserSecurityRepository,
) -> LookupUserResult:
    """
    Look up a user record for deletion confirmation.

    Corresponds to PROCESS-ENTER-KEY: validate user ID, read the record,
    populate the screen display fields.
    """
    id_result = validate_user_id(user_id)
    if not id_result.is_valid:
        return LookupUserResult(
            success=False,
            message=id_result.error_message,
        )

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
# Core delete-user logic
# ---------------------------------------------------------------------------

def delete_user(
    user_id: str,
    repo: UserSecurityRepository,
    current_user_id: str = "",
) -> DeleteUserResult:
    """
    Full delete-user workflow: validate, read, delete.

    This is the top-level entry point that mirrors the COBOL program's
    DELETE-USER-INFO paragraph (triggered by PF5).

    The *current_user_id* parameter implements the business rule that
    prevents deleting the currently signed-in user.

    Returns a DeleteUserResult indicating success or the error.
    """
    # Step 1: Validate user ID
    id_result = validate_user_id(user_id)
    if not id_result.is_valid:
        return DeleteUserResult(
            success=False,
            message=id_result.error_message,
        )

    uid = user_id.strip()

    # Step 2: Prevent self-deletion
    if current_user_id and uid == current_user_id.strip():
        return DeleteUserResult(
            success=False,
            message=MSG_CANNOT_DELETE_SELF,
        )

    # Step 3: Read-for-update to confirm existence
    record = repo.lookup_user(uid)
    if record is None:
        return DeleteUserResult(
            success=False,
            message="User ID NOT found...",
        )

    # Step 4: Delete
    deleted = repo.delete_user(uid)
    if not deleted:
        return DeleteUserResult(
            success=False,
            message="Unable to Update User...",  # matches COBOL error text
        )

    # Success — mirrors the STRING statement in DELETE-USER-SEC-FILE
    user_id_display = uid.rstrip()
    return DeleteUserResult(
        success=True,
        message=f"User {user_id_display} has been deleted ...",
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


def clear_all_fields() -> UserDeleteInput:
    """
    Return a blank UserDeleteInput.

    Corresponds to INITIALIZE-ALL-FIELDS / CLEAR-CURRENT-SCREEN (PF4).
    """
    return UserDeleteInput()
