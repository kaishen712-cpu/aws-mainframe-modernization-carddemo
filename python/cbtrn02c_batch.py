"""
CBTRN02C (Batch) - Post Daily Transactions (Advanced) — Python Translation

Translated from the COBOL batch program CBTRN02C.CBL in the AWS CardDemo
mainframe modernization project.  This module implements the business logic
for reading daily transactions, validating them, posting valid ones to the
main transaction file, updating account and category balances, and writing
rejected transactions to a rejects file.

Original: Batch COBOL program that reads a sequential daily-transaction file,
validates each record (card xref, account lookup, credit-limit check,
expiration-date check), posts valid transactions, and rejects invalid ones.

NOTE: There is also an *online* COBOL program named COTRN02C (a CICS program
for adding individual transactions via a screen).  This module translates the
*batch* program CBTRN02C which processes files in bulk.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROGRAM_NAME = "CBTRN02C"

# Validation fail reason codes (from COBOL WS-VALIDATION-FAIL-REASON)
REASON_INVALID_CARD = 100
REASON_ACCOUNT_NOT_FOUND = 101
REASON_OVERLIMIT = 102
REASON_EXPIRED = 103

REASON_DESCRIPTIONS = {
    REASON_INVALID_CARD: "INVALID CARD NUMBER FOUND",
    REASON_ACCOUNT_NOT_FOUND: "ACCOUNT RECORD NOT FOUND",
    REASON_OVERLIMIT: "OVERLIMIT TRANSACTION",
    REASON_EXPIRED: "TRANSACTION RECEIVED AFTER ACCT EXPIRATION",
}


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
class TransactionRecord:
    """Transaction record (CVTRA05Y — 350 bytes)."""
    tran_id: str = ""                   # TRAN-ID               PIC X(16)
    tran_type_cd: str = ""              # TRAN-TYPE-CD          PIC X(02)
    tran_cat_cd: str = ""               # TRAN-CAT-CD           PIC 9(04)
    tran_source: str = ""               # TRAN-SOURCE           PIC X(10)
    tran_desc: str = ""                 # TRAN-DESC             PIC X(100)
    tran_amt: float = 0.0              # TRAN-AMT              PIC S9(09)V99
    tran_merchant_id: str = ""          # TRAN-MERCHANT-ID      PIC 9(09)
    tran_merchant_name: str = ""        # TRAN-MERCHANT-NAME    PIC X(50)
    tran_merchant_city: str = ""        # TRAN-MERCHANT-CITY    PIC X(50)
    tran_merchant_zip: str = ""         # TRAN-MERCHANT-ZIP     PIC X(10)
    tran_card_num: str = ""             # TRAN-CARD-NUM         PIC X(16)
    tran_orig_ts: str = ""              # TRAN-ORIG-TS          PIC X(26)
    tran_proc_ts: str = ""              # TRAN-PROC-TS          PIC X(26)


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
class TranCatBalRecord:
    """Transaction category balance record (CVTRA01Y — 50 bytes)."""
    acct_id: str = ""       # TRANCAT-ACCT-ID   PIC 9(11)
    type_cd: str = ""       # TRANCAT-TYPE-CD   PIC X(02)
    cat_cd: str = ""        # TRANCAT-CD        PIC 9(04)
    balance: float = 0.0   # TRAN-CAT-BAL      PIC S9(09)V99


@dataclass
class RejectedTransaction:
    """A rejected daily transaction with its rejection reason."""
    daily_tran: DailyTransactionRecord
    fail_reason: int = 0
    fail_reason_desc: str = ""


@dataclass
class BatchResult:
    """Overall result of the CBTRN02C batch run."""
    transaction_count: int = 0
    reject_count: int = 0
    posted_transactions: List[TransactionRecord] = field(default_factory=list)
    rejected_transactions: List[RejectedTransaction] = field(default_factory=list)
    return_code: int = 0


# ---------------------------------------------------------------------------
# Repository interfaces (abstract VSAM file I/O)
# ---------------------------------------------------------------------------

class CardXrefRepository:
    """Abstract interface for card cross-reference lookups."""

    def lookup_by_card_num(self, card_num: str) -> Optional[CardXrefRecord]:
        """Read xref record by card number. Returns None if not found."""
        raise NotImplementedError


class AccountRepository:
    """Abstract interface for account data access."""

    def read_account(self, acct_id: str) -> Optional[AccountRecord]:
        """Read account by ID. Returns None if not found."""
        raise NotImplementedError

    def update_account(self, account: AccountRecord) -> bool:
        """Rewrite account record. Returns True on success."""
        raise NotImplementedError


class TransactionRepository:
    """Abstract interface for the main transaction file."""

    def write_transaction(self, record: TransactionRecord) -> bool:
        """Write a transaction record. Returns True on success."""
        raise NotImplementedError


class TranCatBalRepository:
    """Abstract interface for transaction category balance file."""

    def read_balance(
        self, acct_id: str, type_cd: str, cat_cd: str
    ) -> Optional[TranCatBalRecord]:
        """Read category balance by composite key. Returns None if not found."""
        raise NotImplementedError

    def write_balance(self, record: TranCatBalRecord) -> bool:
        """Write a new category balance record. Returns True on success."""
        raise NotImplementedError

    def update_balance(self, record: TranCatBalRecord) -> bool:
        """Rewrite an existing category balance record. Returns True on success."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# In-memory repository implementations for testing
