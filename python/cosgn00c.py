"""
COSGN00C - Sign-on Screen Program (Python Translation)

Translated from the COBOL program COSGN00C.CBL in the AWS CardDemo
mainframe modernization project. This module implements the business
logic for user authentication (sign-on) in the CardDemo application.

Original: CICS COBOL program using BMS map COSGN0A and VSAM file USRSEC.
This translation separates the pure business logic (credential validation,
user lookup, routing) from the CICS presentation layer so the rules can
be tested and reused independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Constants (from copybooks COTTL01Y, CSMSG01Y, and working storage)
# ---------------------------------------------------------------------------

PROGRAM_NAME = "COSGN00C"
TRANSACTION_ID = "CC00"

TITLE_01 = "      AWS Mainframe Modernization       "
TITLE_02 = "              CardDemo                  "

MSG_THANK_YOU = "Thank you for using CardDemo application..."
MSG_INVALID_KEY = "Invalid key pressed. Please see below..."


# ---------------------------------------------------------------------------
# Data structures (from copybooks)
# ---------------------------------------------------------------------------

@dataclass
class UserSecurityRecord:
    """User security record layout (CSUSR01Y - 80 bytes).

    Maps to the USRSEC VSAM KSDS file keyed by SEC-USR-ID.
    """
    sec_usr_id: str = ""       # SEC-USR-ID     PIC X(08)
    sec_usr_fname: str = ""    # SEC-USR-FNAME   PIC X(20)
    sec_usr_lname: str = ""    # SEC-USR-LNAME   PIC X(20)
    sec_usr_pwd: str = ""      # SEC-USR-PWD     PIC X(08)
    sec_usr_type: str = ""     # SEC-USR-TYPE    PIC X(01)  'A' or 'U'


@dataclass
class CommArea:
    """Communication area for CardDemo programs (COCOM01Y).

    Passed between programs via CICS COMMAREA to maintain session state.
    """
    cdemo_from_tranid: str = ""      # CDEMO-FROM-TRANID    PIC X(04)
    cdemo_from_program: str = ""     # CDEMO-FROM-PROGRAM   PIC X(08)
    cdemo_to_tranid: str = ""        # CDEMO-TO-TRANID      PIC X(04)
    cdemo_to_program: str = ""       # CDEMO-TO-PROGRAM     PIC X(08)
    cdemo_user_id: str = ""          # CDEMO-USER-ID        PIC X(08)
    cdemo_user_type: str = ""        # CDEMO-USER-TYPE      PIC X(01)
    cdemo_pgm_context: int = 0       # CDEMO-PGM-CONTEXT    PIC 9(01)


@dataclass
class SignonInput:
    """User-supplied fields from the sign-on screen (COSGN0AI)."""
    user_id: str = ""     # USERIDI OF COSGN0AI
    password: str = ""    # PASSWDI OF COSGN0AI


@dataclass
class SignonResult:
    """Outcome of a sign-on attempt."""
    success: bool = False
    error_message: str = ""
    error_field: str = ""          # 'user_id' or 'password'
    target_program: str = ""       # program to XCTL to on success
    commarea: Optional[CommArea] = None


# ---------------------------------------------------------------------------
# Repository interface (abstracts VSAM USRSEC file I/O)
# ---------------------------------------------------------------------------

class UserSecurityRepository:
    """Abstract interface for user security data access.

    In the original COBOL program this is a CICS READ against the USRSEC
    VSAM KSDS file keyed by user ID. Concrete implementations can use a
    database, in-memory dict, or any other store.
    """

    def lookup_user(self, user_id: str) -> Optional[UserSecurityRecord]:
        """Look up a user by their ID.

        Corresponds to CICS READ on USRSEC with RIDFLD = user_id.
        Returns None if the user is not found (RESP=13 NOTFND).
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# In-memory repository for testing
# ---------------------------------------------------------------------------

