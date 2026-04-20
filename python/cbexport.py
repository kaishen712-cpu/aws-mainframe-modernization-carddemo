"""
CBEXPORT - Export Customer Data for Branch Migration (Python Translation)

Translated from the COBOL program CBEXPORT.CBL in the AWS CardDemo
mainframe modernization project. This module exports data from multiple
CardDemo repositories into a list of multi-record export records suitable
for branch migration.

Original: BATCH COBOL program reading 5 VSAM files, writing 1 sequential
export file using the CVEXPORT.cpy multi-record layout.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Data structures — source record types (from copybooks)
# ---------------------------------------------------------------------------

@dataclass
class CustomerRecord:
    """Customer record (CVCUS01Y - 500 bytes)."""
    cust_id: str = ""                   # PIC 9(09)
    first_name: str = ""                # PIC X(25)
    middle_name: str = ""               # PIC X(25)
    last_name: str = ""                 # PIC X(25)
    addr_line_1: str = ""               # PIC X(50)
    addr_line_2: str = ""               # PIC X(50)
    addr_line_3: str = ""               # PIC X(50)
    addr_state_cd: str = ""             # PIC X(02)
    addr_country_cd: str = ""           # PIC X(03)
    addr_zip: str = ""                  # PIC X(10)
    phone_num_1: str = ""               # PIC X(15)
    phone_num_2: str = ""               # PIC X(15)
    ssn: str = ""                       # PIC 9(09)
    govt_issued_id: str = ""            # PIC X(20)
    dob_yyyy_mm_dd: str = ""            # PIC X(10)
    eft_account_id: str = ""            # PIC X(10)
    pri_card_holder_ind: str = ""       # PIC X(01)
    fico_credit_score: int = 0          # PIC 9(03)


@dataclass
class AccountRecord:
    """Account record (CVACT01Y - 300 bytes)."""
    acct_id: str = ""                   # PIC 9(11)
    active_status: str = ""             # PIC X(01)
    curr_bal: float = 0.0               # PIC S9(10)V99
    credit_limit: float = 0.0           # PIC S9(10)V99
    cash_credit_limit: float = 0.0      # PIC S9(10)V99
    open_date: str = ""                 # PIC X(10)
    expiration_date: str = ""           # PIC X(10)
    reissue_date: str = ""              # PIC X(10)
    curr_cyc_credit: float = 0.0        # PIC S9(10)V99
    curr_cyc_debit: float = 0.0         # PIC S9(10)V99
    addr_zip: str = ""                  # PIC X(10)
    group_id: str = ""                  # PIC X(10)


@dataclass
class CardXrefRecord:
    """Card cross-reference record (CVACT03Y - 50 bytes)."""
    card_num: str = ""                  # PIC X(16)
    cust_id: str = ""                   # PIC 9(09)
    acct_id: str = ""                   # PIC 9(11)


@dataclass
class TransactionRecord:
    """Transaction record (CVTRA05Y - 350 bytes)."""
    tran_id: str = ""                   # PIC X(16)
    tran_type_cd: str = ""              # PIC X(02)
    tran_cat_cd: str = ""               # PIC 9(04)
    tran_source: str = ""               # PIC X(10)
    tran_desc: str = ""                 # PIC X(100)
    tran_amt: float = 0.0              # PIC S9(09)V99
    tran_merchant_id: str = ""          # PIC 9(09)
    tran_merchant_name: str = ""        # PIC X(50)
    tran_merchant_city: str = ""        # PIC X(50)
    tran_merchant_zip: str = ""         # PIC X(10)
    tran_card_num: str = ""             # PIC X(16)
    tran_orig_ts: str = ""              # PIC X(26)
    tran_proc_ts: str = ""              # PIC X(26)


@dataclass
class CardRecord:
    """Card record (CVACT02Y - 150 bytes)."""
    card_num: str = ""                  # PIC X(16)
    card_acct_id: str = ""              # PIC 9(11)
    card_cvv_cd: str = ""               # PIC 9(03)
    card_embossed_name: str = ""        # PIC X(50)
    card_expiration_date: str = ""      # PIC X(10)
    card_active_status: str = ""        # PIC X(01)


# ---------------------------------------------------------------------------
# Export record — tagged union (from CVEXPORT.cpy)
# ---------------------------------------------------------------------------

@dataclass
class ExportRecord:
    """
    Multi-record export layout (CVEXPORT - 500 bytes conceptual).

    The COBOL program uses REDEFINES to overlay different record structures
    on the EXPORT-RECORD-DATA field. In Python, we use a tagged union with
    a discriminator field (rec_type) and separate typed data fields.
    """
    rec_type: str = ""                  # PIC X(1) — 'C','A','X','T','D'
    timestamp: str = ""                 # PIC X(26)
    sequence_num: int = 0               # PIC 9(9) COMP
    branch_id: str = "0001"             # PIC X(4)
    region_code: str = "NORTH"          # PIC X(5)

    # Tagged data — only one of these is populated per record
    customer_data: Optional[CustomerRecord] = None
    account_data: Optional[AccountRecord] = None
    xref_data: Optional[CardXrefRecord] = None
    transaction_data: Optional[TransactionRecord] = None
    card_data: Optional[CardRecord] = None


# ---------------------------------------------------------------------------
# Export statistics
# ---------------------------------------------------------------------------

@dataclass
class ExportStatistics:
    """Counters matching WS-EXPORT-STATISTICS."""
    customer_records: int = 0
    account_records: int = 0
    xref_records: int = 0
    transaction_records: int = 0
    card_records: int = 0
    total_records: int = 0


# ---------------------------------------------------------------------------
# Repository interface (abstracts VSAM file I/O)
# ---------------------------------------------------------------------------

class ExportDataRepository:
    """
    Abstract interface for reading data to be exported.

    In the original COBOL program these are sequential READs against
    VSAM KSDS files opened in INPUT mode. Concrete implementations
    can use a database, in-memory lists, or any other store.
    """

    def get_all_customers(self) -> list[CustomerRecord]:
        """Return all customer records in key order."""
        raise NotImplementedError

    def get_all_accounts(self) -> list[AccountRecord]:
        """Return all account records in key order."""
        raise NotImplementedError

    def get_all_xrefs(self) -> list[CardXrefRecord]:
        """Return all card cross-reference records in key order."""
        raise NotImplementedError

    def get_all_transactions(self) -> list[TransactionRecord]:
        """Return all transaction records in key order."""
        raise NotImplementedError

    def get_all_cards(self) -> list[CardRecord]:
        """Return all card records in key order."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# In-memory repository for testing
