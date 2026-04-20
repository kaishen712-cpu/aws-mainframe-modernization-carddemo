"""
CBACT04C - Interest Calculation — Python Translation

Translated from the COBOL batch program CBACT04C.CBL in the AWS CardDemo
mainframe modernization project.  This module implements the business logic
for calculating monthly interest charges on credit card account balances.

Original: Batch COBOL program that reads the transaction category balance file
sequentially (sorted by account), looks up interest rates from the disclosure
group file, computes monthly interest, creates interest transaction records,
and updates account balances.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROGRAM_NAME = "CBACT04C"

# Fixed values used when creating interest transaction records
INTEREST_TRAN_TYPE_CD = "01"
INTEREST_TRAN_CAT_CD = "0005"
INTEREST_TRAN_SOURCE = "System"
DEFAULT_GROUP_ID = "DEFAULT"


# ---------------------------------------------------------------------------
# Data structures (from copybooks)
# ---------------------------------------------------------------------------

@dataclass
class TranCatBalRecord:
    """Transaction category balance record (CVTRA01Y — 50 bytes)."""
    acct_id: str = ""       # TRANCAT-ACCT-ID   PIC 9(11)
    type_cd: str = ""       # TRANCAT-TYPE-CD   PIC X(02)
    cat_cd: str = ""        # TRANCAT-CD        PIC 9(04)
    balance: float = 0.0   # TRAN-CAT-BAL      PIC S9(09)V99


@dataclass
class CardXrefRecord:
    """Card cross-reference record (CVACT03Y — 50 bytes)."""
    card_num: str = ""      # XREF-CARD-NUM  PIC X(16)
    cust_id: str = ""       # XREF-CUST-ID   PIC 9(09)
    acct_id: str = ""       # XREF-ACCT-ID   PIC 9(11)


@dataclass
class DisclosureGroupRecord:
    """Disclosure group record (CVTRA02Y — 50 bytes)."""
    acct_group_id: str = ""   # DIS-ACCT-GROUP-ID  PIC X(10)
    tran_type_cd: str = ""    # DIS-TRAN-TYPE-CD   PIC X(02)
    tran_cat_cd: str = ""     # DIS-TRAN-CAT-CD    PIC 9(04)
    int_rate: float = 0.0    # DIS-INT-RATE        PIC S9(04)V99


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
class InterestResult:
    """Result of interest calculation for a single category balance."""
    acct_id: str = ""
    type_cd: str = ""
    cat_cd: str = ""
    balance: float = 0.0
    int_rate: float = 0.0
    monthly_interest: float = 0.0
    used_default_rate: bool = False


@dataclass
class AccountInterestSummary:
    """Summary of interest calculations for a single account."""
    acct_id: str = ""
    total_interest: float = 0.0
    category_results: List[InterestResult] = field(default_factory=list)
    transactions_created: List[TransactionRecord] = field(default_factory=list)


@dataclass
class BatchResult:
    """Overall result of the CBACT04C batch run."""
    records_read: int = 0
    accounts_processed: int = 0
    interest_transactions_created: int = 0
    total_interest_charged: float = 0.0
    account_summaries: List[AccountInterestSummary] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Repository interfaces (abstract VSAM file I/O)
# ---------------------------------------------------------------------------

class CardXrefRepository:
    """Abstract interface for card cross-reference lookups."""

    def lookup_by_acct_id(self, acct_id: str) -> Optional[CardXrefRecord]:
        """
        Look up a cross-reference record by account ID (alternate key).

        Corresponds to READ XREF-FILE KEY IS FD-XREF-ACCT-ID.
        Returns None if not found.
        """
        raise NotImplementedError


class AccountRepository:
    """Abstract interface for account data access."""

    def read_account(self, acct_id: str) -> Optional[AccountRecord]:
        """Read an account record by account ID."""
        raise NotImplementedError

    def update_account(self, account: AccountRecord) -> bool:
        """Rewrite an account record. Returns True on success."""
        raise NotImplementedError


class DisclosureGroupRepository:
    """Abstract interface for disclosure group (interest rate) lookups."""

    def read_rate(
        self, group_id: str, type_cd: str, cat_cd: str
    ) -> Optional[DisclosureGroupRecord]:
        """
        Look up the interest rate for a group/type/category combination.

        Returns None if the record is not found.
        """
        raise NotImplementedError


class TransactionRepository:
    """Abstract interface for the main transaction file."""

    def write_transaction(self, record: TransactionRecord) -> bool:
        """Write a transaction record. Returns True on success."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# In-memory repository implementations for testing