# ---------------------------------------------------------------------------

class InMemoryCardXrefRepository(CardXrefRepository):
    """In-memory card cross-reference repository."""

    def __init__(self) -> None:
        self.records: dict[str, CardXrefRecord] = {}

    def add(self, record: CardXrefRecord) -> None:
        self.records[record.card_num] = record

    def lookup_by_card_num(self, card_num: str) -> Optional[CardXrefRecord]:
        return self.records.get(card_num)


class InMemoryAccountRepository(AccountRepository):
    """In-memory account repository."""

    def __init__(self) -> None:
        self.accounts: dict[str, AccountRecord] = {}

    def add(self, record: AccountRecord) -> None:
        self.accounts[record.acct_id] = record

    def read_account(self, acct_id: str) -> Optional[AccountRecord]:
        return self.accounts.get(acct_id)

    def update_account(self, account: AccountRecord) -> bool:
        if account.acct_id not in self.accounts:
            return False
        self.accounts[account.acct_id] = account
        return True


class InMemoryTransactionRepository(TransactionRepository):
    """In-memory transaction repository."""

    def __init__(self) -> None:
        self.transactions: List[TransactionRecord] = []

    def write_transaction(self, record: TransactionRecord) -> bool:
        self.transactions.append(record)
        return True


class InMemoryTranCatBalRepository(TranCatBalRepository):
    """In-memory transaction category balance repository."""

    def __init__(self) -> None:
        self.balances: dict[str, TranCatBalRecord] = {}

    def _make_key(self, acct_id: str, type_cd: str, cat_cd: str) -> str:
        return f"{acct_id}|{type_cd}|{cat_cd}"

    def add(self, record: TranCatBalRecord) -> None:
        key = self._make_key(record.acct_id, record.type_cd, record.cat_cd)
        self.balances[key] = record

    def read_balance(
        self, acct_id: str, type_cd: str, cat_cd: str
    ) -> Optional[TranCatBalRecord]:
        key = self._make_key(acct_id, type_cd, cat_cd)
        return self.balances.get(key)

    def write_balance(self, record: TranCatBalRecord) -> bool:
        key = self._make_key(record.acct_id, record.type_cd, record.cat_cd)
        self.balances[key] = record
        return True

    def update_balance(self, record: TranCatBalRecord) -> bool:
        key = self._make_key(record.acct_id, record.type_cd, record.cat_cd)
        if key not in self.balances:
            return False
        self.balances[key] = record
        return True


# ---------------------------------------------------------------------------
# Validation logic
# ---------------------------------------------------------------------------

