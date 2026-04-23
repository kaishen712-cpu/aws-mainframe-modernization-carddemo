"""
CBSTM03B - Statement Report Subroutine (Python Translation)

Translated from the COBOL program CBSTM03B.CBL in the AWS CardDemo
mainframe modernization project. This module provides file I/O helper
functions used by the CBSTM03A account statement program.

Original: Batch COBOL subroutine called via CALL 'CBSTM03B' USING
LK-M03B-AREA. Handles open, read, and close operations for four files:
TRNXFILE (transaction), XREFFILE (cross-reference), CUSTFILE (customer),
and ACCTFILE (account).

In this Python translation, the subroutine is implemented as a
StatementFileHandler class that wraps repository interfaces for each
file type and provides open/read/close semantics matching the original.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional


# ---------------------------------------------------------------------------
# Constants (operation codes from 88-level values)
# ---------------------------------------------------------------------------

OP_OPEN = "O"
OP_CLOSE = "C"
OP_READ = "R"
OP_READ_KEY = "K"
OP_WRITE = "W"

RC_OK = "00"
RC_EOF = "10"
RC_ERROR = "12"


# ---------------------------------------------------------------------------
# Data structures (from copybooks used by CBSTM03B)
# ---------------------------------------------------------------------------

@dataclass
class TrnxRecord:
    """Transaction record layout (COSTM01 — keyed by card+tran-id)."""
    trnx_card_num: str = ""         # PIC X(16)
    trnx_id: str = ""               # PIC X(16)
    trnx_type_cd: str = ""          # PIC X(02)
    trnx_cat_cd: str = ""           # PIC 9(04)
    trnx_source: str = ""           # PIC X(10)
    trnx_desc: str = ""             # PIC X(100)
    trnx_amt: float = 0.0           # PIC S9(09)V99
    trnx_merchant_id: str = ""      # PIC 9(09)
    trnx_merchant_name: str = ""    # PIC X(50)
    trnx_merchant_city: str = ""    # PIC X(50)
    trnx_merchant_zip: str = ""     # PIC X(10)
    trnx_orig_ts: str = ""          # PIC X(26)
    trnx_proc_ts: str = ""          # PIC X(26)


@dataclass
class XrefRecord:
    """Card cross-reference record (CVACT03Y - 50 bytes)."""
    xref_card_num: str = ""   # PIC X(16)
    xref_cust_id: str = ""    # PIC 9(09)
    xref_acct_id: str = ""    # PIC 9(11)


@dataclass
class CustomerRecord:
    """Customer record layout (CUSTREC - 500 bytes)."""
    cust_id: str = ""                   # PIC 9(09)
    cust_first_name: str = ""           # PIC X(25)
    cust_middle_name: str = ""          # PIC X(25)
    cust_last_name: str = ""            # PIC X(25)
    cust_addr_line_1: str = ""          # PIC X(50)
    cust_addr_line_2: str = ""          # PIC X(50)
    cust_addr_line_3: str = ""          # PIC X(50)
    cust_addr_state_cd: str = ""        # PIC X(02)
    cust_addr_country_cd: str = ""      # PIC X(03)
    cust_addr_zip: str = ""             # PIC X(10)
    cust_phone_num_1: str = ""          # PIC X(15)
    cust_phone_num_2: str = ""          # PIC X(15)
    cust_ssn: str = ""                  # PIC 9(09)
    cust_govt_issued_id: str = ""       # PIC X(20)
    cust_dob_yyyymmdd: str = ""         # PIC X(10)
    cust_eft_account_id: str = ""       # PIC X(10)
    cust_pri_card_holder_ind: str = ""  # PIC X(01)
    cust_fico_credit_score: str = ""    # PIC 9(03)


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


# ---------------------------------------------------------------------------
# Repository interfaces
# ---------------------------------------------------------------------------

class TrnxFileRepository:
    """Abstract interface for sequential transaction file access."""

    def get_all_records(self) -> List[TrnxRecord]:
        """Return all transaction records in key order."""
        raise NotImplementedError


class XrefFileRepository:
    """Abstract interface for sequential cross-reference file access."""

    def get_all_records(self) -> List[XrefRecord]:
        """Return all xref records in key order."""
        raise NotImplementedError


class CustomerFileRepository:
    """Abstract interface for keyed customer file access."""

    def read_by_key(self, cust_id: str) -> Optional[CustomerRecord]:
        """Read a customer record by customer ID."""
        raise NotImplementedError


class AccountFileRepository:
    """Abstract interface for keyed account file access."""

    def read_by_key(self, acct_id: str) -> Optional[AccountRecord]:
        """Read an account record by account ID."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# In-memory repositories for testing
# ---------------------------------------------------------------------------

class InMemoryTrnxFileRepository(TrnxFileRepository):
    """In-memory transaction file."""

    def __init__(self) -> None:
        self.records: List[TrnxRecord] = []

    def add_record(self, record: TrnxRecord) -> None:
        self.records.append(record)

    def get_all_records(self) -> List[TrnxRecord]:
        return list(self.records)


