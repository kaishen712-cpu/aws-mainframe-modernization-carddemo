"""
Django management command: import_data

Translated from CBIMPORT.cbl — a batch COBOL program that reads a
multi-record export file (produced by CBEXPORT) and splits it into
separate normalized target records (customer, account, card-xref,
transaction, card) with validation and error reporting.

Usage::

    python manage.py import_data --input /path/to/export.dat

Original COBOL structure:
    0000-MAIN-PROCESSING
        1000-INITIALIZE
        2000-PROCESS-EXPORT-FILE
            2100-READ-EXPORT-RECORD
            2200-PROCESS-RECORD-BY-TYPE
                2300-PROCESS-CUSTOMER-RECORD
                2400-PROCESS-ACCOUNT-RECORD
                2500-PROCESS-XREF-RECORD
                2600-PROCESS-TRAN-RECORD
                2650-PROCESS-CARD-RECORD
                2700-PROCESS-UNKNOWN-RECORD
        3000-VALIDATE-IMPORT
        4000-FINALIZE
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from python.models.export_record import (
    EXPORT_REC_TYPE_ACCOUNT,
    EXPORT_REC_TYPE_CARD,
    EXPORT_REC_TYPE_CARD_XREF,
    EXPORT_REC_TYPE_CUSTOMER,
    EXPORT_REC_TYPE_TRANSACTION,
)
from python.models.records import (
    AccountRecord,
    CardRecord,
    CardXrefRecord,
    CustomerRecord,
    TransactionRecord,
)

logger = logging.getLogger(__name__)


@dataclass
class ImportStatistics:
    """Tracks import record counts and errors.

    Translated from WS-IMPORT-STATISTICS in CBIMPORT.cbl.
    """

    total_records_read: int = 0
    customer_count: int = 0
    account_count: int = 0
    xref_count: int = 0
    transaction_count: int = 0
    card_count: int = 0
    error_count: int = 0
    unknown_type_count: int = 0

    def log_summary(self) -> None:
        """Log the import summary statistics.

        Translated from 4000-FINALIZE in CBIMPORT.cbl.
        """
        logger.info("CBIMPORT: Import completed")
        logger.info("CBIMPORT: Total Records Read: %d", self.total_records_read)
        logger.info("CBIMPORT: Customers Imported: %d", self.customer_count)
        logger.info("CBIMPORT: Accounts Imported: %d", self.account_count)
        logger.info("CBIMPORT: XRefs Imported: %d", self.xref_count)
        logger.info("CBIMPORT: Transactions Imported: %d", self.transaction_count)
        logger.info("CBIMPORT: Cards Imported: %d", self.card_count)
        logger.info("CBIMPORT: Errors Written: %d", self.error_count)
        logger.info("CBIMPORT: Unknown Record Types: %d", self.unknown_type_count)


@dataclass
class ErrorRecord:
    """Error record written for invalid import records.

    Translated from WS-ERROR-RECORD in CBIMPORT.cbl.
    """

    timestamp: str
    record_type: str
    sequence: int
    message: str

    def format(self) -> str:
        """Format the error as a pipe-delimited string.

        Matches the COBOL layout: timestamp|type|sequence|message.

        Returns:
            A formatted error string.
        """
        return f"{self.timestamp}|{self.record_type}|{self.sequence:07d}|{self.message}"


def _generate_error_timestamp() -> str:
    """Generate a timestamp for error records.

    Translated from ``MOVE FUNCTION CURRENT-DATE TO ERR-TIMESTAMP``
    in 2700-PROCESS-UNKNOWN-RECORD of CBIMPORT.cbl.

    Returns:
        A 26-character timestamp string.
    """
    now = datetime.now(tz=timezone.utc)
    return now.strftime("%Y-%m-%d %H:%M:%S.%f")[:26]


def _safe_int(value: Any, default: int = 0) -> int:
    """Safely convert a value to int.

    Args:
        value: The value to convert.
        default: Default if conversion fails.

    Returns:
        The integer value or default.
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _safe_decimal_str(value: Any, default: str = "0.0") -> float:
    """Safely convert a value to float via Decimal for precision.

    Uses Decimal as an intermediate step to preserve precision from
    the JSON string representation.

    Args:
        value: The value to convert (string, int, or float).
        default: Default string if conversion fails.

    Returns:
        The float value.
    """
    try:
        return float(Decimal(str(value)))
    except (InvalidOperation, ValueError, TypeError):
        return float(Decimal(default))