def validate_transaction(
    daily_tran: DailyTransactionRecord,
    xref_repo: CardXrefRepository,
    acct_repo: AccountRepository,
) -> Tuple[int, str, Optional[CardXrefRecord], Optional[AccountRecord]]:
    """
    Validate a daily transaction record.

    Corresponds to 1500-VALIDATE-TRAN:
    1. Look up card in cross-reference (1500-A-LOOKUP-XREF)
    2. Look up account (1500-B-LOOKUP-ACCT)
    3. Check credit limit (overlimit check)
    4. Check expiration date

    Returns:
        Tuple of (fail_reason, fail_reason_desc, xref_record, account_record).
        fail_reason is 0 if validation passed.
    """
    # 1500-A-LOOKUP-XREF
    xref = xref_repo.lookup_by_card_num(daily_tran.tran_card_num)
    if xref is None:
        return (REASON_INVALID_CARD, REASON_DESCRIPTIONS[REASON_INVALID_CARD],
                None, None)

    # 1500-B-LOOKUP-ACCT
    account = acct_repo.read_account(xref.acct_id)
    if account is None:
        return (REASON_ACCOUNT_NOT_FOUND,
                REASON_DESCRIPTIONS[REASON_ACCOUNT_NOT_FOUND], xref, None)

    # Overlimit check:
    # COMPUTE WS-TEMP-BAL = ACCT-CURR-CYC-CREDIT
    #                      - ACCT-CURR-CYC-DEBIT
    #                      + DALYTRAN-AMT
    temp_bal = account.curr_cyc_credit - account.curr_cyc_debit + daily_tran.tran_amt
    if account.credit_limit < temp_bal:
        return (REASON_OVERLIMIT, REASON_DESCRIPTIONS[REASON_OVERLIMIT],
                xref, account)

    # Expiration check:
    # IF ACCT-EXPIRAION-DATE >= DALYTRAN-ORIG-TS (1:10) -> OK
    orig_date = daily_tran.tran_orig_ts[:10]
    if account.expiration_date < orig_date:
        return (REASON_EXPIRED, REASON_DESCRIPTIONS[REASON_EXPIRED],
                xref, account)

    return (0, "", xref, account)


# ---------------------------------------------------------------------------
# Posting logic
# ---------------------------------------------------------------------------

def _get_db2_format_timestamp() -> str:
    """
    Generate a DB2-format timestamp from the current date/time.

    Corresponds to Z-GET-DB2-FORMAT-TIMESTAMP.
    Format: YYYY-MM-DD-HH.MM.SS.mm0000
    """
    now = datetime.now()
    return now.strftime("%Y-%m-%d-%H.%M.%S.") + f"{now.microsecond // 10000:02d}0000"


def post_transaction(
    daily_tran: DailyTransactionRecord,
    xref: CardXrefRecord,
    account: AccountRecord,
    tran_repo: TransactionRepository,
    acct_repo: AccountRepository,
    tcatbal_repo: TranCatBalRepository,
    timestamp_fn: Optional[type] = None,
) -> TransactionRecord:
    """
    Post a validated daily transaction.

    Corresponds to 2000-POST-TRANSACTION:
    1. Copy daily tran fields to transaction record
    2. Generate processing timestamp
    3. Update transaction category balance (2700-UPDATE-TCATBAL)
    4. Update account balances (2800-UPDATE-ACCOUNT-REC)
    5. Write transaction to main file (2900-WRITE-TRANSACTION-FILE)

    Args:
        daily_tran: The validated daily transaction.
        xref: The cross-reference record for this card.
        account: The account record.
        tran_repo: Repository to write the posted transaction.
        acct_repo: Repository to update account balances.
        tcatbal_repo: Repository for category balance updates.
        timestamp_fn: Optional callable returning a timestamp string (for testing).

    Returns:
        The posted TransactionRecord.
    """
    # Build transaction record from daily transaction
    proc_ts = timestamp_fn() if timestamp_fn else _get_db2_format_timestamp()

    tran = TransactionRecord(
        tran_id=daily_tran.tran_id,
        tran_type_cd=daily_tran.tran_type_cd,
        tran_cat_cd=daily_tran.tran_cat_cd,
        tran_source=daily_tran.tran_source,
        tran_desc=daily_tran.tran_desc,
        tran_amt=daily_tran.tran_amt,
        tran_merchant_id=daily_tran.tran_merchant_id,
        tran_merchant_name=daily_tran.tran_merchant_name,
        tran_merchant_city=daily_tran.tran_merchant_city,
        tran_merchant_zip=daily_tran.tran_merchant_zip,
        tran_card_num=daily_tran.tran_card_num,
        tran_orig_ts=daily_tran.tran_orig_ts,
        tran_proc_ts=proc_ts,
    )

    # 2700-UPDATE-TCATBAL
    _update_tcatbal(xref.acct_id, daily_tran, tcatbal_repo)

    # 2800-UPDATE-ACCOUNT-REC
    _update_account(account, daily_tran.tran_amt, acct_repo)

    # 2900-WRITE-TRANSACTION-FILE
    tran_repo.write_transaction(tran)

    return tran