class InMemoryUserSecurityRepository(UserSecurityRepository):
    """Simple in-memory implementation backed by a Python dict."""

    def __init__(self) -> None:
        self.users: dict[str, UserSecurityRecord] = {}

    def add_user(self, record: UserSecurityRecord) -> None:
        """Register a user record for lookup."""
        self.users[record.sec_usr_id] = record

    def lookup_user(self, user_id: str) -> Optional[UserSecurityRecord]:
        return self.users.get(user_id)


# ---------------------------------------------------------------------------
# Validation and authentication functions
# ---------------------------------------------------------------------------

def validate_signon_input(signon_input: SignonInput) -> SignonResult:
    """Validate that both user ID and password are provided.

    Business rules (from PROCESS-ENTER-KEY):
    - User ID must not be empty or spaces.
    - Password must not be empty or spaces.
    Both fields are uppercased before further processing.
    """
    # Uppercase both fields (FUNCTION UPPER-CASE in COBOL)
    user_id = signon_input.user_id.strip().upper()
    password = signon_input.password.strip().upper()

    if user_id == "":
        return SignonResult(
            success=False,
            error_message="Please enter User ID ...",
            error_field="user_id",
        )

    if password == "":
        return SignonResult(
            success=False,
            error_message="Please enter Password ...",
            error_field="password",
        )

    # Store uppercased values back for downstream use
    signon_input.user_id = user_id
    signon_input.password = password

    return SignonResult(success=True)


def authenticate_user(
    signon_input: SignonInput,
    repo: UserSecurityRepository,
) -> SignonResult:
    """Authenticate a user against the security file.

    Business rules (from READ-USER-SEC-FILE):
    1. Look up user by ID in the USRSEC file.
    2. If not found (RESP=13): return 'User not found' error.
    3. If found but password doesn't match: return 'Wrong Password' error.
    4. If found and password matches:
       - Populate COMMAREA with user info.
       - Route admin users (type 'A') to COADM01C.
       - Route regular users (type 'U') to COMEN01C.
    """
    user_record = repo.lookup_user(signon_input.user_id)

    if user_record is None:
        return SignonResult(
            success=False,
            error_message="User not found. Try again ...",
            error_field="user_id",
        )

    # Compare password (COBOL: IF SEC-USR-PWD = WS-USER-PWD)
    if user_record.sec_usr_pwd != signon_input.password:
        return SignonResult(
            success=False,
            error_message="Wrong Password. Try again ...",
            error_field="password",
        )

    # Build COMMAREA for successful login
    commarea = CommArea(
        cdemo_from_tranid=TRANSACTION_ID,
        cdemo_from_program=PROGRAM_NAME,
        cdemo_user_id=signon_input.user_id,
        cdemo_user_type=user_record.sec_usr_type,
        cdemo_pgm_context=0,  # CDEMO-PGM-ENTER (initial entry)
    )

    # Route based on user type
    # 'A' → COADM01C (admin menu), anything else → COMEN01C (user menu)
    if user_record.sec_usr_type == "A":
        target_program = "COADM01C"
    else:
        target_program = "COMEN01C"

    return SignonResult(
        success=True,
        target_program=target_program,
        commarea=commarea,
    )


def process_signon(
    signon_input: SignonInput,
    repo: UserSecurityRepository,
) -> SignonResult:
    """Full sign-on workflow: validate input then authenticate.

    This is the top-level entry point that mirrors the COBOL program's
    PROCESS-ENTER-KEY paragraph when the user presses Enter.

    Returns a SignonResult indicating success (with target program and
    COMMAREA) or the first validation/authentication error encountered.
    """
    # Step 1: Validate that credentials are provided
    validation = validate_signon_input(signon_input)
    if not validation.success:
        return validation

    # Step 2: Authenticate against the user security file
    return authenticate_user(signon_input, repo)


# ---------------------------------------------------------------------------
# Screen / header helpers
# ---------------------------------------------------------------------------

def get_header_info() -> dict[str, str]:
    """Build header information for the sign-on screen.

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
