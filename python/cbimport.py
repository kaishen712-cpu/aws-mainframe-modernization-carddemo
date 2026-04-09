"""
CBIMPORT - Import Customer Data from Branch Migration Export (Python Translation)

Translated from the COBOL program CBIMPORT.CBL in the AWS CardDemo
mainframe modernization project. This module reads export records
produced by CBEXPORT and writes them back to individual repositories.

Original: BATCH COBOL program reading 1 sequential export file, writing
to 5 VSAM files + 1 error file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from cbexport import (
    AccountRecord,
    CardRecord,
    CardXrefRecord,
    CustomerRecord,
    ExportRecord,
    TransactionRecord,
)


# ---------------------------------------------------------------------------
# Import statistics
# ---------------------------------------------------------------------------

@dataclass
class ImportStatistics:
    """Counters matching WS-IMPORT-STATISTICS."""
    total_records_read: int = 0
    customer_records: int = 0
    account_records: int = 0
    xref_records: int = 0
    transaction_records: int = 0
    card_records: int = 0
    error_records: int = 0
    unknown_record_types: int = 0


# ---------------------------------------------------------------------------
# Error record
# ---------------------------------------------------------------------------

@dataclass
class ImportError:
    """
    Error record matching WS-ERROR-RECORD (132 bytes conceptual).

    Created when an unknown record type is encountered during import.
    """
    timestamp: str = ""                 # ERR-TIMESTAMP PIC X(26)
    record_type: str = ""               # ERR-RECORD-TYPE PIC X(01)
    sequence_num: int = 0               # ERR-SEQUENCE PIC 9(07)
    message: str = ""                   # ERR-MESSAGE PIC X(50)


# ---------------------------------------------------------------------------
# Import result
# ---------------------------------------------------------------------------

@dataclass
class ImportResult:
    """
    Complete result of an import operation.

    Contains the imported records by type, any errors encountered,
    and statistics counters.
    """
    customers: list[CustomerRecord] = field(default_factory=list)
    accounts: list[AccountRecord] = field(default_factory=list)
    xrefs: list[CardXrefRecord] = field(default_factory=list)
    transactions: list[TransactionRecord] = field(default_factory=list)
    cards: list[CardRecord] = field(default_factory=list)
    errors: list[ImportError] = field(default_factory=list)
    statistics: ImportStatistics = field(default_factory=ImportStatistics)


# ---------------------------------------------------------------------------
# Repository interface (abstracts VSAM file I/O)
# ---------------------------------------------------------------------------

class ImportDataRepository:
    """
    Abstract interface for writing imported data.

    In the original COBOL program these are sequential WRITEs to
    output files opened in OUTPUT mode. Concrete implementations
    can use a database, in-memory lists, or any other store.
    """

    def write_customer(self, record: CustomerRecord) -> bool:
        """
        Write a customer record.

        Returns True on success, False on error (e.g., duplicate key).
        """
        raise NotImplementedError

    def write_account(self, record: AccountRecord) -> bool:
        """Write an account record."""
        raise NotImplementedError

    def write_xref(self, record: CardXrefRecord) -> bool:
        """Write a card cross-reference record."""
        raise NotImplementedError

    def write_transaction(self, record: TransactionRecord) -> bool:
        """Write a transaction record."""
        raise NotImplementedError

    def write_card(self, record: CardRecord) -> bool:
        """Write a card record."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# In-memory repository for testing
# ---------------------------------------------------------------------------

class InMemoryImportDataRepository(ImportDataRepository):
    """Simple in-memory implementation backed by Python lists."""

    def __init__(self) -> None:
        self.customers: list[CustomerRecord] = []
        self.accounts: list[AccountRecord] = []
        self.xrefs: list[CardXrefRecord] = []
        self.transactions: list[TransactionRecord] = []
        self.cards: list[CardRecord] = []

    def write_customer(self, record: CustomerRecord) -> bool:
        self.customers.append(record)
        return True

    def write_account(self, record: AccountRecord) -> bool:
        self.accounts.append(record)
        return True

    def write_xref(self, record: CardXrefRecord) -> bool:
        self.xrefs.append(record)
        return True

    def write_transaction(self, record: TransactionRecord) -> bool:
        self.transactions.append(record)
        return True

    def write_card(self, record: CardRecord) -> bool:
        self.cards.append(record)
        return True