def validate_record_format(data: dict[str, Any]) -> str | None:
    """Validate that a parsed JSON record has the required header fields.

    Translated from the implicit validation in CBIMPORT.cbl — the COBOL
    program checks record type via EVALUATE and abends on file errors.

    Args:
        data: Parsed JSON record dictionary.

    Returns:
        An error message string if invalid, or None if valid.
    """
    required_fields = ["record_type", "timestamp", "sequence_num"]
    for field in required_fields:
        if field not in data:
            return f"Missing required field: {field}"

    rec_type = data.get("record_type", "")
    valid_types = {
        EXPORT_REC_TYPE_CUSTOMER,
        EXPORT_REC_TYPE_ACCOUNT,
        EXPORT_REC_TYPE_CARD_XREF,
        EXPORT_REC_TYPE_TRANSACTION,
        EXPORT_REC_TYPE_CARD,
    }
    if rec_type not in valid_types:
        return f"Unknown record type: {rec_type}"

    return None


def parse_customer_record(data: dict[str, Any]) -> CustomerRecord:
    """Parse a customer record from export JSON data.

    Translated from 2300-PROCESS-CUSTOMER-RECORD in CBIMPORT.cbl.
    Maps EXP-CUST-* fields back to CUST-* fields.

    Args:
        data: The ``customer`` sub-dict from the export record.

    Returns:
        A populated CustomerRecord.
    """
    addr_lines = data.get("addr_lines", ["", "", ""])
    phone_nums = data.get("phone_nums", ["", ""])

    return CustomerRecord(
        cust_id=str(data.get("cust_id", "")),
        cust_first_name=str(data.get("first_name", "")),
        cust_middle_name=str(data.get("middle_name", "")),
        cust_last_name=str(data.get("last_name", "")),
        cust_addr_line_1=str(addr_lines[0]) if len(addr_lines) > 0 else "",
        cust_addr_line_2=str(addr_lines[1]) if len(addr_lines) > 1 else "",
        cust_addr_line_3=str(addr_lines[2]) if len(addr_lines) > 2 else "",
        cust_addr_state_cd=str(data.get("addr_state_cd", "")),
        cust_addr_country_cd=str(data.get("addr_country_cd", "")),
        cust_addr_zip=str(data.get("addr_zip", "")),
        cust_phone_num_1=str(phone_nums[0]) if len(phone_nums) > 0 else "",
        cust_phone_num_2=str(phone_nums[1]) if len(phone_nums) > 1 else "",
        cust_ssn=str(data.get("ssn", "")),
        cust_govt_issued_id=str(data.get("govt_issued_id", "")),
        cust_dob_yyyy_mm_dd=str(data.get("dob", "")),
        cust_eft_account_id=str(data.get("eft_account_id", "")),
        cust_pri_card_holder_ind=str(data.get("pri_card_holder_ind", "")),
        cust_fico_credit_score=str(data.get("fico_credit_score", "")),
    )


