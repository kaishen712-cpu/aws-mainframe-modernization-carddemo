"""
COTRN00C - Transaction List Program (Python Translation)

Translated from the COBOL program COTRN00C.CBL in the AWS CardDemo
mainframe modernization project. This module implements the business
logic for listing transactions with paginated browsing.

Original: CICS COBOL program using BMS maps and VSAM files.
This translation separates the pure business logic (pagination, filtering,
selection) from the CICS presentation layer so the rules can be tested
and reused independently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


# ---------------------------------------------------------------------------
# Constants (from copybooks COTTL01Y, CSMSG01Y)
# ---------------------------------------------------------------------------

PROGRAM_NAME = "COTRN00C"
TRANSACTION_ID = "CT00"

TITLE_01 = "      AWS Mainframe Modernization       "
TITLE_02 = "              CardDemo                  "

MSG_INVALID_KEY = "Invalid key pressed. Please see below..."
MSG_THANK_YOU = "Thank you for using CardDemo application..."

PAGE_SIZE = 10  # Number of transaction rows per page


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
class TransactionDisplayRow:
    """One row of the transaction list display (10 per page)."""
    tran_id: str = ""
    tran_date: str = ""       # formatted MM/DD/YY
    tran_desc: str = ""
    tran_amt: str = ""        # formatted +99999999.99


@dataclass
class TransactionListPage:
    """A page of transaction list results."""
    rows: List[TransactionDisplayRow] = field(default_factory=list)
    page_num: int = 0
    has_next_page: bool = False
    first_tran_id: str = ""
    last_tran_id: str = ""
    message: str = ""


@dataclass
class SelectionResult:
    """Outcome of selecting a transaction from the list."""
    selected: bool = False
    tran_id: str = ""
    transfer_program: str = ""
    error_message: str = ""


# ---------------------------------------------------------------------------
# Repository interface (abstracts VSAM file I/O)
# ---------------------------------------------------------------------------

class TransactionRepository:
    """
    Abstract interface for transaction data access.

    In the original COBOL program these are CICS STARTBR / READNEXT /
    READPREV / ENDBR operations against VSAM KSDS files. Concrete
    implementations can use a database, in-memory dict, or any other store.
    """

    def get_transactions_forward(
        self,
        start_id: str = "",
        limit: int = PAGE_SIZE,
    ) -> List[TransactionRecord]:
        """
        Read transactions forward starting at or after start_id.

        Corresponds to STARTBR + READNEXT loop.
        Returns up to `limit` records in ascending key order.
        If start_id is empty, starts from the beginning.
        """
        raise NotImplementedError

    def get_transactions_backward(
        self,
        start_id: str = "",
        limit: int = PAGE_SIZE,
    ) -> List[TransactionRecord]:
        """
        Read transactions backward starting at or before start_id.

        Corresponds to STARTBR + READPREV loop.
        Returns up to `limit` records in ascending key order
        (reversed from the read order to match display order).
        If start_id is empty, starts from the end.
        """
        raise NotImplementedError

    def get_transaction_by_id(self, tran_id: str) -> Optional[TransactionRecord]:
        """
        Read a single transaction by its ID.

        Corresponds to CICS READ on TRANSACT file.
        Returns None if not found.
        """
        raise NotImplementedError

    def has_more_after(self, tran_id: str) -> bool:
        """
        Check if there are more transactions after the given ID.

        Used to determine the next-page flag.
        """
        raise NotImplementedError

    def has_more_before(self, tran_id: str) -> bool:
        """
        Check if there are more transactions before the given ID.

        Used to determine if backward paging is possible.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# In-memory repository for testing
# ---------------------------------------------------------------------------