# ---------------------------------------------------------------------------
# Import function
# ---------------------------------------------------------------------------

def import_customer_data(
    export_records: list[ExportRecord],
    repo: ImportDataRepository,
) -> ImportResult:
    """
    Import customer data from export records into the repository.

    This is the Python equivalent of the CBIMPORT COBOL program's
    0000-MAIN-PROCESSING paragraph. It reads each export record,
    dispatches by record type, and writes to the appropriate repository.

    Args:
        export_records: List of ExportRecord objects (from CBEXPORT).
        repo: Data repository to write to.

    Returns:
        An ImportResult with imported records, errors, and statistics.
    """
    result = ImportResult()

    for export_rec in export_records:
        result.statistics.total_records_read += 1

        if export_rec.rec_type == "C":
            _process_customer_record(export_rec, repo, result)
        elif export_rec.rec_type == "A":
            _process_account_record(export_rec, repo, result)
        elif export_rec.rec_type == "X":
            _process_xref_record(export_rec, repo, result)
        elif export_rec.rec_type == "T":
            _process_transaction_record(export_rec, repo, result)
        elif export_rec.rec_type == "D":
            _process_card_record(export_rec, repo, result)
        else:
            _process_unknown_record(export_rec, result)

    return result


# ---------------------------------------------------------------------------
# Record processors — correspond to COBOL paragraphs 2300-2700
# ---------------------------------------------------------------------------

def _process_customer_record(
    export_rec: ExportRecord,
    repo: ImportDataRepository,
    result: ImportResult,
) -> None:
    """
    Process a customer export record (type 'C').

    Corresponds to 2300-PROCESS-CUSTOMER-RECORD.
    """
    if export_rec.customer_data is None:
        _process_unknown_record(export_rec, result)
        return

    # Map export fields to customer record (identity mapping in Python)
    customer = CustomerRecord(
        cust_id=export_rec.customer_data.cust_id,
        first_name=export_rec.customer_data.first_name,
        middle_name=export_rec.customer_data.middle_name,
        last_name=export_rec.customer_data.last_name,
        addr_line_1=export_rec.customer_data.addr_line_1,
        addr_line_2=export_rec.customer_data.addr_line_2,
        addr_line_3=export_rec.customer_data.addr_line_3,
        addr_state_cd=export_rec.customer_data.addr_state_cd,
        addr_country_cd=export_rec.customer_data.addr_country_cd,
        addr_zip=export_rec.customer_data.addr_zip,
        phone_num_1=export_rec.customer_data.phone_num_1,
        phone_num_2=export_rec.customer_data.phone_num_2,
        ssn=export_rec.customer_data.ssn,
        govt_issued_id=export_rec.customer_data.govt_issued_id,
        dob_yyyy_mm_dd=export_rec.customer_data.dob_yyyy_mm_dd,
        eft_account_id=export_rec.customer_data.eft_account_id,
        pri_card_holder_ind=export_rec.customer_data.pri_card_holder_ind,
        fico_credit_score=export_rec.customer_data.fico_credit_score,
    )

    repo.write_customer(customer)
    result.customers.append(customer)
    result.statistics.customer_records += 1


def _process_account_record(
    export_rec: ExportRecord,
    repo: ImportDataRepository,
    result: ImportResult,
) -> None:
    """
    Process an account export record (type 'A').

    Corresponds to 2400-PROCESS-ACCOUNT-RECORD.
    """
    if export_rec.account_data is None:
        _process_unknown_record(export_rec, result)
        return

    account = AccountRecord(
        acct_id=export_rec.account_data.acct_id,
        active_status=export_rec.account_data.active_status,
        curr_bal=export_rec.account_data.curr_bal,
        credit_limit=export_rec.account_data.credit_limit,
        cash_credit_limit=export_rec.account_data.cash_credit_limit,
        open_date=export_rec.account_data.open_date,
        expiration_date=export_rec.account_data.expiration_date,
        reissue_date=export_rec.account_data.reissue_date,
        curr_cyc_credit=export_rec.account_data.curr_cyc_credit,
        curr_cyc_debit=export_rec.account_data.curr_cyc_debit,
        addr_zip=export_rec.account_data.addr_zip,
        group_id=export_rec.account_data.group_id,
    )

    repo.write_account(account)
    result.accounts.append(account)
    result.statistics.account_records += 1