def parse_account_record(data: dict[str, Any]) -> AccountRecord:
    """Parse an account record from export JSON data.

    Translated from 2400-PROCESS-ACCOUNT-RECORD in CBIMPORT.cbl.
    Maps EXP-ACCT-* fields back to ACCT-* fields.

    Args:
        data: The ``account`` sub-dict from the export record.

    Returns:
        A populated AccountRecord.
    """
    return AccountRecord(
        acct_id=str(data.get("acct_id", "")),
        acct_active_status=str(data.get("active_status", "")),
        acct_curr_bal=_safe_decimal_str(data.get("curr_bal", "0")),
        acct_credit_limit=_safe_decimal_str(data.get("credit_limit", "0")),
        acct_cash_credit_limit=_safe_decimal_str(data.get("cash_credit_limit", "0")),
        acct_open_date=str(data.get("open_date", "")),
        acct_expiration_date=str(data.get("expiration_date", "")),
        acct_reissue_date=str(data.get("reissue_date", "")),
        acct_curr_cyc_credit=_safe_decimal_str(data.get("curr_cyc_credit", "0")),
        acct_curr_cyc_debit=_safe_decimal_str(data.get("curr_cyc_debit", "0")),
        acct_addr_zip=str(data.get("addr_zip", "")),
        acct_group_id=str(data.get("group_id", "")),
    )


def parse_xref_record(data: dict[str, Any]) -> CardXrefRecord:
    """Parse a card cross-reference record from export JSON data.

    Translated from 2500-PROCESS-XREF-RECORD in CBIMPORT.cbl.
    Maps EXP-XREF-* fields back to XREF-* fields.

    Args:
        data: The ``xref`` sub-dict from the export record.

    Returns:
        A populated CardXrefRecord.
    """
    return CardXrefRecord(
        xref_card_num=str(data.get("card_num", "")),
        xref_cust_id=str(data.get("cust_id", "")),
        xref_acct_id=str(data.get("acct_id", "")),
    )


def parse_transaction_record(data: dict[str, Any]) -> TransactionRecord:
    """Parse a transaction record from export JSON data.

    Translated from 2600-PROCESS-TRAN-RECORD in CBIMPORT.cbl.
    Maps EXP-TRAN-* fields back to TRAN-* fields.

    Args:
        data: The ``transaction`` sub-dict from the export record.

    Returns:
        A populated TransactionRecord.
    """
    return TransactionRecord(
        tran_id=str(data.get("tran_id", "")),
        tran_type_cd=str(data.get("type_cd", "")),
        tran_cat_cd=str(data.get("cat_cd", "")),
        tran_source=str(data.get("source", "")),
        tran_desc=str(data.get("desc", "")),
        tran_amt=_safe_decimal_str(data.get("amt", "0")),
        tran_merchant_id=str(data.get("merchant_id", "")),
        tran_merchant_name=str(data.get("merchant_name", "")),
        tran_merchant_city=str(data.get("merchant_city", "")),
        tran_merchant_zip=str(data.get("merchant_zip", "")),
        tran_card_num=str(data.get("card_num", "")),
        tran_orig_ts=str(data.get("orig_ts", "")),
        tran_proc_ts=str(data.get("proc_ts", "")),
    )


def parse_card_record(data: dict[str, Any]) -> CardRecord:
    """Parse a card record from export JSON data.

    Translated from 2650-PROCESS-CARD-RECORD in CBIMPORT.cbl.
    Maps EXP-CARD-* fields back to CARD-* fields.

    Args:
        data: The ``card`` sub-dict from the export record.

    Returns:
        A populated CardRecord.
    """
    return CardRecord(
        card_num=str(data.get("card_num", "")),
        card_acct_id=str(data.get("acct_id", "")),
        card_cvv_cd=str(data.get("cvv_cd", "")),
        card_embossed_name=str(data.get("embossed_name", "")),
        card_expiration_date=str(data.get("expiration_date", "")),
        card_active_status=str(data.get("active_status", "")),
    )


@dataclass
class ImportResult:
    """Container for all records parsed during import.

    Holds lists of each record type and the error list for reporting.
    """

    customers: list[CustomerRecord]
    accounts: list[AccountRecord]
    xrefs: list[CardXrefRecord]
    transactions: list[TransactionRecord]
    cards: list[CardRecord]
    errors: list[ErrorRecord]
    stats: ImportStatistics


