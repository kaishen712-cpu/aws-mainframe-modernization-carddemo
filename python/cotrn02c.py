"""
COTRN02C - Add Transaction Program (Python Translation)

Translated from the COBOL program COTRN02C.CBL in the AWS CardDemo
mainframe modernization project. This module implements the business
logic for adding a new credit card transaction.

Original: CICS COBOL program using BMS maps and VSAM files.
This translation separates the pure business logic (validation, ID
generation, record building) from the CICS presentation layer so
the rules can be tested and reused independently.

Refactored to use shared foundation layer (models, repositories, utils).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from python.models.records import (
    CardXrefRecord as SharedCardXrefRecord,
    TransactionRecord,
)
from python.repositories.base import (
    CardXrefRepository,
    TransactionRepository as SharedTransactionRepository,
)
from python.utils.date_validation import is_valid_calendar_date


# ---------------------------------------------------------------------------
# Constants (from copybooks COTTL01Y, CSMSG01Y)
# ---------------------------------------------------------------------------

PROGRAM_NAME = "COTRN02C"
TRANSACTION_ID = "CT02"

TITLE_01 = "      AWS Mainframe Modernization       "
TITLE_02 = "              CardDemo                  "

MSG_INVALID_KEY = "Invalid key pressed. Please see below..."
MSG_THANK_YOU = "Thank you for using CardDemo application..."

# Date format expected by the program
DATE_FORMAT = "YYYY-MM-DD"

# Amount format pattern: sign, 8 digits, dot, 2 digits  e.g. +00000100.00
AMOUNT_PATTERN = re.compile(r"^[+\-]\d{8}\.\d{2}$")

# Date format pattern: YYYY-MM-DD
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------------------------------------------------------------------------
# Data structures (from copybooks)
# ---------------------------------------------------------------------------

@dataclass
class CardXrefRecord:
    """Card cross-reference record (CVACT03Y - 50 bytes).

    Thin wrapper providing COTRN02C-style field names while backed by
    the shared foundation CardXrefRecord.
    """
    card_num: str = ""      # XREF-CARD-NUM  PIC X(16)
    cust_id: str = ""       # XREF-CUST-ID   PIC 9(09)
    acct_id: str = ""       # XREF-ACCT-ID   PIC 9(11)

    @classmethod
    def from_shared(cls, shared: SharedCardXrefRecord) -> CardXrefRecord:
        """Create from a shared foundation CardXrefRecord."""
        return cls(
            card_num=shared.xref_card_num,
            cust_id=shared.xref_cust_id,
            acct_id=shared.xref_acct_id,
        )

    def to_shared(self) -> SharedCardXrefRecord:
        """Convert to a shared foundation CardXrefRecord."""
        return SharedCardXrefRecord(
            xref_card_num=self.card_num,
            xref_cust_id=self.cust_id,
            xref_acct_id=self.acct_id,
        )


# TransactionRecord is imported directly from the shared foundation
# (field names are identical, no wrapper needed)


@dataclass
class TransactionInput:
    """All user-supplied fields from the Add Transaction screen (COTRN2AI)."""
    acct_id: str = ""               # ACTIDINI  - Account ID
    card_num: str = ""              # CARDNINI  - Card Number
    tran_type_cd: str = ""          # TTYPCDI   - Transaction Type Code
    tran_cat_cd: str = ""           # TCATCDI   - Transaction Category Code
    tran_source: str = ""           # TRNSRCI   - Source
    tran_desc: str = ""             # TDESCI    - Description
    tran_amt: str = ""              # TRNAMTI   - Amount string
    orig_date: str = ""             # TORIGDTI  - Origination Date
    proc_date: str = ""             # TPROCDTI  - Processing Date
    merchant_id: str = ""           # MIDI      - Merchant ID
    merchant_name: str = ""         # MNAMEI    - Merchant Name
    merchant_city: str = ""         # MCITYI    - Merchant City
    merchant_zip: str = ""          # MZIPI     - Merchant Zip
    confirm: str = ""               # CONFIRMI  - Confirmation (Y/N)


@dataclass
class ValidationResult:
    """Outcome of a validation step."""
    is_valid: bool = True
    error_message: str = ""
    error_field: str = ""           # name of the field with the error


@dataclass
class AddTransactionResult:
    """Outcome of the add-transaction operation."""
    success: bool = False
    message: str = ""
    tran_id: str = ""               # assigned transaction ID on success


# ---------------------------------------------------------------------------
# Repository interface (adapts shared foundation to COTRN02C expectations)
# ---------------------------------------------------------------------------

class TransactionRepository:
    """
    Abstract interface for transaction and cross-reference data access.

    In the original COBOL program these are CICS READ / WRITE / STARTBR /
    READPREV / ENDBR operations against VSAM KSDS files. Concrete
    implementations can use a database, in-memory dict, or any other store.

    This interface adapts the shared foundation repository interfaces
    (CardXrefRepository + TransactionRepository) into the combined
    interface expected by COTRN02C's business logic.
    """

    def lookup_card_by_account(self, acct_id: str) -> Optional[CardXrefRecord]:
        """
        Look up a card cross-reference record by account ID.

        Corresponds to READ on CXACAIX (alternate index keyed by account).
        Returns None if the account is not found.
        """
        raise NotImplementedError

    def lookup_account_by_card(self, card_num: str) -> Optional[CardXrefRecord]:
        """
        Look up a card cross-reference record by card number.

        Corresponds to READ on CCXREF (primary key is card number).
        Returns None if the card is not found.
        """
        raise NotImplementedError

    def get_max_transaction_id(self) -> int:
        """
        Return the highest existing transaction ID as an integer.

        Corresponds to STARTBR with HIGH-VALUES followed by READPREV.
        Returns 0 if the file is empty (ENDFILE condition).
        """
        raise NotImplementedError

    def write_transaction(self, record: TransactionRecord) -> bool:
        """
        Write a new transaction record.

        Corresponds to CICS WRITE to the TRANSACT file.
        Returns True on success, False if a duplicate key exists.
        """
        raise NotImplementedError

    def get_last_transaction(self) -> Optional[TransactionRecord]:
        """
        Read the last (highest-ID) transaction record.

        Used by the PF5 copy-last-transaction feature.
        Returns None if the file is empty.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# In-memory repository for testing
