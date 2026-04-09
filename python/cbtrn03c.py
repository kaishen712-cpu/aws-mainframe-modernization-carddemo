"""
CBTRN03C - Transaction Detail Report (Python Translation)

Translated from the COBOL program CBTRN03C.CBL in the AWS CardDemo
mainframe modernization project. This module generates a formatted
transaction detail report grouped by account, with page totals,
account totals, and a grand total.

Original: Batch COBOL program that reads a sequential transaction file,
looks up cross-reference, transaction type, and transaction category
data from indexed files, and writes a formatted report with headers,
detail lines, and multiple levels of totals.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROGRAM_NAME = "CBTRN03C"
DEFAULT_PAGE_SIZE = 20
REPORT_LINE_WIDTH = 133


# ---------------------------------------------------------------------------
# Data structures (from copybooks)
# ---------------------------------------------------------------------------

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
class CardXrefRecord:
    """Card cross-reference record (CVACT03Y - 50 bytes)."""
    xref_card_num: str = ""   # PIC X(16)
    xref_cust_id: str = ""    # PIC 9(09)
    xref_acct_id: str = ""    # PIC 9(11)


@dataclass
class TranTypeRecord:
    """Transaction type record (CVTRA03Y - 60 bytes)."""
    tran_type: str = ""       # PIC X(02)
    tran_type_desc: str = ""  # PIC X(50)


@dataclass
class TranCatRecord:
    """Transaction category record (CVTRA04Y - 60 bytes)."""
    tran_type_cd: str = ""        # PIC X(02)
    tran_cat_cd: str = ""         # PIC 9(04)
    tran_cat_type_desc: str = ""  # PIC X(50)


# ---------------------------------------------------------------------------
# Repository interfaces
# ---------------------------------------------------------------------------

class TransactionFileRepository:
    """Abstract interface for sequential transaction data access."""

    def get_all_transactions(self) -> List[TransactionRecord]:
        """Return all transactions in sequential order."""
        raise NotImplementedError


class XrefLookupRepository:
    """Abstract interface for card cross-reference lookup."""

    def lookup_by_card_num(self, card_num: str) -> Optional[CardXrefRecord]:
        """Look up a cross-reference record by card number."""
        raise NotImplementedError


class TranTypeLookupRepository:
    """Abstract interface for transaction type lookup."""

    def lookup_by_type(self, tran_type: str) -> Optional[TranTypeRecord]:
        """Look up a transaction type record by type code."""
        raise NotImplementedError


class TranCatLookupRepository:
    """Abstract interface for transaction category lookup."""

    def lookup_by_key(self, tran_type_cd: str, tran_cat_cd: str) -> Optional[TranCatRecord]:
        """Look up a transaction category record by composite key."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# In-memory repositories for testing
# ---------------------------------------------------------------------------

class InMemoryTransactionFileRepository(TransactionFileRepository):
    """Simple in-memory implementation backed by a list."""

    def __init__(self) -> None:
        self.transactions: List[TransactionRecord] = []

    def add_transaction(self, record: TransactionRecord) -> None:
        self.transactions.append(record)

    def get_all_transactions(self) -> List[TransactionRecord]:
        return list(self.transactions)


class InMemoryXrefLookupRepository(XrefLookupRepository):
    """In-memory cross-reference lookup."""

    def __init__(self) -> None:
        self.xrefs: Dict[str, CardXrefRecord] = {}

    def add_xref(self, record: CardXrefRecord) -> None:
        self.xrefs[record.xref_card_num] = record

    def lookup_by_card_num(self, card_num: str) -> Optional[CardXrefRecord]:
        return self.xrefs.get(card_num)


class InMemoryTranTypeLookupRepository(TranTypeLookupRepository):
    """In-memory transaction type lookup."""

    def __init__(self) -> None:
        self.types: Dict[str, TranTypeRecord] = {}

    def add_type(self, record: TranTypeRecord) -> None:
        self.types[record.tran_type] = record

    def lookup_by_type(self, tran_type: str) -> Optional[TranTypeRecord]:
        return self.types.get(tran_type)