# ---------------------------------------------------------------------------

class InMemoryCardXrefRepository(CardXrefRepository):
    """In-memory card cross-reference repository."""

    def __init__(self) -> None:
        self.by_acct: dict[str, CardXrefRecord] = {}
        self.by_card: dict[str, CardXrefRecord] = {}

    def add(self, record: CardXrefRecord) -> None:
        self.by_acct[record.acct_id] = record
        self.by_card[record.card_num] = record

    def lookup_by_acct_id(self, acct_id: str) -> Optional[CardXrefRecord]:
        return self.by_acct.get(acct_id)


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


class InMemoryDisclosureGroupRepository(DisclosureGroupRepository):
    """In-memory disclosure group repository."""

    def __init__(self) -> None:
        self.rates: dict[str, DisclosureGroupRecord] = {}

    def _make_key(self, group_id: str, type_cd: str, cat_cd: str) -> str:
        return f"{group_id}|{type_cd}|{cat_cd}"

    def add(self, record: DisclosureGroupRecord) -> None:
        key = self._make_key(
            record.acct_group_id, record.tran_type_cd, record.tran_cat_cd
        )
        self.rates[key] = record

    def read_rate(
        self, group_id: str, type_cd: str, cat_cd: str
    ) -> Optional[DisclosureGroupRecord]:
        key = self._make_key(group_id, type_cd, cat_cd)
        return self.rates.get(key)


class InMemoryTransactionRepository(TransactionRepository):
    """In-memory transaction repository."""

    def __init__(self) -> None:
        self.transactions: List[TransactionRecord] = []

    def write_transaction(self, record: TransactionRecord) -> bool:
        self.transactions.append(record)
        return True


# ---------------------------------------------------------------------------
# Timestamp helper
# ---------------------------------------------------------------------------

def _get_db2_format_timestamp() -> str:
    """
    Generate a DB2-format timestamp from the current date/time.

    Format: YYYY-MM-DD-HH.MM.SS.mm0000
    """
    now = datetime.now()
    return now.strftime("%Y-%m-%d-%H.%M.%S.") + f"{now.microsecond // 10000:02d}0000"


# ---------------------------------------------------------------------------
# Interest calculation logic
# ---------------------------------------------------------------------------

def get_interest_rate(
    group_id: str,
    type_cd: str,
    cat_cd: str,
    discgrp_repo: DisclosureGroupRepository,
) -> tuple[Optional[DisclosureGroupRecord], bool]:
    """
    Look up the interest rate for a group/type/category.

    Corresponds to 1200-GET-INTEREST-RATE:
    - First try with the account's group ID
    - If not found, try with 'DEFAULT' group ID

    Returns:
        Tuple of (record, used_default). record is None if not found at all.
    """
    record = discgrp_repo.read_rate(group_id, type_cd, cat_cd)
    if record is not None:
        return record, False

    # Try default group
    logger.info(
        "DISCLOSURE GROUP RECORD MISSING for %s/%s/%s, trying DEFAULT",
        group_id, type_cd, cat_cd,
    )
    default_record = discgrp_repo.read_rate(DEFAULT_GROUP_ID, type_cd, cat_cd)
    if default_record is not None:
        return default_record, True

    return None, False