def process_record_by_type(
    data: dict[str, Any],
    errors: list[ErrorRecord],
    stats: ImportStatistics,
) -> CustomerRecord | AccountRecord | CardXrefRecord | TransactionRecord | CardRecord | None:
    """Route a parsed record to the appropriate type handler.

    Translated from 2200-PROCESS-RECORD-BY-TYPE in CBIMPORT.cbl.
    Uses the ``record_type`` field to dispatch to the correct parser.

    Args:
        data: Parsed JSON record dictionary.
        errors: Mutable list to append error records to.
        stats: Mutable statistics tracker.

    Returns:
        The parsed record, or None if the record was invalid.
    """
    rec_type = data.get("record_type", "")
    seq_num = _safe_int(data.get("sequence_num", 0))

    # Validate record format before processing
    validation_error = validate_record_format(data)
    if validation_error is not None:
        errors.append(
            ErrorRecord(
                timestamp=_generate_error_timestamp(),
                record_type=str(rec_type),
                sequence=seq_num,
                message=validation_error,
            )
        )
        stats.error_count += 1
        return None

    # EVALUATE EXPORT-REC-TYPE in CBIMPORT.cbl
    if rec_type == EXPORT_REC_TYPE_CUSTOMER:
        return _process_customer(data, errors, stats, seq_num)
    if rec_type == EXPORT_REC_TYPE_ACCOUNT:
        return _process_account(data, errors, stats, seq_num)
    if rec_type == EXPORT_REC_TYPE_CARD_XREF:
        return _process_xref(data, errors, stats, seq_num)
    if rec_type == EXPORT_REC_TYPE_TRANSACTION:
        return _process_transaction(data, errors, stats, seq_num)
    if rec_type == EXPORT_REC_TYPE_CARD:
        return _process_card(data, errors, stats, seq_num)

    # 2700-PROCESS-UNKNOWN-RECORD
    stats.unknown_type_count += 1
    errors.append(
        ErrorRecord(
            timestamp=_generate_error_timestamp(),
            record_type=str(rec_type),
            sequence=seq_num,
            message="Unknown record type encountered",
        )
    )
    stats.error_count += 1
    return None


def _process_customer(
    data: dict[str, Any],
    errors: list[ErrorRecord],
    stats: ImportStatistics,
    seq_num: int,
) -> CustomerRecord | None:
    """Process a customer record from the export file.

    Args:
        data: Full record dict with ``customer`` sub-dict.
        errors: Mutable error list.
        stats: Mutable statistics.
        seq_num: Record sequence number for error reporting.

    Returns:
        Parsed CustomerRecord or None on error.
    """
    cust_data = data.get("customer")
    if cust_data is None:
        errors.append(
            ErrorRecord(
                timestamp=_generate_error_timestamp(),
                record_type=EXPORT_REC_TYPE_CUSTOMER,
                sequence=seq_num,
                message="Customer record missing data section",
            )
        )
        stats.error_count += 1
        return None

    record = parse_customer_record(cust_data)
    stats.customer_count += 1
    return record


def _process_account(
    data: dict[str, Any],
    errors: list[ErrorRecord],
    stats: ImportStatistics,
    seq_num: int,
) -> AccountRecord | None:
    """Process an account record from the export file.

    Args:
        data: Full record dict with ``account`` sub-dict.
        errors: Mutable error list.
        stats: Mutable statistics.
        seq_num: Record sequence number for error reporting.

    Returns:
        Parsed AccountRecord or None on error.
    """
    acct_data = data.get("account")
    if acct_data is None:
        errors.append(
            ErrorRecord(
                timestamp=_generate_error_timestamp(),
                record_type=EXPORT_REC_TYPE_ACCOUNT,
                sequence=seq_num,
                message="Account record missing data section",
            )
        )
        stats.error_count += 1
        return None

    record = parse_account_record(acct_data)
    stats.account_count += 1
    return record


