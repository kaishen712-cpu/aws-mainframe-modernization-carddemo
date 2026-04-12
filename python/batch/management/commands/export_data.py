"""
Django management command: export_data

Translated from CBEXPORT.cbl — a batch COBOL program that reads
normalized CardDemo files (customers, accounts, cross-references,
transactions, cards) and produces a multi-record flat-file export
for branch migration.

Usage::

    python manage.py export_data --output /path/to/export.dat
    python manage.py export_data --output export.dat --types customer account

Original COBOL structure:
    0000-MAIN-PROCESSING
        1000-INITIALIZE
        2000-EXPORT-CUSTOMERS
        3000-EXPORT-ACCOUNTS
        4000-EXPORT-XREFS
        5000-EXPORT-TRANSACTIONS
        5500-EXPORT-CARDS
        6000-FINALIZE
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from decimal import Decimal
from typing import IO, Any

from python.models.export_record import (
    EXPORT_REC_TYPE_ACCOUNT,
    EXPORT_REC_TYPE_CARD,
    EXPORT_REC_TYPE_CARD_XREF,
    EXPORT_REC_TYPE_CUSTOMER,
    EXPORT_REC_TYPE_TRANSACTION,
    ExportAccountData,
    ExportCardData,
    ExportCardXrefData,
    ExportCustomerData,
    ExportRecord,
    ExportTransactionData,
)
from python.models.records import (
    AccountRecord,
    CardRecord,
    CardXrefRecord,
    CustomerRecord,
    TransactionRecord,
)
from python.repositories.base import (
    AccountRepository,
    CardRepository,
    CardXrefRepository,
    CustomerRepository,
    TransactionRepository,
)

logger = logging.getLogger(__name__)

# Valid record type CLI argument values
VALID_RECORD_TYPES = frozenset(
    {
        "customer",
        "account",
        "xref",
        "transaction",
        "card",
    }
)

# Default branch/region values from COBOL MOVE literals
# Translated from paragraph 2200-CREATE-CUSTOMER-EXP-REC:
#   MOVE '0001' TO EXPORT-BRANCH-ID
#   MOVE 'NORTH' TO EXPORT-REGION-CODE
DEFAULT_BRANCH_ID = "0001"
DEFAULT_REGION_CODE = "NORTH"


class ExportStatistics:
    """Tracks export record counts per type.

    Translated from WS-EXPORT-STATISTICS in CBEXPORT.cbl.
    """

    def __init__(self) -> None:
        self.customer_count: int = 0
        self.account_count: int = 0
        self.xref_count: int = 0
        self.transaction_count: int = 0
        self.card_count: int = 0
        self.total_count: int = 0

    def log_summary(self) -> None:
        """Log the export summary statistics.

        Translated from 6000-FINALIZE in CBEXPORT.cbl.
        """
        logger.info("CBEXPORT: Export completed")
        logger.info("CBEXPORT: Customers Exported: %d", self.customer_count)
        logger.info("CBEXPORT: Accounts Exported: %d", self.account_count)
        logger.info("CBEXPORT: XRefs Exported: %d", self.xref_count)
        logger.info("CBEXPORT: Transactions Exported: %d", self.transaction_count)
        logger.info("CBEXPORT: Cards Exported: %d", self.card_count)
        logger.info("CBEXPORT: Total Records Exported: %d", self.total_count)


def generate_timestamp() -> str:
    """Generate a 26-character formatted timestamp for export records.

    Translated from 1050-GENERATE-TIMESTAMP in CBEXPORT.cbl.
    The COBOL code formats as ``YYYY-MM-DD HH:MM:SS.00``.

    Returns:
        A 26-character timestamp string.
    """
    now = datetime.now(tz=timezone.utc)
    return now.strftime("%Y-%m-%d %H:%M:%S.%f")[:26]


def _next_sequence(counter: list[int]) -> int:
    """Increment and return the next sequence number.

    Translated from ``ADD 1 TO WS-SEQUENCE-COUNTER`` in CBEXPORT.cbl.

    Args:
        counter: A single-element list used as a mutable integer reference.

    Returns:
        The incremented sequence number.
    """
    counter[0] += 1
    return counter[0]


def _build_header(
    rec_type: str,
    timestamp: str,
    sequence: int,
    branch_id: str = DEFAULT_BRANCH_ID,
    region_code: str = DEFAULT_REGION_CODE,
) -> dict[str, Any]:
    """Build the common header fields for an export record.

    Translated from the repeated pattern in paragraphs 2200, 3200, 4200,
    5200, and 5700 of CBEXPORT.cbl.

    Args:
        rec_type: Single-character record type code (C/A/X/T/D).
        timestamp: 26-character formatted timestamp.
        sequence: Monotonically increasing sequence number.
        branch_id: 4-character branch identifier.
        region_code: 5-character region code.

    Returns:
        A dict with the header fields.
    """
    return {
        "record_type": rec_type,
        "timestamp": timestamp,
        "sequence_num": sequence,
        "branch_id": branch_id,
        "region_code": region_code,
    }


def build_customer_export(
    customer: CustomerRecord,
    timestamp: str,
    sequence: int,
) -> ExportRecord:
    """Create an export record from a customer record.

    Translated from 2200-CREATE-CUSTOMER-EXP-REC in CBEXPORT.cbl.
    Maps CUST-* fields to EXP-CUST-* fields in the export record.

    Args:
        customer: The source customer record.
        timestamp: Formatted export timestamp.
        sequence: Sequence number for this record.

    Returns:
        A populated ExportRecord with customer data.
    """
    return ExportRecord(
        export_rec_type=EXPORT_REC_TYPE_CUSTOMER,
        export_timestamp=timestamp,
        export_sequence_num=sequence,
        export_branch_id=DEFAULT_BRANCH_ID,
        export_region_code=DEFAULT_REGION_CODE,
        record_data=ExportCustomerData(
            exp_cust_id=int(customer.cust_id) if customer.cust_id else 0,
            exp_cust_first_name=customer.cust_first_name,
            exp_cust_middle_name=customer.cust_middle_name,
            exp_cust_last_name=customer.cust_last_name,
            exp_cust_addr_lines=[
                customer.cust_addr_line_1,
                customer.cust_addr_line_2,
                customer.cust_addr_line_3,
            ],
            exp_cust_addr_state_cd=customer.cust_addr_state_cd,
            exp_cust_addr_country_cd=customer.cust_addr_country_cd,
            exp_cust_addr_zip=customer.cust_addr_zip,
            exp_cust_phone_nums=[
                customer.cust_phone_num_1,
                customer.cust_phone_num_2,
            ],
            exp_cust_ssn=customer.cust_ssn,
            exp_cust_govt_issued_id=customer.cust_govt_issued_id,
            exp_cust_dob_yyyy_mm_dd=customer.cust_dob_yyyy_mm_dd,
            exp_cust_eft_account_id=customer.cust_eft_account_id,
            exp_cust_pri_card_holder_ind=customer.cust_pri_card_holder_ind,
            exp_cust_fico_credit_score=(
                int(customer.cust_fico_credit_score) if customer.cust_fico_credit_score else 0
            ),
        ),
    )


def build_account_export(
    account: AccountRecord,
    timestamp: str,
    sequence: int,
) -> ExportRecord:
    """Create an export record from an account record.

    Translated from 3200-CREATE-ACCOUNT-EXP-REC in CBEXPORT.cbl.
    Maps ACCT-* fields to EXP-ACCT-* fields.

    Note: Monetary fields are converted from float to Decimal-safe strings
    for the export. The COBOL MOVE preserves the COMP-3 representation.

    Args:
        account: The source account record.
        timestamp: Formatted export timestamp.
        sequence: Sequence number for this record.

    Returns:
        A populated ExportRecord with account data.
    """
    return ExportRecord(
        export_rec_type=EXPORT_REC_TYPE_ACCOUNT,
        export_timestamp=timestamp,
        export_sequence_num=sequence,
        export_branch_id=DEFAULT_BRANCH_ID,
        export_region_code=DEFAULT_REGION_CODE,
        record_data=ExportAccountData(
            exp_acct_id=account.acct_id,
            exp_acct_active_status=account.acct_active_status,
            exp_acct_curr_bal=account.acct_curr_bal,
            exp_acct_credit_limit=account.acct_credit_limit,
            exp_acct_cash_credit_limit=account.acct_cash_credit_limit,
            exp_acct_open_date=account.acct_open_date,
            exp_acct_expiration_date=account.acct_expiration_date,
            exp_acct_reissue_date=account.acct_reissue_date,
            exp_acct_curr_cyc_credit=account.acct_curr_cyc_credit,
            exp_acct_curr_cyc_debit=account.acct_curr_cyc_debit,
            exp_acct_addr_zip=account.acct_addr_zip,
            exp_acct_group_id=account.acct_group_id,
        ),
    )


def build_xref_export(
    xref: CardXrefRecord,
    timestamp: str,
    sequence: int,
) -> ExportRecord:
    """Create an export record from a card cross-reference record.

    Translated from 4200-CREATE-XREF-EXPORT-RECORD in CBEXPORT.cbl.
    Maps XREF-* fields to EXP-XREF-* fields.

    Args:
        xref: The source cross-reference record.
        timestamp: Formatted export timestamp.
        sequence: Sequence number for this record.

    Returns:
        A populated ExportRecord with xref data.
    """
    return ExportRecord(
        export_rec_type=EXPORT_REC_TYPE_CARD_XREF,
        export_timestamp=timestamp,
        export_sequence_num=sequence,
        export_branch_id=DEFAULT_BRANCH_ID,
        export_region_code=DEFAULT_REGION_CODE,
        record_data=ExportCardXrefData(
            exp_xref_card_num=xref.xref_card_num,
            exp_xref_cust_id=xref.xref_cust_id,
            exp_xref_acct_id=(int(xref.xref_acct_id) if xref.xref_acct_id else 0),
        ),
    )


def build_transaction_export(
    tran: TransactionRecord,
    timestamp: str,
    sequence: int,
) -> ExportRecord:
    """Create an export record from a transaction record.

    Translated from 5200-CREATE-TRAN-EXP-REC in CBEXPORT.cbl.
    Maps TRAN-* fields to EXP-TRAN-* fields.

    Args:
        tran: The source transaction record.
        timestamp: Formatted export timestamp.
        sequence: Sequence number for this record.

    Returns:
        A populated ExportRecord with transaction data.
    """
    return ExportRecord(
        export_rec_type=EXPORT_REC_TYPE_TRANSACTION,
        export_timestamp=timestamp,
        export_sequence_num=sequence,
        export_branch_id=DEFAULT_BRANCH_ID,
        export_region_code=DEFAULT_REGION_CODE,
        record_data=ExportTransactionData(
            exp_tran_id=tran.tran_id,
            exp_tran_type_cd=tran.tran_type_cd,
            exp_tran_cat_cd=tran.tran_cat_cd,
            exp_tran_source=tran.tran_source,
            exp_tran_desc=tran.tran_desc,
            exp_tran_amt=tran.tran_amt,
            exp_tran_merchant_id=(int(tran.tran_merchant_id) if tran.tran_merchant_id else 0),
            exp_tran_merchant_name=tran.tran_merchant_name,
            exp_tran_merchant_city=tran.tran_merchant_city,
            exp_tran_merchant_zip=tran.tran_merchant_zip,
            exp_tran_card_num=tran.tran_card_num,
            exp_tran_orig_ts=tran.tran_orig_ts,
            exp_tran_proc_ts=tran.tran_proc_ts,
        ),
    )


def build_card_export(
    card: CardRecord,
    timestamp: str,
    sequence: int,
) -> ExportRecord:
    """Create an export record from a card record.

    Translated from 5700-CREATE-CARD-EXPORT-RECORD in CBEXPORT.cbl.
    Maps CARD-* fields to EXP-CARD-* fields.

    Args:
        card: The source card record.
        timestamp: Formatted export timestamp.
        sequence: Sequence number for this record.

    Returns:
        A populated ExportRecord with card data.
    """
    return ExportRecord(
        export_rec_type=EXPORT_REC_TYPE_CARD,
        export_timestamp=timestamp,
        export_sequence_num=sequence,
        export_branch_id=DEFAULT_BRANCH_ID,
        export_region_code=DEFAULT_REGION_CODE,
        record_data=ExportCardData(
            exp_card_num=card.card_num,
            exp_card_acct_id=(int(card.card_acct_id) if card.card_acct_id else 0),
            exp_card_cvv_cd=(int(card.card_cvv_cd) if card.card_cvv_cd else 0),
            exp_card_embossed_name=card.card_embossed_name,
            exp_card_expiration_date=card.card_expiration_date,
            exp_card_active_status=card.card_active_status,
        ),
    )


def _serialize_record(record: ExportRecord) -> str:
    """Serialize an ExportRecord to a single JSON line for the export file.

    The COBOL program writes 500-byte fixed-length records.  In the Python
    translation we use newline-delimited JSON (NDJSON) — each line is a
    self-describing record that preserves all field data in UTF-8.

    EBCDIC encoding references in the original COBOL are replaced with
    UTF-8 throughout.

    Args:
        record: The export record to serialize.

    Returns:
        A single JSON string (no trailing newline).
    """
    data: dict[str, Any] = {
        "record_type": record.export_rec_type,
        "timestamp": record.export_timestamp,
        "sequence_num": record.export_sequence_num,
        "branch_id": record.export_branch_id,
        "region_code": record.export_region_code,
    }

    if isinstance(record.record_data, ExportCustomerData):
        data["customer"] = {
            "cust_id": record.record_data.exp_cust_id,
            "first_name": record.record_data.exp_cust_first_name,
            "middle_name": record.record_data.exp_cust_middle_name,
            "last_name": record.record_data.exp_cust_last_name,
            "addr_lines": record.record_data.exp_cust_addr_lines,
            "addr_state_cd": record.record_data.exp_cust_addr_state_cd,
            "addr_country_cd": record.record_data.exp_cust_addr_country_cd,
            "addr_zip": record.record_data.exp_cust_addr_zip,
            "phone_nums": record.record_data.exp_cust_phone_nums,
            "ssn": record.record_data.exp_cust_ssn,
            "govt_issued_id": record.record_data.exp_cust_govt_issued_id,
            "dob": record.record_data.exp_cust_dob_yyyy_mm_dd,
            "eft_account_id": record.record_data.exp_cust_eft_account_id,
            "pri_card_holder_ind": (record.record_data.exp_cust_pri_card_holder_ind),
            "fico_credit_score": (record.record_data.exp_cust_fico_credit_score),
        }
    elif isinstance(record.record_data, ExportAccountData):
        data["account"] = {
            "acct_id": record.record_data.exp_acct_id,
            "active_status": record.record_data.exp_acct_active_status,
            "curr_bal": str(Decimal(str(record.record_data.exp_acct_curr_bal))),
            "credit_limit": str(Decimal(str(record.record_data.exp_acct_credit_limit))),
            "cash_credit_limit": str(Decimal(str(record.record_data.exp_acct_cash_credit_limit))),
            "open_date": record.record_data.exp_acct_open_date,
            "expiration_date": record.record_data.exp_acct_expiration_date,
            "reissue_date": record.record_data.exp_acct_reissue_date,
            "curr_cyc_credit": str(Decimal(str(record.record_data.exp_acct_curr_cyc_credit))),
            "curr_cyc_debit": str(Decimal(str(record.record_data.exp_acct_curr_cyc_debit))),
            "addr_zip": record.record_data.exp_acct_addr_zip,
            "group_id": record.record_data.exp_acct_group_id,
        }
    elif isinstance(record.record_data, ExportCardXrefData):
        data["xref"] = {
            "card_num": record.record_data.exp_xref_card_num,
            "cust_id": record.record_data.exp_xref_cust_id,
            "acct_id": record.record_data.exp_xref_acct_id,
        }
    elif isinstance(record.record_data, ExportTransactionData):
        data["transaction"] = {
            "tran_id": record.record_data.exp_tran_id,
            "type_cd": record.record_data.exp_tran_type_cd,
            "cat_cd": record.record_data.exp_tran_cat_cd,
            "source": record.record_data.exp_tran_source,
            "desc": record.record_data.exp_tran_desc,
            "amt": str(Decimal(str(record.record_data.exp_tran_amt))),
            "merchant_id": record.record_data.exp_tran_merchant_id,
            "merchant_name": record.record_data.exp_tran_merchant_name,
            "merchant_city": record.record_data.exp_tran_merchant_city,
            "merchant_zip": record.record_data.exp_tran_merchant_zip,
            "card_num": record.record_data.exp_tran_card_num,
            "orig_ts": record.record_data.exp_tran_orig_ts,
            "proc_ts": record.record_data.exp_tran_proc_ts,
        }
    elif isinstance(record.record_data, ExportCardData):
        data["card"] = {
            "card_num": record.record_data.exp_card_num,
            "acct_id": record.record_data.exp_card_acct_id,
            "cvv_cd": record.record_data.exp_card_cvv_cd,
            "embossed_name": record.record_data.exp_card_embossed_name,
            "expiration_date": record.record_data.exp_card_expiration_date,
            "active_status": record.record_data.exp_card_active_status,
        }

    return json.dumps(data, ensure_ascii=False)


def write_record(file_handle: IO[str], record: ExportRecord) -> None:
    """Write a single export record to the output file.

    Translated from the WRITE EXPORT-OUTPUT-RECORD pattern repeated
    throughout CBEXPORT.cbl (paragraphs 2200, 3200, 4200, 5200, 5700).

    Args:
        file_handle: An open file handle for writing.
        record: The export record to write.

    Raises:
        IOError: If writing fails (translated from 9999-ABEND-PROGRAM).
    """
    line = _serialize_record(record)
    file_handle.write(line + "\n")


def export_customers(
    customers: list[CustomerRecord],
    file_handle: IO[str],
    timestamp: str,
    seq_counter: list[int],
    stats: ExportStatistics,
) -> None:
    """Export all customer records.

    Translated from 2000-EXPORT-CUSTOMERS in CBEXPORT.cbl.

    Args:
        customers: List of customer records to export.
        file_handle: Open file handle for writing.
        timestamp: Formatted export timestamp.
        seq_counter: Mutable sequence counter.
        stats: Export statistics tracker.
    """
    logger.info("CBEXPORT: Processing customer records")

    for customer in customers:
        seq = _next_sequence(seq_counter)
        record = build_customer_export(customer, timestamp, seq)
        write_record(file_handle, record)
        stats.customer_count += 1
        stats.total_count += 1

    logger.info("CBEXPORT: Customers exported: %d", stats.customer_count)


def export_accounts(
    accounts: list[AccountRecord],
    file_handle: IO[str],
    timestamp: str,
    seq_counter: list[int],
    stats: ExportStatistics,
) -> None:
    """Export all account records.

    Translated from 3000-EXPORT-ACCOUNTS in CBEXPORT.cbl.

    Args:
        accounts: List of account records to export.
        file_handle: Open file handle for writing.
        timestamp: Formatted export timestamp.
        seq_counter: Mutable sequence counter.
        stats: Export statistics tracker.
    """
    logger.info("CBEXPORT: Processing account records")

    for account in accounts:
        seq = _next_sequence(seq_counter)
        record = build_account_export(account, timestamp, seq)
        write_record(file_handle, record)
        stats.account_count += 1
        stats.total_count += 1

    logger.info("CBEXPORT: Accounts exported: %d", stats.account_count)


def export_xrefs(
    xrefs: list[CardXrefRecord],
    file_handle: IO[str],
    timestamp: str,
    seq_counter: list[int],
    stats: ExportStatistics,
) -> None:
    """Export all card cross-reference records.

    Translated from 4000-EXPORT-XREFS in CBEXPORT.cbl.

    Args:
        xrefs: List of cross-reference records to export.
        file_handle: Open file handle for writing.
        timestamp: Formatted export timestamp.
        seq_counter: Mutable sequence counter.
        stats: Export statistics tracker.
    """
    logger.info("CBEXPORT: Processing cross-reference records")

    for xref in xrefs:
        seq = _next_sequence(seq_counter)
        record = build_xref_export(xref, timestamp, seq)
        write_record(file_handle, record)
        stats.xref_count += 1
        stats.total_count += 1

    logger.info("CBEXPORT: Cross-references exported: %d", stats.xref_count)


def export_transactions(
    transactions: list[TransactionRecord],
    file_handle: IO[str],
    timestamp: str,
    seq_counter: list[int],
    stats: ExportStatistics,
) -> None:
    """Export all transaction records.

    Translated from 5000-EXPORT-TRANSACTIONS in CBEXPORT.cbl.

    Args:
        transactions: List of transaction records to export.
        file_handle: Open file handle for writing.
        timestamp: Formatted export timestamp.
        seq_counter: Mutable sequence counter.
        stats: Export statistics tracker.
    """
    logger.info("CBEXPORT: Processing transaction records")

    for tran in transactions:
        seq = _next_sequence(seq_counter)
        record = build_transaction_export(tran, timestamp, seq)
        write_record(file_handle, record)
        stats.transaction_count += 1
        stats.total_count += 1

    logger.info("CBEXPORT: Transactions exported: %d", stats.transaction_count)


def export_cards(
    cards: list[CardRecord],
    file_handle: IO[str],
    timestamp: str,
    seq_counter: list[int],
    stats: ExportStatistics,
) -> None:
    """Export all card records.

    Translated from 5500-EXPORT-CARDS in CBEXPORT.cbl.

    Args:
        cards: List of card records to export.
        file_handle: Open file handle for writing.
        timestamp: Formatted export timestamp.
        seq_counter: Mutable sequence counter.
        stats: Export statistics tracker.
    """
    logger.info("CBEXPORT: Processing card records")

    for card in cards:
        seq = _next_sequence(seq_counter)
        record = build_card_export(card, timestamp, seq)
        write_record(file_handle, record)
        stats.card_count += 1
        stats.total_count += 1

    logger.info("CBEXPORT: Cards exported: %d", stats.card_count)


def run_export(
    output_path: str,
    record_types: set[str] | None,
    customer_repo: CustomerRepository,
    account_repo: AccountRepository,
    xref_repo: CardXrefRepository,
    transaction_repo: TransactionRepository,
    card_repo: CardRepository,
) -> ExportStatistics:
    """Execute the full export process.

    Translated from 0000-MAIN-PROCESSING in CBEXPORT.cbl.  Opens the
    output file, generates a timestamp, and sequentially exports each
    record type requested.

    Args:
        output_path: File system path for the output export file.
        record_types: Set of record type names to export, or None for all.
        customer_repo: Repository providing customer data.
        account_repo: Repository providing account data.
        xref_repo: Repository providing cross-reference data.
        transaction_repo: Repository providing transaction data.
        card_repo: Repository providing card data.

    Returns:
        The export statistics with counts per record type.

    Raises:
        IOError: If the output file cannot be opened or written
            (translated from 9999-ABEND-PROGRAM).
    """
    export_all = record_types is None or len(record_types) == 0

    # 1000-INITIALIZE
    logger.info("CBEXPORT: Starting Customer Data Export")
    timestamp = generate_timestamp()
    logger.info("CBEXPORT: Export Date: %s", timestamp[:10])
    logger.info("CBEXPORT: Export Time: %s", timestamp[11:19])

    stats = ExportStatistics()
    seq_counter: list[int] = [0]

    with open(output_path, "w", encoding="utf-8") as fh:
        # 2000-EXPORT-CUSTOMERS
        if export_all or "customer" in record_types:  # type: ignore[operator]
            customers = _load_all_customers(customer_repo)
            export_customers(customers, fh, timestamp, seq_counter, stats)

        # 3000-EXPORT-ACCOUNTS
        if export_all or "account" in record_types:  # type: ignore[operator]
            accounts = account_repo.list_all()
            export_accounts(accounts, fh, timestamp, seq_counter, stats)

        # 4000-EXPORT-XREFS
        if export_all or "xref" in record_types:  # type: ignore[operator]
            xrefs = _load_all_xrefs(xref_repo)
            export_xrefs(xrefs, fh, timestamp, seq_counter, stats)

        # 5000-EXPORT-TRANSACTIONS
        if export_all or "transaction" in record_types:  # type: ignore[operator]
            transactions = _load_all_transactions(transaction_repo)
            export_transactions(transactions, fh, timestamp, seq_counter, stats)

        # 5500-EXPORT-CARDS
        if export_all or "card" in record_types:  # type: ignore[operator]
            cards = _load_all_cards(card_repo)
            export_cards(cards, fh, timestamp, seq_counter, stats)

    # 6000-FINALIZE
    stats.log_summary()
    return stats


def _load_all_customers(repo: CustomerRepository) -> list[CustomerRecord]:
    """Load all customers from the repository.

    The base CustomerRepository interface only provides lookup_by_id.
    If the repository has a list_all method (e.g., in-memory impl),
    use it; otherwise return an empty list.

    Args:
        repo: Customer repository instance.

    Returns:
        List of all customer records.
    """
    if hasattr(repo, "list_all"):
        return repo.list_all()  # type: ignore[attr-defined]
    if hasattr(repo, "_store"):
        return list(repo._store.values())  # type: ignore[attr-defined]
    return []


def _load_all_xrefs(repo: CardXrefRepository) -> list[CardXrefRecord]:
    """Load all cross-references from the repository.

    Args:
        repo: Card cross-reference repository instance.

    Returns:
        List of all xref records.
    """
    if hasattr(repo, "list_all"):
        return repo.list_all()  # type: ignore[attr-defined]
    if hasattr(repo, "_by_card"):
        return list(repo._by_card.values())  # type: ignore[attr-defined]
    return []


def _load_all_transactions(
    repo: TransactionRepository,
) -> list[TransactionRecord]:
    """Load all transactions from the repository.

    Args:
        repo: Transaction repository instance.

    Returns:
        List of all transaction records.
    """
    if hasattr(repo, "list_all"):
        return repo.list_all()  # type: ignore[attr-defined]
    if hasattr(repo, "_store"):
        return list(repo._store.values())  # type: ignore[attr-defined]
    return []


def _load_all_cards(repo: CardRepository) -> list[CardRecord]:
    """Load all cards from the repository.

    Args:
        repo: Card repository instance.

    Returns:
        List of all card records.
    """
    if hasattr(repo, "list_all"):
        return repo.list_all()  # type: ignore[attr-defined]
    if hasattr(repo, "_store"):
        return list(repo._store.values())  # type: ignore[attr-defined]
    return []


def main(args: list[str] | None = None) -> int:
    """CLI entry point for standalone execution (without Django).

    Provides argument parsing for the export command.  In a full Django
    deployment this would be wrapped in a management command's ``handle()``
    method.

    Args:
        args: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 for success, 1 for error).
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Export CardDemo data to multi-record flat file. Translated from CBEXPORT.cbl."
    )
    parser.add_argument(
        "--output",
        "-o",
        required=True,
        help="Output file path for the export data.",
    )
    parser.add_argument(
        "--types",
        nargs="*",
        choices=sorted(VALID_RECORD_TYPES),
        help="Record types to export (default: all). "
        "Choose from: account, card, customer, transaction, xref.",
    )

    parsed = parser.parse_args(args)

    record_types = set(parsed.types) if parsed.types else None

    # For standalone CLI, use in-memory repos (empty — real data
    # would come from Django ORM in production)
    from python.repositories.in_memory import (
        InMemoryAccountRepository,
        InMemoryCardRepository,
        InMemoryCardXrefRepository,
        InMemoryCustomerRepository,
        InMemoryTransactionRepository,
    )

    logging.basicConfig(level=logging.INFO, stream=sys.stderr)

    try:
        run_export(
            output_path=parsed.output,
            record_types=record_types,
            customer_repo=InMemoryCustomerRepository(),
            account_repo=InMemoryAccountRepository(),
            xref_repo=InMemoryCardXrefRepository(),
            transaction_repo=InMemoryTransactionRepository(),
            card_repo=InMemoryCardRepository(),
        )
        return 0
    except OSError as exc:
        logger.error("CBEXPORT: ABENDING PROGRAM — %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