# ---------------------------------------------------------------------------

class InMemoryTransactionRepository(TransactionRepository):
    """Simple in-memory implementation backed by Python dicts."""

    def __init__(self) -> None:
        self.xref_by_account: dict[str, CardXrefRecord] = {}
        self.xref_by_card: dict[str, CardXrefRecord] = {}
        self.transactions: dict[str, TransactionRecord] = {}

    # -- seed helpers -------------------------------------------------------

    def add_xref(self, record: CardXrefRecord) -> None:
        """Register a cross-reference record for both lookups."""
        self.xref_by_account[record.acct_id] = record
        self.xref_by_card[record.card_num] = record

    def add_transaction(self, record: TransactionRecord) -> None:
        """Insert a transaction record directly (for test setup)."""
        self.transactions[record.tran_id] = record

    # -- interface ----------------------------------------------------------

    def lookup_card_by_account(self, acct_id: str) -> Optional[CardXrefRecord]:
        return self.xref_by_account.get(acct_id)

    def lookup_account_by_card(self, card_num: str) -> Optional[CardXrefRecord]:
        return self.xref_by_card.get(card_num)

    def get_max_transaction_id(self) -> int:
        if not self.transactions:
            return 0
        # Transaction IDs are numeric strings; find the max integer value
        return max(int(tid) for tid in self.transactions)

    def write_transaction(self, record: TransactionRecord) -> bool:
        if record.tran_id in self.transactions:
            return False  # duplicate key
        self.transactions[record.tran_id] = record
        return True

    def get_last_transaction(self) -> Optional[TransactionRecord]:
        if not self.transactions:
            return None
        max_id = max(self.transactions.keys(), key=lambda k: int(k))
        return self.transactions[max_id]


# ---------------------------------------------------------------------------
# Adapter: bridge shared foundation repos into COTRN02C's interface
# ---------------------------------------------------------------------------

class FoundationTransactionRepository(TransactionRepository):
    """Adapter that bridges the shared foundation repositories into
    the combined interface expected by COTRN02C.

    Wraps a CardXrefRepository and a (shared) TransactionRepository
    to present the unified COTRN02C TransactionRepository API.
    """

    def __init__(
        self,
        xref_repo: CardXrefRepository,
        txn_repo: SharedTransactionRepository,
    ) -> None:
        self._xref_repo = xref_repo
        self._txn_repo = txn_repo

    def lookup_card_by_account(self, acct_id: str) -> Optional[CardXrefRecord]:
        shared = self._xref_repo.lookup_by_acct_id(acct_id)
        if shared is None:
            return None
        return CardXrefRecord.from_shared(shared)

    def lookup_account_by_card(self, card_num: str) -> Optional[CardXrefRecord]:
        shared = self._xref_repo.lookup_by_card_num(card_num)
        if shared is None:
            return None
        return CardXrefRecord.from_shared(shared)

    def get_max_transaction_id(self) -> int:
        return self._txn_repo.get_max_id()

    def write_transaction(self, record: TransactionRecord) -> bool:
        return self._txn_repo.write(record)

    def get_last_transaction(self) -> Optional[TransactionRecord]:
        return self._txn_repo.get_last_transaction()