def _process_xref_record(
    export_rec: ExportRecord,
    repo: ImportDataRepository,
    result: ImportResult,
) -> None:
    """
    Process a cross-reference export record (type 'X').

    Corresponds to 2500-PROCESS-XREF-RECORD.
    """
    if export_rec.xref_data is None:
        _process_unknown_record(export_rec, result)
        return

    xref = CardXrefRecord(
        card_num=export_rec.xref_data.card_num,
        cust_id=export_rec.xref_data.cust_id,
        acct_id=export_rec.xref_data.acct_id,
    )

    repo.write_xref(xref)
    result.xrefs.append(xref)
    result.statistics.xref_records += 1


def _process_transaction_record(
    export_rec: ExportRecord,
    repo: ImportDataRepository,
    result: ImportResult,
) -> None:
    """
    Process a transaction export record (type 'T').

    Corresponds to 2600-PROCESS-TRAN-RECORD.
    """
    if export_rec.transaction_data is None:
        _process_unknown_record(export_rec, result)
        return

    transaction = TransactionRecord(
        tran_id=export_rec.transaction_data.tran_id,
        tran_type_cd=export_rec.transaction_data.tran_type_cd,
        tran_cat_cd=export_rec.transaction_data.tran_cat_cd,
        tran_source=export_rec.transaction_data.tran_source,
        tran_desc=export_rec.transaction_data.tran_desc,
        tran_amt=export_rec.transaction_data.tran_amt,
        tran_merchant_id=export_rec.transaction_data.tran_merchant_id,
        tran_merchant_name=export_rec.transaction_data.tran_merchant_name,
        tran_merchant_city=export_rec.transaction_data.tran_merchant_city,
        tran_merchant_zip=export_rec.transaction_data.tran_merchant_zip,
        tran_card_num=export_rec.transaction_data.tran_card_num,
        tran_orig_ts=export_rec.transaction_data.tran_orig_ts,
        tran_proc_ts=export_rec.transaction_data.tran_proc_ts,
    )

    repo.write_transaction(transaction)
    result.transactions.append(transaction)
    result.statistics.transaction_records += 1


def _process_card_record(
    export_rec: ExportRecord,
    repo: ImportDataRepository,
    result: ImportResult,
) -> None:
    """
    Process a card export record (type 'D').

    Corresponds to 2650-PROCESS-CARD-RECORD.
    """
    if export_rec.card_data is None:
        _process_unknown_record(export_rec, result)
        return

    card = CardRecord(
        card_num=export_rec.card_data.card_num,
        card_acct_id=export_rec.card_data.card_acct_id,
        card_cvv_cd=export_rec.card_data.card_cvv_cd,
        card_embossed_name=export_rec.card_data.card_embossed_name,
        card_expiration_date=export_rec.card_data.card_expiration_date,
        card_active_status=export_rec.card_data.card_active_status,
    )

    repo.write_card(card)
    result.cards.append(card)
    result.statistics.card_records += 1


def _process_unknown_record(
    export_rec: ExportRecord,
    result: ImportResult,
) -> None:
    """
    Process an unknown/invalid export record.

    Corresponds to 2700-PROCESS-UNKNOWN-RECORD.
    """
    error = ImportError(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ".00    ",
        record_type=export_rec.rec_type,
        sequence_num=export_rec.sequence_num,
        message="Unknown record type encountered",
    )
    result.errors.append(error)
    result.statistics.error_records += 1
    result.statistics.unknown_record_types += 1


# ---------------------------------------------------------------------------
# Summary report
# ---------------------------------------------------------------------------

def print_import_summary(stats: ImportStatistics) -> None:
    """
    Print the import summary report.

    Corresponds to the DISPLAY statements in 4000-FINALIZE.
    """
    print("CBIMPORT: Import completed")
    print(f"CBIMPORT: Total Records Read: {stats.total_records_read}")
    print(f"CBIMPORT: Customers Imported: {stats.customer_records}")
    print(f"CBIMPORT: Accounts Imported: {stats.account_records}")
    print(f"CBIMPORT: XRefs Imported: {stats.xref_records}")
    print(f"CBIMPORT: Transactions Imported: {stats.transaction_records}")
    print(f"CBIMPORT: Cards Imported: {stats.card_records}")
    print(f"CBIMPORT: Errors Written: {stats.error_records}")
    print(f"CBIMPORT: Unknown Record Types: {stats.unknown_record_types}")
