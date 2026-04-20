"""
CBTRN01C - Post Daily Transactions (Simple) — Python Translation

Translated from the COBOL batch program CBTRN01C.CBL in the AWS CardDemo
mainframe modernization project.  This module implements the business logic
for reading daily transaction records and verifying them against the card
cross-reference and account master files.

Original: Batch COBOL program that reads a sequential daily-transaction file,
looks up each card in the cross-reference, and reads the associated account.
This is the *simple* posting program — it verifies cards and accounts but
does not write to a transaction master or update balances (see CBTRN02C for
the advanced version).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROGRAM_NAME = "CBTRN01C"


# ---------------------------------------------------------------------------
# Data structures (from copybooks)
# ---------------------------------------------------------------------------

@dataclass
class DailyTransactionRecord:
    """Daily transaction record (CVTRA06Y — 350 bytes)."""
    tran_id: str = ""                   # DALYTRAN-ID           PIC X(16)
    tran_type_cd: str = ""              # DALYTRAN-TYPE-CD      PIC X(02)
    tran_cat_cd: str = ""               # DALYTRAN-CAT-CD       PIC 9(04)
    tran_source: str = ""               # DALYTRAN-SOURCE       PIC X(10)
    tran_desc: str = ""                 # DALYTRAN-DESC         PIC X(100)
    tran_amt: float = 0.0              # DALYTRAN-AMT          PIC S9(09)V99
    tran_merchant_id: str = ""          # DALYTRAN-MERCHANT-ID  PIC 9(09)
    tran_merchant_name: str = ""        # DALYTRAN-MERCHANT-NAME PIC X(50)
    tran_merchant_city: str = ""        # DALYTRAN-MERCHANT-CITY PIC X(50)
    tran_merchant_zip: str = ""         # DALYTRAN-MERCHANT-ZIP PIC X(10)
    tran_card_num: str = ""             # DALYTRAN-CARD-NUM     PIC X(16)
    tran_orig_ts: str = ""              # DALYTRAN-ORIG-TS      PIC X(26)
    tran_proc_ts: str = ""              # DALYTRAN-PROC-TS      PIC X(26)


@dataclass
class CardXrefRecord:
    """Card cross-reference record (CVACT03Y — 50 bytes)."""
    card_num: str = ""      # XREF-CARD-NUM  PIC X(16)
    cust_id: str = ""       # XREF-CUST-ID   PIC 9(09)
    acct_id: str = ""       # XREF-ACCT-ID   PIC 9(11)


@dataclass
class AccountRecord:
    """Account record (CVACT01Y — 300 bytes)."""
    acct_id: str = ""                   # ACCT-ID               PIC 9(11)
    active_status: str = ""             # ACCT-ACTIVE-STATUS    PIC X(01)
    curr_bal: float = 0.0              # ACCT-CURR-BAL         PIC S9(10)V99
    credit_limit: float = 0.0         # ACCT-CREDIT-LIMIT     PIC S9(10)V99
    cash_credit_limit: float = 0.0    # ACCT-CASH-CREDIT-LIMIT PIC S9(10)V99
    open_date: str = ""                 # ACCT-OPEN-DATE        PIC X(10)
    expiration_date: str = ""           # ACCT-EXPIRAION-DATE   PIC X(10)
    reissue_date: str = ""              # ACCT-REISSUE-DATE     PIC X(10)
    curr_cyc_credit: float = 0.0       # ACCT-CURR-CYC-CREDIT  PIC S9(10)V99
    curr_cyc_debit: float = 0.0        # ACCT-CURR-CYC-DEBIT   PIC S9(10)V99
    addr_zip: str = ""                  # ACCT-ADDR-ZIP         PIC X(10)
    group_id: str = ""                  # ACCT-GROUP-ID         PIC X(10)


@dataclass
class TransactionPostResult:
    """Result for a single daily transaction processing attempt."""
    tran_id: str = ""
    card_num: str = ""
    xref_found: bool = False
    acct_id: str = ""
    acct_found: bool = False
    error_message: str = ""


@dataclass
class BatchResult:
    """Overall result of the CBTRN01C batch run."""
    transactions_read: int = 0
    xref_found: int = 0
    xref_not_found: int = 0
    accounts_found: int = 0
    accounts_not_found: int = 0
    results: List[TransactionPostResult] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Repository interfaces (abstract VSAM file I/O)
# ---------------------------------------------------------------------------

class CardXrefRepository:
    """Abstract interface for card cross-reference lookups."""

    def lookup_by_card_num(self, card_num: str) -> Optional[CardXrefRecord]:
        """
        Look up a cross-reference record by card number.

        Corresponds to READ XREF-FILE KEY IS FD-XREF-CARD-NUM.
        Returns None if card number not found (INVALID KEY).
        """
        raise NotImplementedError


class AccountRepository:
    """Abstract interface for account data access."""

    def read_account(self, acct_id: str) -> Optional[AccountRecord]:
        """
        Read an account record by account ID.

        Corresponds to READ ACCOUNT-FILE KEY IS FD-ACCT-ID.
        Returns None if account not found (INVALID KEY).
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# In-memory repository implementations for testing
# ---------------------------------------------------------------------------