def _update_tcatbal(
    acct_id: str,
    daily_tran: DailyTransactionRecord,
    tcatbal_repo: TranCatBalRepository,
) -> None:
    """
    Update the transaction category balance.

    Corresponds to 2700-UPDATE-TCATBAL:
    - Read by composite key (acct_id + type_cd + cat_cd)
    - If found: add amount and REWRITE
    - If not found: create new record with the amount
    """
    existing = tcatbal_repo.read_balance(
        acct_id, daily_tran.tran_type_cd, daily_tran.tran_cat_cd
    )

    if existing is not None:
        # 2700-B-UPDATE-TCATBAL-REC
        existing.balance += daily_tran.tran_amt
        tcatbal_repo.update_balance(existing)
    else:
        # 2700-A-CREATE-TCATBAL-REC
        new_record = TranCatBalRecord(
            acct_id=acct_id,
            type_cd=daily_tran.tran_type_cd,
            cat_cd=daily_tran.tran_cat_cd,
            balance=daily_tran.tran_amt,
        )
        tcatbal_repo.write_balance(new_record)


def _update_account(
    account: AccountRecord,
    tran_amt: float,
    acct_repo: AccountRepository,
) -> None:
    """
    Update account balances after posting a transaction.

    Corresponds to 2800-UPDATE-ACCOUNT-REC:
    - Add transaction amount to current balance
    - If amount >= 0: add to cycle credit
    - If amount < 0: add to cycle debit
    - REWRITE the account record
    """
    account.curr_bal += tran_amt
    if tran_amt >= 0:
        account.curr_cyc_credit += tran_amt
    else:
        account.curr_cyc_debit += tran_amt
    acct_repo.update_account(account)


# ---------------------------------------------------------------------------
# Main batch entry point
# ---------------------------------------------------------------------------

def run(
    daily_transactions: List[DailyTransactionRecord],
    xref_repo: CardXrefRepository,
    acct_repo: AccountRepository,
    tran_repo: TransactionRepository,
    tcatbal_repo: TranCatBalRepository,
    timestamp_fn: Optional[type] = None,
) -> BatchResult:
    """
    Main entry point for the CBTRN02C batch process.

    Iterates over all daily transaction records, validates each, and either
    posts valid ones or records rejections.

    Args:
        daily_transactions: List of daily transaction records to process.
        xref_repo: Repository for card cross-reference lookups.
        acct_repo: Repository for account data (read and update).
        tran_repo: Repository for writing posted transactions.
        tcatbal_repo: Repository for category balance tracking.
        timestamp_fn: Optional callable returning a timestamp string (for testing).

    Returns:
        A BatchResult summarizing the entire batch run.
    """
    logger.info("START OF EXECUTION OF PROGRAM CBTRN02C")

    batch_result = BatchResult()

    for daily_tran in daily_transactions:
        batch_result.transaction_count += 1

        # 1500-VALIDATE-TRAN
        fail_reason, fail_desc, xref, account = validate_transaction(
            daily_tran, xref_repo, acct_repo
        )

        if fail_reason == 0 and xref is not None and account is not None:
            # 2000-POST-TRANSACTION
            posted = post_transaction(
                daily_tran, xref, account,
                tran_repo, acct_repo, tcatbal_repo,
                timestamp_fn,
            )
            batch_result.posted_transactions.append(posted)
        else:
            # 2500-WRITE-REJECT-REC
            batch_result.reject_count += 1
            rejected = RejectedTransaction(
                daily_tran=daily_tran,
                fail_reason=fail_reason,
                fail_reason_desc=fail_desc,
            )
            batch_result.rejected_transactions.append(rejected)

    # Set return code (4 if any rejects, 0 otherwise)
    if batch_result.reject_count > 0:
        batch_result.return_code = 4

    logger.info("TRANSACTIONS PROCESSED: %d", batch_result.transaction_count)
    logger.info("TRANSACTIONS REJECTED: %d", batch_result.reject_count)
    logger.info("END OF EXECUTION OF PROGRAM CBTRN02C")

    return batch_result