# ---------------------------------------------------------------------------

class InMemoryExportDataRepository(ExportDataRepository):
    """Simple in-memory implementation backed by Python lists."""

    def __init__(self) -> None:
        self.customers: list[CustomerRecord] = []
        self.accounts: list[AccountRecord] = []
        self.xrefs: list[CardXrefRecord] = []
        self.transactions: list[TransactionRecord] = []
        self.cards: list[CardRecord] = []

    def get_all_customers(self) -> list[CustomerRecord]:
        return list(self.customers)

    def get_all_accounts(self) -> list[AccountRecord]:
        return list(self.accounts)

    def get_all_xrefs(self) -> list[CardXrefRecord]:
        return list(self.xrefs)

    def get_all_transactions(self) -> list[TransactionRecord]:
        return list(self.transactions)

    def get_all_cards(self) -> list[CardRecord]:
        return list(self.cards)


# ---------------------------------------------------------------------------
# Export function
# ---------------------------------------------------------------------------

def generate_timestamp() -> str:
    """
    Generate a 26-character timestamp matching the COBOL format.

    Format: YYYY-MM-DD HH:MM:SS.00
    Corresponds to 1050-GENERATE-TIMESTAMP in the COBOL program.
    """
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S") + ".00"


def export_customer_data(
    repo: ExportDataRepository,
    branch_id: str = "0001",
    region_code: str = "NORTH",
    timestamp: Optional[str] = None,
) -> tuple[list[ExportRecord], ExportStatistics]:
    """
    Export all customer data from the repository.

    This is the Python equivalent of the CBEXPORT COBOL program's
    0000-MAIN-PROCESSING paragraph. It reads all records from each
    file type and produces a list of ExportRecord objects.

    Args:
        repo: Data repository to read from.
        branch_id: Branch identifier (default '0001').
        region_code: Region code (default 'NORTH').
        timestamp: Override timestamp (for testing). If None, generates current.

    Returns:
        A tuple of (export_records, statistics).
    """
    if timestamp is None:
        timestamp = generate_timestamp()

    records: list[ExportRecord] = []
    stats = ExportStatistics()
    sequence_counter = 0

    # 2000-EXPORT-CUSTOMERS
    for customer in repo.get_all_customers():
        sequence_counter += 1
        records.append(ExportRecord(
            rec_type="C",
            timestamp=timestamp,
            sequence_num=sequence_counter,
            branch_id=branch_id,
            region_code=region_code,
            customer_data=customer,
        ))
        stats.customer_records += 1
        stats.total_records += 1

    # 3000-EXPORT-ACCOUNTS
    for account in repo.get_all_accounts():
        sequence_counter += 1
        records.append(ExportRecord(
            rec_type="A",
            timestamp=timestamp,
            sequence_num=sequence_counter,
            branch_id=branch_id,
            region_code=region_code,
            account_data=account,
        ))
        stats.account_records += 1
        stats.total_records += 1

    # 4000-EXPORT-XREFS
    for xref in repo.get_all_xrefs():
        sequence_counter += 1
        records.append(ExportRecord(
            rec_type="X",
            timestamp=timestamp,
            sequence_num=sequence_counter,
            branch_id=branch_id,
            region_code=region_code,
            xref_data=xref,
        ))
        stats.xref_records += 1
        stats.total_records += 1

    # 5000-EXPORT-TRANSACTIONS
    for transaction in repo.get_all_transactions():
        sequence_counter += 1
        records.append(ExportRecord(
            rec_type="T",
            timestamp=timestamp,
            sequence_num=sequence_counter,
            branch_id=branch_id,
            region_code=region_code,
            transaction_data=transaction,
        ))
        stats.transaction_records += 1
        stats.total_records += 1

    # 5500-EXPORT-CARDS
    for card in repo.get_all_cards():
        sequence_counter += 1
        records.append(ExportRecord(
            rec_type="D",
            timestamp=timestamp,
            sequence_num=sequence_counter,
            branch_id=branch_id,
            region_code=region_code,
            card_data=card,
        ))
        stats.card_records += 1
        stats.total_records += 1

    return records, stats


def print_export_summary(stats: ExportStatistics) -> None:
    """
    Print the export summary report.

    Corresponds to the DISPLAY statements in 6000-FINALIZE.
    """
    print("CBEXPORT: Export completed")
    print(f"CBEXPORT: Customers Exported: {stats.customer_records}")
    print(f"CBEXPORT: Accounts Exported: {stats.account_records}")
    print(f"CBEXPORT: XRefs Exported: {stats.xref_records}")
    print(f"CBEXPORT: Transactions Exported: {stats.transaction_records}")
    print(f"CBEXPORT: Cards Exported: {stats.card_records}")
    print(f"CBEXPORT: Total Records Exported: {stats.total_records}")