# ---------------------------------------------------------------------------
# Validation functions
# ---------------------------------------------------------------------------

def validate_key_fields(
    txn_input: TransactionInput,
    repo: TransactionRepository,
) -> ValidationResult:
    """
    Validate key fields: account ID and/or card number.

    Business rules (from VALIDATE-INPUT-KEY-FIELDS):
    - At least one of account ID or card number must be provided.
    - If account ID is provided, it must be numeric and must exist in the
      cross-reference file. The associated card number is resolved.
    - If card number is provided, it must be numeric and must exist in the
      cross-reference file. The associated account ID is resolved.
    """
    has_acct = txn_input.acct_id.strip() != ""
    has_card = txn_input.card_num.strip() != ""

    if has_acct:
        # Account ID takes priority when both are supplied
        if not txn_input.acct_id.strip().isdigit():
            return ValidationResult(
                is_valid=False,
                error_message="Account ID must be Numeric...",
                error_field="acct_id",
            )
        # Normalise to right-justified numeric string (11 digits)
        normalised_acct = txn_input.acct_id.strip().zfill(11)
        txn_input.acct_id = normalised_acct

        xref = repo.lookup_card_by_account(normalised_acct)
        if xref is None:
            return ValidationResult(
                is_valid=False,
                error_message="Account ID NOT found...",
                error_field="acct_id",
            )
        # Resolve associated card number
        txn_input.card_num = xref.card_num
        return ValidationResult(is_valid=True)

    if has_card:
        if not txn_input.card_num.strip().isdigit():
            return ValidationResult(
                is_valid=False,
                error_message="Card Number must be Numeric...",
                error_field="card_num",
            )
        normalised_card = txn_input.card_num.strip().zfill(16)
        txn_input.card_num = normalised_card

        xref = repo.lookup_account_by_card(normalised_card)
        if xref is None:
            return ValidationResult(
                is_valid=False,
                error_message="Card Number NOT found...",
                error_field="card_num",
            )
        # Resolve associated account ID
        txn_input.acct_id = xref.acct_id
        return ValidationResult(is_valid=True)

    # Neither provided
    return ValidationResult(
        is_valid=False,
        error_message="Account or Card Number must be entered...",
        error_field="acct_id",
    )


def validate_data_fields(txn_input: TransactionInput) -> ValidationResult:
    """
    Validate all non-key data fields.

    Business rules (from VALIDATE-INPUT-DATA-FIELDS):
    1. All fields must be non-empty.
    2. Type Code and Category Code must be numeric.
    3. Amount must match the format +/-99999999.99.
    4. Origination and Processing dates must match YYYY-MM-DD and be valid
       calendar dates.
    5. Merchant ID must be numeric.
    """

    # --- Required-field checks (order matches COBOL EVALUATE) ---------------
    required_fields = [
        ("tran_type_cd", "Type CD can NOT be empty..."),
        ("tran_cat_cd", "Category CD can NOT be empty..."),
        ("tran_source", "Source can NOT be empty..."),
        ("tran_desc", "Description can NOT be empty..."),
        ("tran_amt", "Amount can NOT be empty..."),
        ("orig_date", "Orig Date can NOT be empty..."),
        ("proc_date", "Proc Date can NOT be empty..."),
        ("merchant_id", "Merchant ID can NOT be empty..."),
        ("merchant_name", "Merchant Name can NOT be empty..."),
        ("merchant_city", "Merchant City can NOT be empty..."),
        ("merchant_zip", "Merchant Zip can NOT be empty..."),
    ]

    for field_name, error_msg in required_fields:
        value = getattr(txn_input, field_name)
        if value.strip() == "":
            return ValidationResult(
                is_valid=False,
                error_message=error_msg,
                error_field=field_name,
            )

    # --- Numeric checks -----------------------------------------------------
    if not txn_input.tran_type_cd.strip().isdigit():
        return ValidationResult(
            is_valid=False,
            error_message="Type CD must be Numeric...",
            error_field="tran_type_cd",
        )

    if not txn_input.tran_cat_cd.strip().isdigit():
        return ValidationResult(
            is_valid=False,
            error_message="Category CD must be Numeric...",
            error_field="tran_cat_cd",
        )

    # --- Amount format check ------------------------------------------------
    # Expected: [+/-]99999999.99  (sign + 8 digits + dot + 2 digits)
    amt = txn_input.tran_amt.strip()
    if not AMOUNT_PATTERN.match(amt):
        return ValidationResult(
            is_valid=False,
            error_message="Amount should be in format -99999999.99",
            error_field="tran_amt",
        )

    # --- Date format and calendar checks ------------------------------------
    orig = txn_input.orig_date.strip()
    if not DATE_PATTERN.match(orig):
        return ValidationResult(
            is_valid=False,
            error_message="Orig Date should be in format YYYY-MM-DD",
            error_field="orig_date",
        )
    if not _is_valid_calendar_date(orig):
        return ValidationResult(
            is_valid=False,
            error_message="Orig Date - Not a valid date...",
            error_field="orig_date",
        )

    proc = txn_input.proc_date.strip()
    if not DATE_PATTERN.match(proc):
        return ValidationResult(
            is_valid=False,
            error_message="Proc Date should be in format YYYY-MM-DD",
            error_field="proc_date",
        )
    if not _is_valid_calendar_date(proc):
        return ValidationResult(
            is_valid=False,
            error_message="Proc Date - Not a valid date...",
            error_field="proc_date",
        )

    # --- Merchant ID numeric check ------------------------------------------
    if not txn_input.merchant_id.strip().isdigit():
        return ValidationResult(
            is_valid=False,
            error_message="Merchant ID must be Numeric...",
            error_field="merchant_id",
        )

    return ValidationResult(is_valid=True)