class InMemoryTransactionRepository(TransactionRepository):
    """Simple in-memory implementation backed by a sorted dict."""

    def __init__(self) -> None:
        self.transactions: dict[str, TransactionRecord] = {}

    def add_transaction(self, record: TransactionRecord) -> None:
        """Insert a transaction record directly (for test setup)."""
        self.transactions[record.tran_id] = record

    def _sorted_ids(self) -> List[str]:
        """Return all transaction IDs in sorted order."""
        return sorted(self.transactions.keys())

    def get_transactions_forward(
        self,
        start_id: str = "",
        limit: int = PAGE_SIZE,
    ) -> List[TransactionRecord]:
        sorted_ids = self._sorted_ids()
        if not sorted_ids:
            return []

        # Find starting position
        start_idx = 0
        if start_id:
            for i, tid in enumerate(sorted_ids):
                if tid >= start_id:
                    start_idx = i
                    break
            else:
                return []  # start_id is beyond all records

        result = []
        for tid in sorted_ids[start_idx:start_idx + limit]:
            result.append(self.transactions[tid])
        return result

    def get_transactions_backward(
        self,
        start_id: str = "",
        limit: int = PAGE_SIZE,
    ) -> List[TransactionRecord]:
        sorted_ids = self._sorted_ids()
        if not sorted_ids:
            return []

        # Find starting position (at or before start_id)
        if start_id:
            start_idx = len(sorted_ids) - 1
            for i in range(len(sorted_ids) - 1, -1, -1):
                if sorted_ids[i] <= start_id:
                    start_idx = i
                    break
            else:
                return []  # start_id is before all records
        else:
            start_idx = len(sorted_ids) - 1

        # Read backward
        end_idx = max(start_idx - limit + 1, 0)
        result = []
        for tid in sorted_ids[end_idx:start_idx + 1]:
            result.append(self.transactions[tid])
        return result

    def get_transaction_by_id(self, tran_id: str) -> Optional[TransactionRecord]:
        return self.transactions.get(tran_id)

    def has_more_after(self, tran_id: str) -> bool:
        sorted_ids = self._sorted_ids()
        if not sorted_ids:
            return False
        return tran_id < sorted_ids[-1]

    def has_more_before(self, tran_id: str) -> bool:
        sorted_ids = self._sorted_ids()
        if not sorted_ids:
            return False
        return tran_id > sorted_ids[0]


# ---------------------------------------------------------------------------
# Validation functions
# ---------------------------------------------------------------------------

def validate_tran_id_filter(tran_id_input: str) -> tuple[bool, str, str]:
    """
    Validate the transaction ID filter input.

    Business rules (from PROCESS-ENTER-KEY):
    - If blank/empty, no filter is applied (valid, returns empty string).
    - If provided, must be numeric.

    Returns:
        (is_valid, normalised_tran_id, error_message)
    """
    stripped = tran_id_input.strip()
    if not stripped:
        return (True, "", "")

    if not stripped.isdigit():
        return (False, "", "Tran ID must be Numeric ...")

    # Normalise to 16-character zero-padded ID
    normalised = stripped.zfill(16)
    return (True, normalised, "")


def validate_selection(selection_flag: str) -> tuple[bool, str]:
    """
    Validate a row selection flag.

    Business rules:
    - 'S' or 's' is valid (view transaction).
    - Anything else non-blank is invalid.

    Returns:
        (is_valid, error_message)
    """
    s = selection_flag.strip()
    if not s:
        return (True, "")

    if s.upper() == "S":
        return (True, "")

    return (False, "Invalid selection. Valid value is S")


# ---------------------------------------------------------------------------
# Core list/pagination logic
# ---------------------------------------------------------------------------

def format_tran_date(orig_ts: str) -> str:
    """
    Format a transaction origination timestamp to MM/DD/YY.

    Corresponds to the POPULATE-TRAN-DATA paragraph which extracts
    YYYY-MM-DD from the timestamp and reformats to MM/DD/YY.
    """
    if not orig_ts or len(orig_ts) < 10:
        return "00/00/00"

    # Expected format: YYYY-MM-DD...
    date_part = orig_ts[:10]
    try:
        parts = date_part.split("-")
        if len(parts) == 3:
            yyyy, mm, dd = parts
            yy = yyyy[2:4] if len(yyyy) >= 4 else yyyy
            return f"{mm}/{dd}/{yy}"
    except (ValueError, IndexError):
        pass

    return "00/00/00"


def format_tran_amount(amount: float) -> str:
    """
    Format a transaction amount for display.

    Corresponds to MOVE TRAN-AMT TO WS-TRAN-AMT where
    WS-TRAN-AMT is PIC +99999999.99.
    """
    sign = "+" if amount >= 0 else "-"
    return f"{sign}{abs(amount):011.2f}"


def build_display_row(record: TransactionRecord) -> TransactionDisplayRow:
    """Build a display row from a transaction record."""
    return TransactionDisplayRow(
        tran_id=record.tran_id,
        tran_date=format_tran_date(record.tran_orig_ts),
        tran_desc=record.tran_desc,
        tran_amt=format_tran_amount(record.tran_amt),
    )


def list_transactions_forward(
    repo: TransactionRepository,
    start_id: str = "",
    current_page: int = 0,
) -> TransactionListPage:
    """
    Load a page of transactions moving forward.

    Corresponds to PROCESS-PAGE-FORWARD paragraph.

    Args:
        repo: Transaction data repository.
        start_id: Transaction ID to start from (empty = beginning).
        current_page: Current page number before this operation.

    Returns:
        A TransactionListPage with up to PAGE_SIZE rows.
    """
    # Fetch one extra to check for next page
    records = repo.get_transactions_forward(start_id, PAGE_SIZE + 1)

    if not records:
        return TransactionListPage(
            page_num=current_page,
            message="You have reached the bottom of the page...",
        )

    has_next = len(records) > PAGE_SIZE
    page_records = records[:PAGE_SIZE]

    rows = [build_display_row(r) for r in page_records]

    first_id = page_records[0].tran_id if page_records else ""
    last_id = page_records[-1].tran_id if page_records else ""

    return TransactionListPage(
        rows=rows,
        page_num=current_page + 1,
        has_next_page=has_next,
        first_tran_id=first_id,
        last_tran_id=last_id,
    )


