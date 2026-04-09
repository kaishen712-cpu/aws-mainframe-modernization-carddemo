"""
CBACT01C - Read Accounts & Write Output (Python Translation)

Translated from the COBOL program CBACT01C.CBL in the AWS CardDemo
mainframe modernization project. This module reads account records and
produces multiple formatted output representations including a standard
account record, an array record with balance repetitions, and variable-
length records.

Original: Batch COBOL program reading a VSAM KSDS account file
sequentially, reformatting dates via the COBDATFT assembler routine,
and writing to three output files (OUT-FILE, ARRY-FILE, VBRC-FILE).

The COBDATFT assembler call is replaced with Python datetime formatting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROGRAM_NAME = "CBACT01C"


# ---------------------------------------------------------------------------
# Data structures (from copybook CVACT01Y — account entity, RECLN 300)
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
class OutputAccountRecord:
    """
    Reformatted output account record (from OUT-FILE FD).

    Corresponds to the OUT-ACCT-REC structure in the COBOL program.
    """
    acct_id: str = ""                       # PIC 9(11)
    acct_active_status: str = ""            # PIC X(01)
    acct_curr_bal: float = 0.0              # PIC S9(10)V99
    acct_credit_limit: float = 0.0          # PIC S9(10)V99
    acct_cash_credit_limit: float = 0.0     # PIC S9(10)V99
    acct_open_date: str = ""                # PIC X(10)
    acct_expiration_date: str = ""          # PIC X(10)
    acct_reissue_date: str = ""             # PIC X(10) — reformatted by date routine
    acct_curr_cyc_credit: float = 0.0       # PIC S9(10)V99
    acct_curr_cyc_debit: float = 0.0        # PIC S9(10)V99 COMP-3
    acct_group_id: str = ""                 # PIC X(10)


@dataclass
class ArrayAccountRecord:
    """
    Array output record (from ARRY-FILE FD).

    Each entry has 5 occurrences of (balance, debit) pairs.
    """
    acct_id: str = ""
    balances: List[float] = field(default_factory=lambda: [0.0] * 5)
    debits: List[float] = field(default_factory=lambda: [0.0] * 5)


@dataclass
class VbrcRecord1:
    """Variable-length record type 1: ID + active status (12 bytes)."""
    acct_id: str = ""
    acct_active_status: str = ""


@dataclass
class VbrcRecord2:
    """Variable-length record type 2: ID + balance + limit + reissue year (39 bytes)."""
    acct_id: str = ""
    acct_curr_bal: float = 0.0
    acct_credit_limit: float = 0.0
    acct_reissue_yyyy: str = ""


# ---------------------------------------------------------------------------
# Repository interface
# ---------------------------------------------------------------------------

class AccountRepository:
    """
    Abstract interface for account data access.

    In the original COBOL program this is a sequential read of a VSAM
    KSDS file. Concrete implementations can use any data source.
    """

    def get_all_accounts(self) -> List[AccountRecord]:
        """Return all account records in sequential order."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# In-memory repository for testing
# ---------------------------------------------------------------------------

class InMemoryAccountRepository(AccountRepository):
    """Simple in-memory implementation backed by a list."""

    def __init__(self) -> None:
        self.accounts: List[AccountRecord] = []

    def add_account(self, record: AccountRecord) -> None:
        """Add an account record."""
        self.accounts.append(record)

    def get_all_accounts(self) -> List[AccountRecord]:
        return list(self.accounts)


# ---------------------------------------------------------------------------
# Date formatting (replaces COBDATFT assembler call)
# ---------------------------------------------------------------------------

def format_date_cobdatft(
    input_date: str,
    input_type: str = "2",
    output_type: str = "2",
) -> str:
    """
    Reformat a date string, replacing the COBDATFT assembler routine.

    The original COBOL program calls COBDATFT with CODATECN-REC to
    convert dates between formats:
      Type "1" = YYYYMMDD
      Type "2" = YYYY-MM-DD

    Args:
        input_date: The input date string.
        input_type: "1" for YYYYMMDD, "2" for YYYY-MM-DD.
        output_type: "1" for YYYY-MM-DD output, "2" for YYYYMMDD output.

    Returns:
        The reformatted date string, or the original on parse failure.
    """
    try:
        if input_type == "1":
            dt = datetime.strptime(input_date[:8], "%Y%m%d")
        else:
            dt = datetime.strptime(input_date[:10], "%Y-%m-%d")

        if output_type == "1":
            return dt.strftime("%Y-%m-%d")
        else:
            return dt.strftime("%Y%m%d")
    except (ValueError, IndexError):
        return input_date


# ---------------------------------------------------------------------------
# Record transformation functions
# ---------------------------------------------------------------------------