def validate_confirmation(confirm_value: str) -> ValidationResult:
    """
    Check the confirmation flag.

    Business rules (from PROCESS-ENTER-KEY):
    - 'Y' or 'y' means confirmed (proceed to add).
    - 'N', 'n', blank, or empty means not yet confirmed.
    - Anything else is invalid.
    """
    c = confirm_value.strip().upper()
    if c == "Y":
        return ValidationResult(is_valid=True)
    if c in ("N", ""):
        return ValidationResult(
            is_valid=False,
            error_message="Confirm to add this transaction...",
            error_field="confirm",
        )
    return ValidationResult(
        is_valid=False,
        error_message="Invalid value. Valid values are (Y/N)...",
        error_field="confirm",
    )


# ---------------------------------------------------------------------------
# Core transaction-add logic
# ---------------------------------------------------------------------------

def generate_transaction_id(repo: TransactionRepository) -> str:
    """
    Generate the next transaction ID.

    Business rule (from ADD-TRANSACTION):
    Browse to end of TRANSACT file, read last record, add 1 to its ID.
    If the file is empty, start from 1.
    """
    max_id = repo.get_max_transaction_id()
    next_id = max_id + 1
    # COBOL TRAN-ID is PIC X(16) — left-pad with zeros
    return str(next_id).zfill(16)


def build_transaction_record(
    tran_id: str,
    txn_input: TransactionInput,
) -> TransactionRecord:
    """
    Build a TransactionRecord from validated user input.

    Corresponds to the field-move block inside ADD-TRANSACTION.
    """
    # Parse amount using NUMVAL-C equivalent (handles sign and commas)
    amt = _parse_amount(txn_input.tran_amt.strip())

    return TransactionRecord(
        tran_id=tran_id,
        tran_type_cd=txn_input.tran_type_cd.strip(),
        tran_cat_cd=txn_input.tran_cat_cd.strip(),
        tran_source=txn_input.tran_source.strip(),
        tran_desc=txn_input.tran_desc.strip(),
        tran_amt=amt,
        tran_merchant_id=txn_input.merchant_id.strip(),
        tran_merchant_name=txn_input.merchant_name.strip(),
        tran_merchant_city=txn_input.merchant_city.strip(),
        tran_merchant_zip=txn_input.merchant_zip.strip(),
        tran_card_num=txn_input.card_num.strip(),
        tran_orig_ts=txn_input.orig_date.strip(),
        tran_proc_ts=txn_input.proc_date.strip(),
    )