def _process_xref(
    data: dict[str, Any],
    errors: list[ErrorRecord],
    stats: ImportStatistics,
    seq_num: int,
) -> CardXrefRecord | None:
    """Process a cross-reference record from the export file.

    Args:
        data: Full record dict with ``xref`` sub-dict.
        errors: Mutable error list.
        stats: Mutable statistics.
        seq_num: Record sequence number for error reporting.

    Returns:
        Parsed CardXrefRecord or None on error.
    """
    xref_data = data.get("xref")
    if xref_data is None:
        errors.append(
            ErrorRecord(
                timestamp=_generate_error_timestamp(),
                record_type=EXPORT_REC_TYPE_CARD_XREF,
                sequence=seq_num,
                message="Xref record missing data section",
            )
        )
        stats.error_count += 1
        return None

    record = parse_xref_record(xref_data)
    stats.xref_count += 1
    return record


def _process_transaction(
    data: dict[str, Any],
    errors: list[ErrorRecord],
    stats: ImportStatistics,
    seq_num: int,
) -> TransactionRecord | None:
    """Process a transaction record from the export file.

    Args:
        data: Full record dict with ``transaction`` sub-dict.
        errors: Mutable error list.
        stats: Mutable statistics.
        seq_num: Record sequence number for error reporting.

    Returns:
        Parsed TransactionRecord or None on error.
    """
    tran_data = data.get("transaction")
    if tran_data is None:
        errors.append(
            ErrorRecord(
                timestamp=_generate_error_timestamp(),
                record_type=EXPORT_REC_TYPE_TRANSACTION,
                sequence=seq_num,
                message="Transaction record missing data section",
            )
        )
        stats.error_count += 1
        return None

    record = parse_transaction_record(tran_data)
    stats.transaction_count += 1
    return record


def _process_card(
    data: dict[str, Any],
    errors: list[ErrorRecord],
    stats: ImportStatistics,
    seq_num: int,
) -> CardRecord | None:
    """Process a card record from the export file.

    Args:
        data: Full record dict with ``card`` sub-dict.
        errors: Mutable error list.
        stats: Mutable statistics.
        seq_num: Record sequence number for error reporting.

    Returns:
        Parsed CardRecord or None on error.
    """
    card_data = data.get("card")
    if card_data is None:
        errors.append(
            ErrorRecord(
                timestamp=_generate_error_timestamp(),
                record_type=EXPORT_REC_TYPE_CARD,
                sequence=seq_num,
                message="Card record missing data section",
            )
        )
        stats.error_count += 1
        return None

    record = parse_card_record(card_data)
    stats.card_count += 1
    return record


def run_import(
    input_path: str,
    error_path: str | None = None,
) -> ImportResult:
    """Execute the full import process.

    Translated from 0000-MAIN-PROCESSING in CBIMPORT.cbl.  Reads the
    export file line by line, parses each record, and collects results.

    Uses atomic processing: all records are parsed first, then committed.
    Invalid records are logged but do not stop processing of valid ones.

    Args:
        input_path: File system path for the input export file.
        error_path: Optional path for the error report file.  If None,
            errors are only logged.

    Returns:
        ImportResult containing all parsed records and statistics.

    Raises:
        FileNotFoundError: If the input file does not exist.
        IOError: If the input file cannot be read
            (translated from 9999-ABEND-PROGRAM).
    """
    # 1000-INITIALIZE
    logger.info("CBIMPORT: Starting Customer Data Import")
    import_date = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    import_time = datetime.now(tz=timezone.utc).strftime("%H:%M:%S")
    logger.info("CBIMPORT: Import Date: %s", import_date)
    logger.info("CBIMPORT: Import Time: %s", import_time)

    stats = ImportStatistics()
    errors: list[ErrorRecord] = []
    customers: list[CustomerRecord] = []
    accounts: list[AccountRecord] = []
    xrefs: list[CardXrefRecord] = []
    transactions: list[TransactionRecord] = []
    cards: list[CardRecord] = []

    # 2000-PROCESS-EXPORT-FILE
    with open(input_path, encoding="utf-8") as fh:
        for line_num, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue

            stats.total_records_read += 1

            # 2100-READ-EXPORT-RECORD — parse JSON line
            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(
                    ErrorRecord(
                        timestamp=_generate_error_timestamp(),
                        record_type="?",
                        sequence=line_num,
                        message=f"Invalid JSON on line {line_num}: {exc}",
                    )
                )
                stats.error_count += 1
                continue

            # 2200-PROCESS-RECORD-BY-TYPE
            record = process_record_by_type(data, errors, stats)
            if record is None:
                continue

            _collect_record(record, customers, accounts, xrefs, transactions, cards)

    # 3000-VALIDATE-IMPORT
    logger.info("CBIMPORT: Import validation completed")
    if not errors:
        logger.info("CBIMPORT: No validation errors detected")

    # Write error report if path provided
    if error_path and errors:
        _write_error_report(error_path, errors)

    # 4000-FINALIZE
    stats.log_summary()

    return ImportResult(
        customers=customers,
        accounts=accounts,
        xrefs=xrefs,
        transactions=transactions,
        cards=cards,
        errors=errors,
        stats=stats,
    )


