"""
COBIL00C - Bill Payment Program (Python Translation)

Translated from the COBOL program COBIL00C.CBL in the AWS CardDemo
mainframe modernization project. This module implements the business
logic for paying an account balance and creating a payment transaction.

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

PROGRAM_NAME = "COBIL00C"
TRANSACTION_ID = "CB00"

TITLE_01 = "      AWS Mainframe Modernization       "
TITLE_02 = "              CardDemo                  "

MSG_INVALID_KEY = "Invalid key pressed. Please see below..."

# Payment transaction defaults (from COBIL00C PROCESS-ENTER-KEY)
PAYMENT_TRAN_TYPE_CD = "02"
PAYMENT_TRAN_CAT_CD = "0002"
PAYMENT_TRAN_SOURCE = "POS TERM"
PAYMENT_TRAN_DESC = "BILL PAYMENT - ONLINE"
PAYMENT_MERCHANT_ID = "999999999"
PAYMENT_MERCHANT_NAME = "BILL PAYMENT"
PAYMENT_MERCHANT_CITY = "N/A"
PAYMENT_MERCHANT_ZIP = "N/A"


# ---------------------------------------------------------------------------
# Data structures (from copybooks)
# ---------------------------------------------------------------------------

@dataclass
class AccountRecord:
    """Account record layout (CVACT01Y - 300 bytes)."""
    acct_id: str = ""                   # PIC 9(11)
    acct_active_status: str = ""        # PIC X(01)
    acct_curr_bal: float = 0.0          # PIC S9(10)V99
    acct_credit_limit: float = 0.0      # PIC S9(10)V99
    acct_cash_credit_limit: float = 0.0  # PIC S9(10)V99
    acct_open_date: str = ""            # PIC X(10)
    acct_expiration_date: str = ""      # PIC X(10)
    acct_reissue_date: str = ""         # PIC X(10)
    acct_curr_cyc_credit: float = 0.0   # PIC S9(10)V99
    acct_curr_cyc_debit: float = 0.0    # PIC S9(10)V99
    acct_addr_zip: str = ""             # PIC X(10)
    acct_group_id: str = ""             # PIC X(10)


@dataclass
class CardXrefRecord:
    """Card cross-reference record (CVACT03Y - 50 bytes)."""
    card_num: str = ""      # XREF-CARD-NUM  PIC X(16)
    cust_id: str = ""       # XREF-CUST-ID   PIC 9(09)
    acct_id: str = ""       # XREF-ACCT-ID   PIC 9(11)


@dataclass
class TransactionRecord:
    """Transaction record layout (CVTRA05Y - 350 bytes)."""
    tran_id: str = ""               # PIC X(16)
    tran_type_cd: str = ""          # PIC X(02)
    tran_cat_cd: str = ""           # PIC 9(04)
    tran_source: str = ""           # PIC X(10)
    tran_desc: str = ""             # PIC X(100)
    tran_amt: float = 0.0           # PIC S9(09)V99
    tran_merchant_id: str = ""      # PIC 9(09)
    tran_merchant_name: str = ""    # PIC X(50)
    tran_merchant_city: str = ""    # PIC X(50)
    tran_merchant_zip: str = ""     # PIC X(10)
    tran_card_num: str = ""         # PIC X(16)
    tran_orig_ts: str = ""          # PIC X(26)
    tran_proc_ts: str = ""          # PIC X(26)


@dataclass
class BillPaymentResult:
    """Outcome of a bill payment operation."""
    success: bool = False
    message: str = ""
    tran_id: str = ""
    new_balance: float = 0.0
    display_balance: str = ""


# ---------------------------------------------------------------------------
# Repository interfaces (abstracts VSAM file I/O)
# ---------------------------------------------------------------------------

class AccountRepository:
    """
    Abstract interface for account data access.

    In the original COBOL program these are CICS READ / REWRITE
    operations against VSAM files.
    """

    def read_account(self, acct_id: str) -> Optional[AccountRecord]:
        """
        Read an account by its ID.

        Corresponds to CICS READ on ACCTDAT file.
        Returns None if the account is not found.
        """
        raise NotImplementedError

    def update_account(self, account: AccountRecord) -> bool:
        """
        Update an account record.

        Corresponds to CICS REWRITE on ACCTDAT file.
        Returns True on success, False on failure.
        """
        raise NotImplementedError


class CardXrefRepository:
    """
    Abstract interface for card cross-reference data access.
    """

    def lookup_by_account(self, acct_id: str) -> Optional[CardXrefRecord]:
        """
        Look up a card cross-reference record by account ID.

        Corresponds to READ on CXACAIX (alternate index keyed by account).
        Returns None if the account is not found.
        """
        raise NotImplementedError


class TransactionRepository:
    """
    Abstract interface for transaction data access.
    """

    def get_max_transaction_id(self) -> int:
        """
        Return the highest existing transaction ID as an integer.

        Corresponds to STARTBR with HIGH-VALUES followed by READPREV.
        Returns 0 if the file is empty.
        """
        raise NotImplementedError

    def write_transaction(self, record: TransactionRecord) -> bool:
        """
        Write a new transaction record.

        Corresponds to CICS WRITE to the TRANSACT file.
        Returns True on success, False if a duplicate key exists.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# In-memory repositories for testing