def add_transaction(
    txn_input: TransactionInput,
    repo: TransactionRepository,
) -> AddTransactionResult:
    """
    Full add-transaction workflow: validate, generate ID, write record.

    This is the top-level entry point that mirrors the COBOL program's
    PROCESS-ENTER-KEY paragraph when the user presses Enter with
    confirmation = 'Y'.

    Returns an AddTransactionResult indicating success or the first
    validation error encountered.
    """
    # Step 1: Validate key fields (account / card number lookup)
    key_result = validate_key_fields(txn_input, repo)
    if not key_result.is_valid:
        return AddTransactionResult(
            success=False,
            message=key_result.error_message,
        )

    # Step 2: Validate data fields
    data_result = validate_data_fields(txn_input)
    if not data_result.is_valid:
        return AddTransactionResult(
            success=False,
            message=data_result.error_message,
        )

    # Step 3: Check confirmation
    confirm_result = validate_confirmation(txn_input.confirm)
    if not confirm_result.is_valid:
        return AddTransactionResult(
            success=False,
            message=confirm_result.error_message,
        )

    # Step 4: Generate new transaction ID
    tran_id = generate_transaction_id(repo)

    # Step 5: Build the record
    record = build_transaction_record(tran_id, txn_input)

    # Step 6: Write to the repository
    written = repo.write_transaction(record)
    if not written:
        return AddTransactionResult(
            success=False,
            message="Tran ID already exist...",
        )

    # Success — mirrors the STRING statement in WRITE-TRANSACT-FILE
    tran_id_display = tran_id.lstrip("0") or "0"
    return AddTransactionResult(
        success=True,
        message=(
            f"Transaction added successfully. "
            f"Your Tran ID is {tran_id_display}."
        ),
        tran_id=tran_id,
    )


# ---------------------------------------------------------------------------
# Copy-last-transaction helper (PF5 feature)
# ---------------------------------------------------------------------------

def copy_last_transaction_data(
    txn_input: TransactionInput,
    repo: TransactionRepository,
) -> Optional[TransactionInput]:
    """
    Copy data fields from the last transaction into the input.

    Business rule (from COPY-LAST-TRAN-DATA):
    1. The key fields (account/card) must be valid first.
    2. Read the last transaction record.
    3. Populate the data fields (but NOT the key fields).

    Returns the updated TransactionInput, or None if key validation fails
    or the transaction file is empty.
    """
    key_result = validate_key_fields(txn_input, repo)
    if not key_result.is_valid:
        return None

    last_tran = repo.get_last_transaction()
    if last_tran is None:
        return None

    # Copy data fields from the last transaction into the screen input
    txn_input.tran_type_cd = last_tran.tran_type_cd
    txn_input.tran_cat_cd = last_tran.tran_cat_cd
    txn_input.tran_source = last_tran.tran_source
    txn_input.tran_desc = last_tran.tran_desc
    txn_input.tran_amt = _format_amount(last_tran.tran_amt)
    txn_input.orig_date = last_tran.tran_orig_ts[:10] if last_tran.tran_orig_ts else ""
    txn_input.proc_date = last_tran.tran_proc_ts[:10] if last_tran.tran_proc_ts else ""
    txn_input.merchant_id = last_tran.tran_merchant_id
    txn_input.merchant_name = last_tran.tran_merchant_name
    txn_input.merchant_city = last_tran.tran_merchant_city
    txn_input.merchant_zip = last_tran.tran_merchant_zip

    return txn_input


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


def clear_all_fields() -> TransactionInput:
    """
    Return a blank TransactionInput.

    Corresponds to INITIALIZE-ALL-FIELDS / CLEAR-CURRENT-SCREEN (PF4).
    """
    return TransactionInput()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_valid_calendar_date(date_str: str) -> bool:
    """
    Check that a YYYY-MM-DD string represents a real calendar date.

    Delegates to the shared foundation's is_valid_calendar_date after
    converting from YYYY-MM-DD format to CCYYMMDD format.
    """
    # Convert YYYY-MM-DD to CCYYMMDD for the shared validator
    parts = date_str.split("-")
    if len(parts) != 3:
        return False
    ccyymmdd = parts[0] + parts[1] + parts[2]
    return is_valid_calendar_date(ccyymmdd)


def _parse_amount(amount_str: str) -> float:
    """
    Parse a signed amount string into a float.

    Mirrors FUNCTION NUMVAL-C which handles sign characters and commas.
    Input examples: "+00000100.50", "-00000025.00"
    """
    # Remove commas (NUMVAL-C handles them) and convert
    cleaned = amount_str.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _format_amount(amount: float) -> str:
    """
    Format a numeric amount back to the screen format +99999999.99.

    Used when copying the last transaction's amount to the input fields.
    """
    sign = "+" if amount >= 0 else "-"
    # Format absolute value with 8 integer digits and 2 decimal places
    return f"{sign}{abs(amount):011.2f}"