def build_output_account_record(acct: AccountRecord) -> OutputAccountRecord:
    """
    Build an OutputAccountRecord from an AccountRecord.

    Corresponds to 1300-POPUL-ACCT-RECORD in the COBOL program.
    Reformats the reissue date via the date formatting routine.
    If the cycle debit is zero, it defaults to 2525.00 (matching
    the COBOL business rule).
    """
    reissue_date_formatted = format_date_cobdatft(
        acct.acct_reissue_date,
        input_type="2",
        output_type="2",
    )

    cyc_debit = acct.acct_curr_cyc_debit
    if cyc_debit == 0.0:
        cyc_debit = 2525.00

    return OutputAccountRecord(
        acct_id=acct.acct_id,
        acct_active_status=acct.acct_active_status,
        acct_curr_bal=acct.acct_curr_bal,
        acct_credit_limit=acct.acct_credit_limit,
        acct_cash_credit_limit=acct.acct_cash_credit_limit,
        acct_open_date=acct.acct_open_date,
        acct_expiration_date=acct.acct_expiration_date,
        acct_reissue_date=reissue_date_formatted,
        acct_curr_cyc_credit=acct.acct_curr_cyc_credit,
        acct_curr_cyc_debit=cyc_debit,
        acct_group_id=acct.acct_group_id,
    )


def build_array_record(acct: AccountRecord) -> ArrayAccountRecord:
    """
    Build an ArrayAccountRecord from an AccountRecord.

    Corresponds to 1400-POPUL-ARRAY-RECORD in the COBOL program.
    Populates 3 of 5 balance/debit slots with specific values.
    """
    rec = ArrayAccountRecord(acct_id=acct.acct_id)
    rec.balances[0] = acct.acct_curr_bal
    rec.debits[0] = 1005.00
    rec.balances[1] = acct.acct_curr_bal
    rec.debits[1] = 1525.00
    rec.balances[2] = -1025.00
    rec.debits[2] = -2500.00
    return rec


def build_vbrc_records(
    acct: AccountRecord,
) -> tuple[VbrcRecord1, VbrcRecord2]:
    """
    Build variable-length record pair from an AccountRecord.

    Corresponds to 1500-POPUL-VBRC-RECORD in the COBOL program.
    """
    reissue_yyyy = acct.acct_reissue_date[:4] if acct.acct_reissue_date else ""

    vb1 = VbrcRecord1(
        acct_id=acct.acct_id,
        acct_active_status=acct.acct_active_status,
    )
    vb2 = VbrcRecord2(
        acct_id=acct.acct_id,
        acct_curr_bal=acct.acct_curr_bal,
        acct_credit_limit=acct.acct_credit_limit,
        acct_reissue_yyyy=reissue_yyyy,
    )
    return vb1, vb2


# ---------------------------------------------------------------------------
# Display formatting
# ---------------------------------------------------------------------------

def format_account_display(acct: AccountRecord) -> List[str]:
    """
    Format an account record for display output.

    Corresponds to 1100-DISPLAY-ACCT-RECORD in the COBOL program.
    """
    return [
        f"ACCT-ID                 :{acct.acct_id}",
        f"ACCT-ACTIVE-STATUS      :{acct.acct_active_status}",
        f"ACCT-CURR-BAL           :{acct.acct_curr_bal:013.2f}",
        f"ACCT-CREDIT-LIMIT       :{acct.acct_credit_limit:013.2f}",
        f"ACCT-CASH-CREDIT-LIMIT  :{acct.acct_cash_credit_limit:013.2f}",
        f"ACCT-OPEN-DATE          :{acct.acct_open_date}",
        f"ACCT-EXPIRAION-DATE     :{acct.acct_expiration_date}",
        f"ACCT-REISSUE-DATE       :{acct.acct_reissue_date}",
        f"ACCT-CURR-CYC-CREDIT    :{acct.acct_curr_cyc_credit:013.2f}",
        f"ACCT-CURR-CYC-DEBIT     :{acct.acct_curr_cyc_debit:013.2f}",
        f"ACCT-GROUP-ID           :{acct.acct_group_id}",
        "-" * 49,
    ]


# ---------------------------------------------------------------------------
# Main batch processing
# ---------------------------------------------------------------------------

@dataclass
class BatchResult:
    """Results from processing all accounts."""
    display_lines: List[str] = field(default_factory=list)
    output_records: List[OutputAccountRecord] = field(default_factory=list)
    array_records: List[ArrayAccountRecord] = field(default_factory=list)
    vbrc_records_1: List[VbrcRecord1] = field(default_factory=list)
    vbrc_records_2: List[VbrcRecord2] = field(default_factory=list)


def process_accounts(repo: AccountRepository) -> BatchResult:
    """
    Read all account records and produce formatted outputs.

    This is the main entry point corresponding to the COBOL program's
    PROCEDURE DIVISION. For each account record it:
    1. Formats display lines (1100-DISPLAY-ACCT-RECORD)
    2. Builds reformatted output records (1300-POPUL-ACCT-RECORD)
    3. Builds array records (1400-POPUL-ARRAY-RECORD)
    4. Builds variable-length record pairs (1500-POPUL-VBRC-RECORD)

    Args:
        repo: An AccountRepository providing account records.

    Returns:
        A BatchResult containing all output collections.
    """
    result = BatchResult()
    result.display_lines.append(f"START OF EXECUTION OF PROGRAM {PROGRAM_NAME}")

    accounts = repo.get_all_accounts()
    for acct in accounts:
        result.display_lines.extend(format_account_display(acct))
        result.output_records.append(build_output_account_record(acct))
        result.array_records.append(build_array_record(acct))
        vb1, vb2 = build_vbrc_records(acct)
        result.vbrc_records_1.append(vb1)
        result.vbrc_records_2.append(vb2)

    result.display_lines.append(f"END OF EXECUTION OF PROGRAM {PROGRAM_NAME}")
    return result