def list_transactions_backward(
    repo: TransactionRepository,
    start_id: str = "",
    current_page: int = 0,
) -> TransactionListPage:
    """
    Load a page of transactions moving backward.

    Corresponds to PROCESS-PAGE-BACKWARD paragraph.

    Args:
        repo: Transaction data repository.
        start_id: Transaction ID to start from (going backward).
        current_page: Current page number before this operation.

    Returns:
        A TransactionListPage with up to PAGE_SIZE rows.
    """
    records = repo.get_transactions_backward(start_id, PAGE_SIZE)

    if not records:
        return TransactionListPage(
            page_num=current_page,
            message="You are already at the top of the page...",
        )

    rows = [build_display_row(r) for r in records]

    first_id = records[0].tran_id if records else ""
    last_id = records[-1].tran_id if records else ""

    new_page = max(current_page - 1, 1) if current_page > 1 else 1

    return TransactionListPage(
        rows=rows,
        page_num=new_page,
        has_next_page=True,  # Can always go forward after going back
        first_tran_id=first_id,
        last_tran_id=last_id,
    )


def process_enter_key(
    repo: TransactionRepository,
    tran_id_filter: str = "",
    selections: Optional[List[tuple[str, str]]] = None,
) -> tuple[Optional[SelectionResult], Optional[TransactionListPage]]:
    """
    Process the Enter key action.

    Corresponds to PROCESS-ENTER-KEY paragraph.

    Args:
        repo: Transaction data repository.
        tran_id_filter: Optional transaction ID filter from the input field.
        selections: List of (selection_flag, tran_id) tuples from each row.

    Returns:
        A tuple of (SelectionResult or None, TransactionListPage or None).
        If a valid selection was made, returns (SelectionResult, None).
        Otherwise returns (None, TransactionListPage).
    """
    # Check for row selection
    if selections:
        for sel_flag, sel_tran_id in selections:
            if sel_flag.strip() and sel_tran_id.strip():
                is_valid, error = validate_selection(sel_flag)
                if not is_valid:
                    return (
                        SelectionResult(error_message=error),
                        None,
                    )
                return (
                    SelectionResult(
                        selected=True,
                        tran_id=sel_tran_id.strip(),
                        transfer_program="COTRN01C",
                    ),
                    None,
                )

    # Validate transaction ID filter
    is_valid, normalised_id, error = validate_tran_id_filter(tran_id_filter)
    if not is_valid:
        return (
            None,
            TransactionListPage(message=error),
        )

    # Load first page from the given starting ID
    page = list_transactions_forward(repo, normalised_id, current_page=0)
    return (None, page)


def process_pf7(
    repo: TransactionRepository,
    first_tran_id: str,
    current_page: int,
) -> TransactionListPage:
    """
    Process PF7 (page backward).

    Corresponds to PROCESS-PF7-KEY paragraph.
    """
    if current_page <= 1:
        return TransactionListPage(
            page_num=current_page,
            message="You are already at the top of the page...",
        )

    # Go backward from the first ID on the current page
    # We need the page BEFORE the current one, so we need records
    # strictly before first_tran_id
    if not first_tran_id.strip():
        start_id = ""
    else:
        # Decrement the ID by 1 to get records before this one
        try:
            id_val = int(first_tran_id)
            if id_val > 0:
                start_id = str(id_val - 1).zfill(16)
            else:
                start_id = ""
        except ValueError:
            start_id = first_tran_id

    return list_transactions_backward(repo, start_id, current_page)


def process_pf8(
    repo: TransactionRepository,
    last_tran_id: str,
    current_page: int,
    has_next_page: bool,
) -> TransactionListPage:
    """
    Process PF8 (page forward).

    Corresponds to PROCESS-PF8-KEY paragraph.
    """
    if not has_next_page:
        return TransactionListPage(
            page_num=current_page,
            message="You are already at the bottom of the page...",
        )

    # Start from the record after the last one on the current page
    if not last_tran_id.strip():
        start_id = ""
    else:
        try:
            id_val = int(last_tran_id)
            start_id = str(id_val + 1).zfill(16)
        except ValueError:
            start_id = last_tran_id

    return list_transactions_forward(repo, start_id, current_page)


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