def compute_interest(balance: float, annual_rate: float) -> float:
    """
    Compute monthly interest.

    Corresponds to 1300-COMPUTE-INTEREST:
        COMPUTE WS-MONTHLY-INT = (TRAN-CAT-BAL * DIS-INT-RATE) / 1200

    The rate is an annual percentage (e.g. 18.50 means 18.50%).
    Dividing by 1200 converts to a monthly decimal factor:
        monthly_interest = balance * annual_rate / 1200

    Args:
        balance: The category balance amount.
        annual_rate: The annual interest rate as a percentage.

    Returns:
        The monthly interest amount.
    """
    return (balance * annual_rate) / 1200.0


def create_interest_transaction(
    acct_id: str,
    card_num: str,
    monthly_interest: float,
    parm_date: str,
    tran_suffix: int,
    timestamp_fn: Optional[type] = None,
) -> TransactionRecord:
    """
    Create an interest transaction record.

    Corresponds to 1300-B-WRITE-TX.

    Args:
        acct_id: The account identifier.
        card_num: The card number from the cross-reference.
        monthly_interest: The computed monthly interest amount.
        parm_date: The processing date (YYYY-MM-DD format, 10 chars).
        tran_suffix: Sequential suffix for the transaction ID.
        timestamp_fn: Optional callable returning a timestamp string.

    Returns:
        A TransactionRecord for the interest charge.
    """
    ts = timestamp_fn() if timestamp_fn else _get_db2_format_timestamp()

    # Transaction ID = PARM-DATE + suffix (STRING DELIMITED BY SIZE)
    tran_id = f"{parm_date}{tran_suffix:06d}"

    return TransactionRecord(
        tran_id=tran_id,
        tran_type_cd=INTEREST_TRAN_TYPE_CD,
        tran_cat_cd=INTEREST_TRAN_CAT_CD,
        tran_source=INTEREST_TRAN_SOURCE,
        tran_desc=f"Int. for a/c {acct_id}",
        tran_amt=monthly_interest,
        tran_merchant_id="0",
        tran_merchant_name="",
        tran_merchant_city="",
        tran_merchant_zip="",
        tran_card_num=card_num,
        tran_orig_ts=ts,
        tran_proc_ts=ts,
    )


def update_account_for_interest(
    account: AccountRecord,
    total_interest: float,
    acct_repo: AccountRepository,
) -> None:
    """
    Update account balances after interest calculation.

    Corresponds to 1050-UPDATE-ACCOUNT:
    - Add total interest to current balance
    - Reset current cycle credit to 0
    - Reset current cycle debit to 0
    - Rewrite the account record

    Args:
        account: The account record to update.
        total_interest: The total interest accumulated for this account.
        acct_repo: The account repository for persistence.
    """
    account.curr_bal += total_interest
    account.curr_cyc_credit = 0.0
    account.curr_cyc_debit = 0.0
    acct_repo.update_account(account)


# ---------------------------------------------------------------------------
# Main batch entry point
# ---------------------------------------------------------------------------