class InMemoryXrefFileRepository(XrefFileRepository):
    """In-memory cross-reference file."""

    def __init__(self) -> None:
        self.records: List[XrefRecord] = []

    def add_record(self, record: XrefRecord) -> None:
        self.records.append(record)

    def get_all_records(self) -> List[XrefRecord]:
        return list(self.records)


class InMemoryCustomerFileRepository(CustomerFileRepository):
    """In-memory customer file."""

    def __init__(self) -> None:
        self.records: Dict[str, CustomerRecord] = {}

    def add_record(self, record: CustomerRecord) -> None:
        self.records[record.cust_id] = record

    def read_by_key(self, cust_id: str) -> Optional[CustomerRecord]:
        return self.records.get(cust_id)


class InMemoryAccountFileRepository(AccountFileRepository):
    """In-memory account file."""

    def __init__(self) -> None:
        self.records: Dict[str, AccountRecord] = {}

    def add_record(self, record: AccountRecord) -> None:
        self.records[record.acct_id] = record

    def read_by_key(self, acct_id: str) -> Optional[AccountRecord]:
        return self.records.get(acct_id)


# ---------------------------------------------------------------------------
# StatementFileHandler — Python equivalent of the CBSTM03B subroutine
# ---------------------------------------------------------------------------

@dataclass
class FileOperationResult:
    """Result of a file operation, matching WS-M03B-AREA return fields."""
    return_code: str = RC_OK
    data: object = None


class StatementFileHandler:
    """
    File I/O handler for the account statement program.

    This class replaces the CBSTM03B COBOL subroutine. Each method
    corresponds to one of the file operations dispatched by the
    EVALUATE LK-M03B-DD block in the original program.

    Usage:
        handler = StatementFileHandler(trnx_repo, xref_repo, cust_repo, acct_repo)
        handler.open_all()
        xref = handler.read_next_xref()
        cust = handler.read_customer_by_key(cust_id)
        acct = handler.read_account_by_key(acct_id)
        trnx = handler.read_next_trnx()
        handler.close_all()
    """

    def __init__(
        self,
        trnx_repo: TrnxFileRepository,
        xref_repo: XrefFileRepository,
        cust_repo: CustomerFileRepository,
        acct_repo: AccountFileRepository,
    ) -> None:
        self._trnx_repo = trnx_repo
        self._xref_repo = xref_repo
        self._cust_repo = cust_repo
        self._acct_repo = acct_repo

        self._trnx_iter: Optional[Iterator[TrnxRecord]] = None
        self._xref_iter: Optional[Iterator[XrefRecord]] = None
        self._is_open = False

    def open_all(self) -> None:
        """
        Open all files for reading.

        Corresponds to the series of CALL 'CBSTM03B' with M03B-OPEN
        for TRNXFILE, XREFFILE, CUSTFILE, and ACCTFILE.
        """
        self._trnx_iter = iter(self._trnx_repo.get_all_records())
        self._xref_iter = iter(self._xref_repo.get_all_records())
        self._is_open = True

    def close_all(self) -> None:
        """
        Close all files.

        Corresponds to the CALL 'CBSTM03B' with M03B-CLOSE operations.
        """
        self._trnx_iter = None
        self._xref_iter = None
        self._is_open = False

    def read_next_trnx(self) -> FileOperationResult:
        """
        Read the next transaction record sequentially.

        Corresponds to CALL 'CBSTM03B' with DD='TRNXFILE', OPER='R'.
        Returns RC_OK with the record, or RC_EOF when exhausted.
        """
        if self._trnx_iter is None:
            return FileOperationResult(return_code=RC_ERROR)
        try:
            record = next(self._trnx_iter)
            return FileOperationResult(return_code=RC_OK, data=record)
        except StopIteration:
            return FileOperationResult(return_code=RC_EOF)

    def read_next_xref(self) -> FileOperationResult:
        """
        Read the next cross-reference record sequentially.

        Corresponds to CALL 'CBSTM03B' with DD='XREFFILE', OPER='R'.
        Returns RC_OK with the record, or RC_EOF when exhausted.
        """
        if self._xref_iter is None:
            return FileOperationResult(return_code=RC_ERROR)
        try:
            record = next(self._xref_iter)
            return FileOperationResult(return_code=RC_OK, data=record)
        except StopIteration:
            return FileOperationResult(return_code=RC_EOF)

    def read_customer_by_key(self, cust_id: str) -> FileOperationResult:
        """
        Read a customer record by key.

        Corresponds to CALL 'CBSTM03B' with DD='CUSTFILE', OPER='K'.
        """
        record = self._cust_repo.read_by_key(cust_id)
        if record is None:
            return FileOperationResult(return_code=RC_ERROR)
        return FileOperationResult(return_code=RC_OK, data=record)

    def read_account_by_key(self, acct_id: str) -> FileOperationResult:
        """
        Read an account record by key.

        Corresponds to CALL 'CBSTM03B' with DD='ACCTFILE', OPER='K'.
        """
        record = self._acct_repo.read_by_key(acct_id)
        if record is None:
            return FileOperationResult(return_code=RC_ERROR)
        return FileOperationResult(return_code=RC_OK, data=record)