# ---------------------------------------------------------------------------

class InMemoryAccountRepository(AccountRepository):
    """Simple in-memory account repository."""

    def __init__(self) -> None:
        self.accounts: dict[str, AccountRecord] = {}

    def add_account(self, account: AccountRecord) -> None:
        """Insert an account record directly (for test setup)."""
        self.accounts[account.acct_id] = account

    def read_account(self, acct_id: str) -> Optional[AccountRecord]:
        return self.accounts.get(acct_id)

    def update_account(self, account: AccountRecord) -> bool:
        if account.acct_id not in self.accounts:
            return False
        self.accounts[account.acct_id] = account
        return True


class InMemoryCardXrefRepository(CardXrefRepository):
    """Simple in-memory card cross-reference repository."""

    def __init__(self) -> None:
        self.xref_by_account: dict[str, CardXrefRecord] = {}

    def add_xref(self, record: CardXrefRecord) -> None:
        """Insert a cross-reference record (for test setup)."""
        self.xref_by_account[record.acct_id] = record

    def lookup_by_account(self, acct_id: str) -> Optional[CardXrefRecord]:
        return self.xref_by_account.get(acct_id)


class InMemoryTransactionRepository(TransactionRepository):
    """Simple in-memory transaction repository."""

    def __init__(self) -> None:
        self.transactions: dict[str, TransactionRecord] = {}

    def add_transaction(self, record: TransactionRecord) -> None:
        """Insert a transaction record directly (for test setup)."""
        self.transactions[record.tran_id] = record

    def get_max_transaction_id(self) -> int:
        if not self.transactions:
            return 0
        return max(int(tid) for tid in self.transactions)

    def write_transaction(self, record: TransactionRecord) -> bool:
        if record.tran_id in self.transactions:
            return False  # duplicate key
        self.transactions[record.tran_id] = record
        return True


# ---------------------------------------------------------------------------
# Validation functions
# ---------------------------------------------------------------------------

def validate_account_id(acct_id_input: str) -> tuple[bool, str]:
    """
    Validate the account ID input.

    Business rules (from PROCESS-ENTER-KEY):
    - Account ID cannot be empty or blank.

    Returns:
        (is_valid, error_message)
    """
    stripped = acct_id_input.strip()
    if not stripped:
        return (False, "Acct ID can NOT be empty...")

    return (True, "")