class InMemoryTranCatLookupRepository(TranCatLookupRepository):
    """In-memory transaction category lookup."""

    def __init__(self) -> None:
        self.categories: Dict[str, TranCatRecord] = {}

    def add_category(self, record: TranCatRecord) -> None:
        key = record.tran_type_cd + record.tran_cat_cd
        self.categories[key] = record

    def lookup_by_key(self, tran_type_cd: str, tran_cat_cd: str) -> Optional[TranCatRecord]:
        key = tran_type_cd + tran_cat_cd
        return self.categories.get(key)


# ---------------------------------------------------------------------------
# Report formatting helpers (from copybook CVTRA07Y)
# ---------------------------------------------------------------------------

def _format_amount(amount: float) -> str:
    """
    Format an amount using the COBOL PIC -ZZZ,ZZZ,ZZZ.ZZ pattern.

    Returns a right-justified 15-character string with sign, commas,
    and two decimal places.
    """
    sign = "-" if amount < 0 else "+"
    abs_amt = abs(amount)
    integer_part = int(abs_amt)
    decimal_part = round((abs_amt - integer_part) * 100)
    if decimal_part >= 100:
        integer_part += 1
        decimal_part -= 100
    formatted_int = f"{integer_part:,}"
    result = f"{sign}{formatted_int}.{decimal_part:02d}"
    return result.rjust(15)


def _build_report_name_header(start_date: str, end_date: str) -> str:
    """
    Build the report name header line (REPORT-NAME-HEADER from CVTRA07Y).

    Layout: short name (38) + long name (41) + date header (12) +
            start date (10) + ' to ' (4) + end date (10) = ~115 chars
    """
    short_name = "DALYREPT".ljust(38)
    long_name = "Daily Transaction Report".ljust(41)
    date_header = "Date Range: "
    return f"{short_name}{long_name}{date_header}{start_date} to {end_date}"


def _build_transaction_header_1() -> str:
    """
    Build the column header line (TRANSACTION-HEADER-1 from CVTRA07Y).
    """
    return (
        "Transaction ID".ljust(17)
        + "Account ID".ljust(12)
        + "Transaction Type".ljust(19)
        + "Tran Category".ljust(35)
        + "Tran Source".ljust(14)
        + " "
        + "        Amount".ljust(16)
    )


def _build_transaction_header_2() -> str:
    """Build the separator line (TRANSACTION-HEADER-2 from CVTRA07Y)."""
    return "-" * REPORT_LINE_WIDTH


def _build_detail_line(
    tran_id: str,
    acct_id: str,
    type_cd: str,
    type_desc: str,
    cat_cd: str,
    cat_desc: str,
    source: str,
    amount: float,
) -> str:
    """
    Build a transaction detail line (TRANSACTION-DETAIL-REPORT from CVTRA07Y).

    Layout: trans_id(16) + sp + acct_id(11) + sp + type_cd(2) + '-' +
            type_desc(15) + sp + cat_cd(4) + '-' + cat_desc(29) + sp +
            source(10) + sp(4) + amount(15) + sp(2)
    """
    return (
        f"{tran_id:<16} "
        f"{acct_id:<11} "
        f"{type_cd:<2}-{type_desc:<15} "
        f"{cat_cd:>4}-{cat_desc:<29} "
        f"{source:<10}    "
        f"{_format_amount(amount)}  "
    )


def _build_page_totals_line(total: float) -> str:
    """Build the page totals line (REPORT-PAGE-TOTALS from CVTRA07Y)."""
    label = "Page Total"
    dots = "." * 86
    return f"{label}{dots}{_format_amount(total)}"


def _build_account_totals_line(total: float) -> str:
    """Build the account totals line (REPORT-ACCOUNT-TOTALS from CVTRA07Y)."""
    label = "Account Total"
    dots = "." * 84
    return f"{label}{dots}{_format_amount(total)}"


def _build_grand_totals_line(total: float) -> str:
    """Build the grand totals line (REPORT-GRAND-TOTALS from CVTRA07Y)."""
    label = "Grand Total"
    dots = "." * 86
    return f"{label}{dots}{_format_amount(total)}"


# ---------------------------------------------------------------------------
# Main report generation
# ---------------------------------------------------------------------------

