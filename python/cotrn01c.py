"""
COTRN01C - Transaction View Program (Python Translation)

Translated from the COBOL program COTRN01C.CBL in the AWS CardDemo
mainframe modernization project. This module implements the business
logic for viewing a single transaction's details (read-only).

Original: CICS COBOL program using BMS maps and VSAM files.
This translation separates the pure business logic from the CICS
presentation layer so the rules can be tested and reused independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Constants (from copybooks COTTL01Y, CSMSG01Y)
# ---------------------------------------------------------------------------

PROGRAM_NAME = "COTRN01C"
TRANSACTION_ID = "CT01"

TITLE_01 = "      AWS Mainframe Modernization       "
TITLE_02 = "              CardDemo                  "

MSG_INVALID_KEY = "Invalid key pressed. Please see below..."


# ---------------------------------------------------------------------------
# Data structures (from copybooks)
# ---------------------------------------------------------------------------

@dataclass
class TransactionRecord:
    """Transaction record layout (CVTRA05Y - 350 bytes)."""
    tran_id: str = ""               # PIC X(16)  primary key
    tran_type_cd: str = ""          # PIC X(02)  transaction type code
    tran_cat_cd: str = ""           # PIC 9(04)  transaction category code
    tran_source: str = ""           # PIC X(10)  transaction source
    tran_desc: str = ""             # PIC X(100) transaction description
    tran_amt: float = 0.0           # PIC S9(09)V99  signed amount
    tran_merchant_id: str = ""      # PIC 9(09)  merchant identifier
    tran_merchant_name: str = ""    # PIC X(50)  merchant name
    tran_merchant_city: str = ""    # PIC X(50)  merchant city
    tran_merchant_zip: str = ""     # PIC X(10)  merchant zip code
    tran_card_num: str = ""         # PIC X(16)  card number
    tran_orig_ts: str = ""          # PIC X(26)  origination timestamp
    tran_proc_ts: str = ""          # PIC X(26)  processing timestamp


@dataclass
class TransactionViewResult:
    """Outcome of a transaction view operation."""
    success: bool = False
    message: str = ""
    record: Optional[TransactionRecord] = None
    formatted_amt: str = ""


# ---------------------------------------------------------------------------
# Repository interface (abstracts VSAM file I/O)
# ---------------------------------------------------------------------------

class TransactionRepository:
    """
    Abstract interface for transaction data access.

    In the original COBOL program this is a CICS READ operation against
    the TRANSACT VSAM KSDS file. Concrete implementations can use a
    database, in-memory dict, or any other store.
    """

    def read_transaction(self, tran_id: str) -> Optional[TransactionRecord]:
        """
        Read a transaction by its ID.

        Corresponds to CICS READ on TRANSACT file with RIDFLD(TRAN-ID).
        Returns None if the transaction is not found.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# In-memory repository for testing
# ---------------------------------------------------------------------------

class InMemoryTransactionRepository(TransactionRepository):
    """Simple in-memory implementation backed by a Python dict."""

    def __init__(self) -> None:
        self.transactions: dict[str, TransactionRecord] = {}

    def add_transaction(self, record: TransactionRecord) -> None:
        """Insert a transaction record directly (for test setup)."""
        self.transactions[record.tran_id] = record

    def read_transaction(self, tran_id: str) -> Optional[TransactionRecord]:
        return self.transactions.get(tran_id)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_tran_id(tran_id_input: str) -> tuple[bool, str]:
    """
    Validate the transaction ID input.

    Business rules (from PROCESS-ENTER-KEY):
    - Transaction ID cannot be empty or blank.

    Returns:
        (is_valid, error_message)
    """
    stripped = tran_id_input.strip()
    if not stripped:
        return (False, "Tran ID can NOT be empty...")

    return (True, "")


# ---------------------------------------------------------------------------
# Core view logic
# ---------------------------------------------------------------------------

def format_amount(amount: float) -> str:
    """
    Format a transaction amount for display.

    Corresponds to MOVE TRAN-AMT TO WS-TRAN-AMT where
    WS-TRAN-AMT is PIC +99999999.99.
    """
    sign = "+" if amount >= 0 else "-"
    return f"{sign}{abs(amount):011.2f}"


def view_transaction(
    tran_id_input: str,
    repo: TransactionRepository,
) -> TransactionViewResult:
    """
    Look up and return a transaction by ID.

    Corresponds to the PROCESS-ENTER-KEY paragraph.

    Args:
        tran_id_input: Transaction ID entered by the user.
        repo: Transaction data repository.

    Returns:
        TransactionViewResult with the record if found, or an error message.
    """
    # Step 1: Validate input
    is_valid, error = validate_tran_id(tran_id_input)
    if not is_valid:
        return TransactionViewResult(success=False, message=error)

    # Step 2: Normalise and read
    tran_id = tran_id_input.strip()
    record = repo.read_transaction(tran_id)

    if record is None:
        return TransactionViewResult(
            success=False,
            message="Transaction ID NOT found...",
        )

    # Step 3: Format amount for display
    formatted_amt = format_amount(record.tran_amt)

    return TransactionViewResult(
        success=True,
        record=record,
        formatted_amt=formatted_amt,
    )


def clear_all_fields() -> dict[str, str]:
    """
    Return a dictionary of blank fields.

    Corresponds to INITIALIZE-ALL-FIELDS / CLEAR-CURRENT-SCREEN (PF4).
    """
    return {
        "tran_id_input": "",
        "tran_id": "",
        "card_num": "",
        "type_cd": "",
        "cat_cd": "",
        "source": "",
        "amount": "",
        "description": "",
        "orig_date": "",
        "proc_date": "",
        "merchant_id": "",
        "merchant_name": "",
        "merchant_city": "",
        "merchant_zip": "",
    }


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