def _collect_record(
    record: (CustomerRecord | AccountRecord | CardXrefRecord | TransactionRecord | CardRecord),
    customers: list[CustomerRecord],
    accounts: list[AccountRecord],
    xrefs: list[CardXrefRecord],
    transactions: list[TransactionRecord],
    cards: list[CardRecord],
) -> None:
    """Append a parsed record to the appropriate collection.

    Args:
        record: The parsed record to collect.
        customers: Customer record collection.
        accounts: Account record collection.
        xrefs: Cross-reference record collection.
        transactions: Transaction record collection.
        cards: Card record collection.
    """
    if isinstance(record, CustomerRecord):
        customers.append(record)
    elif isinstance(record, AccountRecord):
        accounts.append(record)
    elif isinstance(record, CardXrefRecord):
        xrefs.append(record)
    elif isinstance(record, TransactionRecord):
        transactions.append(record)
    elif isinstance(record, CardRecord):
        cards.append(record)


def _write_error_report(error_path: str, errors: list[ErrorRecord]) -> None:
    """Write error records to the error report file.

    Translated from 2750-WRITE-ERROR in CBIMPORT.cbl.

    Args:
        error_path: File path for the error report.
        errors: List of error records to write.
    """
    try:
        with open(error_path, "w", encoding="utf-8") as efh:
            for err in errors:
                efh.write(err.format() + "\n")
        logger.info(
            "CBIMPORT: Error report written to %s (%d errors)",
            error_path,
            len(errors),
        )
    except OSError as exc:
        logger.error("CBIMPORT: Failed to write error report: %s", exc)


def main(args: list[str] | None = None) -> int:
    """CLI entry point for standalone execution (without Django).

    Provides argument parsing for the import command.  In a full Django
    deployment this would be wrapped in a management command's ``handle()``
    method.

    Args:
        args: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 for success, 1 for error).
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Import CardDemo data from multi-record flat file. "
        "Translated from CBIMPORT.cbl."
    )
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        dest="input_file",
        help="Input file path for the export data to import.",
    )
    parser.add_argument(
        "--errors",
        "-e",
        dest="error_file",
        default=None,
        help="Output file path for error report (optional).",
    )

    parsed = parser.parse_args(args)

    logging.basicConfig(level=logging.INFO, stream=sys.stderr)

    try:
        result = run_import(
            input_path=parsed.input_file,
            error_path=parsed.error_file,
        )
        if result.stats.error_count > 0:
            logger.warning(
                "CBIMPORT: Completed with %d errors",
                result.stats.error_count,
            )
        return 0
    except FileNotFoundError as exc:
        logger.error("CBIMPORT: ABENDING PROGRAM — %s", exc)
        return 1
    except OSError as exc:
        logger.error("CBIMPORT: ABENDING PROGRAM — %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