def generate_transaction_detail_report(
    transaction_repo: TransactionFileRepository,
    xref_repo: XrefLookupRepository,
    type_repo: TranTypeLookupRepository,
    cat_repo: TranCatLookupRepository,
    start_date: str,
    end_date: str,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> List[str]:
    """
    Generate the transaction detail report.

    This is the main entry point corresponding to the COBOL program's
    PROCEDURE DIVISION. It processes all transactions within the given
    date range, groups them by account (card number), and produces
    a formatted report with headers, detail lines, page totals,
    account totals, and a grand total.

    Args:
        transaction_repo: Repository providing transactions sequentially.
        xref_repo: Repository for card-to-account cross-reference lookups.
        type_repo: Repository for transaction type description lookups.
        cat_repo: Repository for transaction category description lookups.
        start_date: Report start date (YYYY-MM-DD format).
        end_date: Report end date (YYYY-MM-DD format).
        page_size: Number of detail lines per page before page totals.

    Returns:
        A list of formatted report lines.
    """
    lines: List[str] = []
    transactions = transaction_repo.get_all_transactions()

    first_time = True
    line_counter = 0
    page_total = 0.0
    account_total = 0.0
    grand_total = 0.0
    curr_card_num = ""

    # Filter and process transactions
    filtered_transactions: List[TransactionRecord] = []
    for tran in transactions:
        proc_date = tran.tran_proc_ts[:10] if len(tran.tran_proc_ts) >= 10 else tran.tran_proc_ts
        if start_date <= proc_date <= end_date:
            filtered_transactions.append(tran)

    for i, tran in enumerate(filtered_transactions):
        # Account change detection
        if curr_card_num != tran.tran_card_num:
            if not first_time:
                # Write account totals for previous account
                lines.append(_build_account_totals_line(account_total))
                account_total = 0.0
                line_counter += 1
                lines.append(_build_transaction_header_2())
                line_counter += 1

            curr_card_num = tran.tran_card_num

            # Look up cross-reference for account ID
            xref = xref_repo.lookup_by_card_num(tran.tran_card_num)

        # Write headers on first time
        if first_time:
            first_time = False
            lines.append(_build_report_name_header(start_date, end_date))
            line_counter += 1
            lines.append(" " * REPORT_LINE_WIDTH)
            line_counter += 1
            lines.append(_build_transaction_header_1())
            line_counter += 1
            lines.append(_build_transaction_header_2())
            line_counter += 1

        # Page break logic
        if line_counter > 0 and line_counter % page_size == 0:
            lines.append(_build_page_totals_line(page_total))
            grand_total += page_total
            page_total = 0.0
            line_counter += 1
            lines.append(_build_transaction_header_2())
            line_counter += 1
            # Write headers for new page
            lines.append(_build_report_name_header(start_date, end_date))
            line_counter += 1
            lines.append(" " * REPORT_LINE_WIDTH)
            line_counter += 1
            lines.append(_build_transaction_header_1())
            line_counter += 1
            lines.append(_build_transaction_header_2())
            line_counter += 1

        # Accumulate totals
        page_total += tran.tran_amt
        account_total += tran.tran_amt

        # Look up type description
        type_rec = type_repo.lookup_by_type(tran.tran_type_cd)
        type_desc = type_rec.tran_type_desc if type_rec else ""

        # Look up category description
        cat_rec = cat_repo.lookup_by_key(tran.tran_type_cd, tran.tran_cat_cd)
        cat_desc = cat_rec.tran_cat_type_desc if cat_rec else ""

        # Get account ID from xref
        acct_id = xref.xref_acct_id if xref else ""

        # Write detail line
        lines.append(_build_detail_line(
            tran_id=tran.tran_id,
            acct_id=acct_id,
            type_cd=tran.tran_type_cd,
            type_desc=type_desc,
            cat_cd=tran.tran_cat_cd,
            cat_desc=cat_desc,
            source=tran.tran_source,
            amount=tran.tran_amt,
        ))
        line_counter += 1

    # Final totals (only if we had transactions)
    if not first_time:
        # Write final page totals
        lines.append(_build_page_totals_line(page_total))
        grand_total += page_total

        # Write final account totals
        lines.append(_build_account_totals_line(account_total))

        # Write grand totals
        lines.append(_build_grand_totals_line(grand_total))

    return lines