def validate_confirmation(confirm_input: str) -> tuple[str, str]:
    """
    Validate and classify the confirmation input.

    Business rules:
    - 'Y' or 'y': confirmed
    - 'N' or 'n': cancelled
    - Blank/empty: not yet confirmed (show balance)
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

    return ("invalid", "Invalid value. Valid values are (Y/N)...")


# ---------------------------------------------------------------------------
# Core bill payment logic
# ---------------------------------------------------------------------------

def format_balance(balance: float) -> str:
    """
    Format an account balance for display.

    Corresponds to MOVE ACCT-CURR-BAL TO WS-CURR-BAL where
    WS-CURR-BAL is PIC +9999999999.99.
    """
    sign = "+" if balance >= 0 else "-"
    return f"{sign}{abs(balance):013.2f}"


def generate_transaction_id(tran_repo: TransactionRepository) -> str:
    """
    Generate the next transaction ID.

    Business rule: browse to end of TRANSACT file, read last record,
    add 1. If file is empty, start from 1.
    """
    max_id = tran_repo.get_max_transaction_id()
    next_id = max_id + 1
    return str(next_id).zfill(16)


def get_current_timestamp() -> str:
    """
    Generate a current timestamp string.

    Corresponds to GET-CURRENT-TIMESTAMP which uses CICS ASKTIME/FORMATTIME
    to produce YYYY-MM-DD HH:MM:SS.000000 format.
    """
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S.000000")


def process_bill_payment(
    acct_id_input: str,
    confirm_input: str,
    acct_repo: AccountRepository,
    xref_repo: CardXrefRepository,
    tran_repo: TransactionRepository,
) -> BillPaymentResult:
    """
    Full bill payment workflow.

    Corresponds to the PROCESS-ENTER-KEY paragraph in COBIL00C.

    Args:
        acct_id_input: Account ID entered by the user.
        confirm_input: Confirmation flag (Y/N/blank).
        acct_repo: Account data repository.
        xref_repo: Card cross-reference repository.
        tran_repo: Transaction repository.

    Returns:
        BillPaymentResult indicating success or the error encountered.
    """
    # Step 1: Validate account ID
    is_valid, error = validate_account_id(acct_id_input)
    if not is_valid:
        return BillPaymentResult(success=False, message=error)

    acct_id = acct_id_input.strip()

    # Step 2: Validate confirmation
    conf_status, conf_error = validate_confirmation(confirm_input)
    if conf_status == "invalid":
        return BillPaymentResult(success=False, message=conf_error)

    if conf_status == "cancelled":
        return BillPaymentResult(success=False, message="")

    # Step 3: Read account
    account = acct_repo.read_account(acct_id)
    if account is None:
        return BillPaymentResult(
            success=False,
            message="Account ID NOT found...",
        )

    display_bal = format_balance(account.acct_curr_bal)

    # Step 4: Check balance
    if account.acct_curr_bal <= 0:
        return BillPaymentResult(
            success=False,
            message="You have nothing to pay...",
            display_balance=display_bal,
        )

    # Step 5: If not confirmed yet, prompt
    if conf_status == "pending":
        return BillPaymentResult(
            success=False,
            message="Confirm to make a bill payment...",
            display_balance=display_bal,
        )

    # Step 6: Process the payment (confirmed)
    # 6a: Look up card number
    xref = xref_repo.lookup_by_account(acct_id)
    if xref is None:
        return BillPaymentResult(
            success=False,
            message="Account ID NOT found...",
            display_balance=display_bal,
        )

    # 6b: Generate transaction ID
    tran_id = generate_transaction_id(tran_repo)

    # 6c: Build payment transaction record
    timestamp = get_current_timestamp()
    payment_record = TransactionRecord(
        tran_id=tran_id,
        tran_type_cd=PAYMENT_TRAN_TYPE_CD,
        tran_cat_cd=PAYMENT_TRAN_CAT_CD,
        tran_source=PAYMENT_TRAN_SOURCE,
        tran_desc=PAYMENT_TRAN_DESC,
        tran_amt=account.acct_curr_bal,
        tran_card_num=xref.card_num,
        tran_merchant_id=PAYMENT_MERCHANT_ID,
        tran_merchant_name=PAYMENT_MERCHANT_NAME,
        tran_merchant_city=PAYMENT_MERCHANT_CITY,
        tran_merchant_zip=PAYMENT_MERCHANT_ZIP,
        tran_orig_ts=timestamp,
        tran_proc_ts=timestamp,
    )

    # 6d: Write transaction
    written = tran_repo.write_transaction(payment_record)
    if not written:
        return BillPaymentResult(
            success=False,
            message="Tran ID already exist...",
            display_balance=display_bal,
        )

    # 6e: Update account balance
    payment_amount = account.acct_curr_bal
    account.acct_curr_bal = account.acct_curr_bal - payment_amount
    updated = acct_repo.update_account(account)
    if not updated:
        return BillPaymentResult(
            success=False,
            message="Unable to Update Account...",
        )

    # 6f: Success
    tran_id_display = tran_id.lstrip("0") or "0"
    return BillPaymentResult(
        success=True,
        message=(
            f"Payment successful. "
            f"Your Transaction ID is {tran_id_display}."
        ),
        tran_id=tran_id,
        new_balance=account.acct_curr_bal,
        display_balance=format_balance(account.acct_curr_bal),
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
        "acct_id": "",
        "cur_bal": "",
        "confirm": "",
    }