class InMemoryCardXrefRepository(CardXrefRepository):
    """In-memory card cross-reference repository."""

    def __init__(self) -> None:
        self.records: dict[str, CardXrefRecord] = {}

    def add(self, record: CardXrefRecord) -> None:
        """Add a cross-reference record."""
        self.records[record.card_num] = record

    def lookup_by_card_num(self, card_num: str) -> Optional[CardXrefRecord]:
        return self.records.get(card_num)


class InMemoryAccountRepository(AccountRepository):
    """In-memory account repository."""

    def __init__(self) -> None:
        self.accounts: dict[str, AccountRecord] = {}

    def add(self, record: AccountRecord) -> None:
        """Add an account record."""
        self.accounts[record.acct_id] = record

    def read_account(self, acct_id: str) -> Optional[AccountRecord]:
        return self.accounts.get(acct_id)


# ---------------------------------------------------------------------------
# Core batch processing logic
# ---------------------------------------------------------------------------

def process_single_transaction(
    daily_tran: DailyTransactionRecord,
    xref_repo: CardXrefRepository,
    acct_repo: AccountRepository,
) -> TransactionPostResult:
    """
    Process a single daily transaction record.

    Mirrors the main loop body of CBTRN01C:
    1. Look up the card number in the cross-reference file.
    2. If found, read the account using the xref account ID.
    3. Return the result indicating what was found/not found.

    Args:
        daily_tran: The daily transaction record to process.
        xref_repo: Repository for card cross-reference lookups.
        acct_repo: Repository for account lookups.

    Returns:
        A TransactionPostResult with the outcome.
    """
    result = TransactionPostResult(
        tran_id=daily_tran.tran_id,
        card_num=daily_tran.tran_card_num,
    )

    # 2000-LOOKUP-XREF
    xref = xref_repo.lookup_by_card_num(daily_tran.tran_card_num)
    if xref is None:
        result.error_message = (
            f"CARD NUMBER {daily_tran.tran_card_num} COULD NOT BE VERIFIED. "
            f"SKIPPING TRANSACTION ID-{daily_tran.tran_id}"
        )
        logger.warning(result.error_message)
        return result

    result.xref_found = True
    result.acct_id = xref.acct_id
    logger.info(
        "SUCCESSFUL READ OF XREF - CARD NUMBER: %s ACCOUNT ID: %s CUSTOMER ID: %s",
        xref.card_num, xref.acct_id, xref.cust_id,
    )

    # 3000-READ-ACCOUNT
    account = acct_repo.read_account(xref.acct_id)
    if account is None:
        result.error_message = f"ACCOUNT {xref.acct_id} NOT FOUND"
        logger.warning(result.error_message)
        return result

    result.acct_found = True
    logger.info("SUCCESSFUL READ OF ACCOUNT FILE for %s", xref.acct_id)

    return result


def run(
    daily_transactions: List[DailyTransactionRecord],
    xref_repo: CardXrefRepository,
    acct_repo: AccountRepository,
) -> BatchResult:
    """
    Main entry point for the CBTRN01C batch process.

    Iterates over all daily transaction records and processes each one.
    This corresponds to the MAIN-PARA PERFORM UNTIL loop.

    Args:
        daily_transactions: List of daily transaction records to process.
        xref_repo: Repository for card cross-reference lookups.
        acct_repo: Repository for account lookups.

    Returns:
        A BatchResult summarizing the entire batch run.
    """
    logger.info("START OF EXECUTION OF PROGRAM CBTRN01C")

    batch_result = BatchResult()

    for daily_tran in daily_transactions:
        batch_result.transactions_read += 1

        result = process_single_transaction(daily_tran, xref_repo, acct_repo)
        batch_result.results.append(result)

        if result.xref_found:
            batch_result.xref_found += 1
        else:
            batch_result.xref_not_found += 1

        if result.acct_found:
            batch_result.accounts_found += 1
        elif result.xref_found:
            batch_result.accounts_not_found += 1

    logger.info("END OF EXECUTION OF PROGRAM CBTRN01C")

    return batch_result