def run(
    category_balances: List[TranCatBalRecord],
    xref_repo: CardXrefRepository,
    acct_repo: AccountRepository,
    discgrp_repo: DisclosureGroupRepository,
    tran_repo: TransactionRepository,
    parm_date: str = "",
    timestamp_fn: Optional[type] = None,
) -> BatchResult:
    """
    Main entry point for the CBACT04C batch process.

    Processes transaction category balance records (assumed sorted by account),
    groups them by account, calculates interest for each category using
    disclosure group rates, creates interest transaction records, and updates
    account balances.

    Args:
        category_balances: List of category balance records, sorted by acct_id.
        xref_repo: Repository for card cross-reference lookups by account.
        acct_repo: Repository for account data (read and update).
        discgrp_repo: Repository for disclosure group (interest rate) lookups.
        tran_repo: Repository for writing interest transactions.
        parm_date: Processing date in YYYY-MM-DD format (from JCL PARM).
        timestamp_fn: Optional callable returning a timestamp string (for testing).

    Returns:
        A BatchResult summarizing the entire batch run.
    """
    logger.info("START OF EXECUTION OF PROGRAM CBACT04C")

    if not parm_date:
        parm_date = datetime.now().strftime("%Y-%m-%d")

    batch_result = BatchResult()
    tran_suffix = 0

    # Group category balances by account (they are sorted by acct_id)
    current_acct_id = ""
    current_account: Optional[AccountRecord] = None
    current_xref: Optional[CardXrefRecord] = None
    current_summary: Optional[AccountInterestSummary] = None
    total_interest = 0.0

    def _finalize_account() -> None:
        """Update the current account and finalize its summary."""
        if current_account is not None and current_summary is not None:
            current_summary.total_interest = total_interest
            update_account_for_interest(current_account, total_interest, acct_repo)
            batch_result.account_summaries.append(current_summary)
            batch_result.accounts_processed += 1
            batch_result.total_interest_charged += total_interest

    for cat_bal in category_balances:
        batch_result.records_read += 1

        # New account group?
        if cat_bal.acct_id != current_acct_id:
            # Finalize previous account
            if current_acct_id:
                _finalize_account()

            # Start new account group
            current_acct_id = cat_bal.acct_id
            total_interest = 0.0
            current_summary = AccountInterestSummary(acct_id=current_acct_id)

            # 1100-GET-ACCT-DATA
            current_account = acct_repo.read_account(current_acct_id)
            if current_account is None:
                logger.error("ACCOUNT NOT FOUND: %s", current_acct_id)
                current_xref = None
                continue

            # 1110-GET-XREF-DATA
            current_xref = xref_repo.lookup_by_acct_id(current_acct_id)
            if current_xref is None:
                logger.error("XREF NOT FOUND FOR ACCOUNT: %s", current_acct_id)

        if current_account is None:
            continue

        # 1200-GET-INTEREST-RATE
        group_id = current_account.group_id
        rate_record, used_default = get_interest_rate(
            group_id, cat_bal.type_cd, cat_bal.cat_cd, discgrp_repo
        )

        if rate_record is None or rate_record.int_rate == 0.0:
            # No rate or zero rate -> no interest for this category
            if current_summary is not None:
                current_summary.category_results.append(InterestResult(
                    acct_id=current_acct_id,
                    type_cd=cat_bal.type_cd,
                    cat_cd=cat_bal.cat_cd,
                    balance=cat_bal.balance,
                    int_rate=0.0,
                    monthly_interest=0.0,
                    used_default_rate=False,
                ))
            continue

        # 1300-COMPUTE-INTEREST
        monthly_int = compute_interest(cat_bal.balance, rate_record.int_rate)
        total_interest += monthly_int

        interest_result = InterestResult(
            acct_id=current_acct_id,
            type_cd=cat_bal.type_cd,
            cat_cd=cat_bal.cat_cd,
            balance=cat_bal.balance,
            int_rate=rate_record.int_rate,
            monthly_interest=monthly_int,
            used_default_rate=used_default,
        )

        # 1300-B-WRITE-TX
        card_num = current_xref.card_num if current_xref else ""
        tran_suffix += 1
        tran_record = create_interest_transaction(
            current_acct_id, card_num, monthly_int,
            parm_date, tran_suffix, timestamp_fn,
        )
        tran_repo.write_transaction(tran_record)
        batch_result.interest_transactions_created += 1

        if current_summary is not None:
            current_summary.category_results.append(interest_result)
            current_summary.transactions_created.append(tran_record)

    # Finalize last account
    if current_acct_id:
        _finalize_account()

    logger.info("RECORDS READ: %d", batch_result.records_read)
    logger.info("ACCOUNTS PROCESSED: %d", batch_result.accounts_processed)
    logger.info("INTEREST TRANSACTIONS: %d", batch_result.interest_transactions_created)
    logger.info("END OF EXECUTION OF PROGRAM CBACT04C")

    return batch_result
