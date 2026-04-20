"""
COACTVWC - Account View Program (Python Translation)

Translated from the COBOL program COACTVWC.CBL in the AWS CardDemo
mainframe modernization project.  This module implements the business
logic for viewing account details in read-only mode.

Original: CICS COBOL program using BMS maps and VSAM files.
This translation separates the pure business logic (validation, data
lookup, result building) from the CICS presentation layer so the rules
can be tested and reused independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Constants (from copybooks COTTL01Y, CSMSG01Y, literals)
# ---------------------------------------------------------------------------

PROGRAM_NAME = "COACTVWC"
TRANSACTION_ID = "CAVW"

TITLE_01 = "      AWS Mainframe Modernization       "
TITLE_02 = "              CardDemo                  "

MSG_THANK_YOU = "Thank you for using CardDemo application..."


# ---------------------------------------------------------------------------
# Data structures (from copybooks CVACT01Y, CVACT02Y, CVACT03Y, CVCUS01Y)
# ---------------------------------------------------------------------------

@dataclass
class AccountRecord:
    """Account record layout (CVACT01Y - 300 bytes)."""
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
class CardRecord:
    """Card record layout (CVACT02Y - 150 bytes)."""
    card_num: str = ""                  # PIC X(16)
    acct_id: str = ""                   # PIC 9(11)
    cvv_cd: str = ""                    # PIC 9(03)
    embossed_name: str = ""             # PIC X(50)
    expiration_date: str = ""           # PIC X(10)
    active_status: str = ""             # PIC X(01)


@dataclass
class CardXrefRecord:
    """Card cross-reference record (CVACT03Y - 50 bytes)."""
    card_num: str = ""                  # XREF-CARD-NUM  PIC X(16)
    cust_id: str = ""                   # XREF-CUST-ID   PIC 9(09)
    acct_id: str = ""                   # XREF-ACCT-ID   PIC 9(11)


@dataclass
class CustomerRecord:
    """Customer record layout (CVCUS01Y - 500 bytes)."""
    cust_id: str = ""                   # PIC 9(09)
    first_name: str = ""                # PIC X(25)
    middle_name: str = ""               # PIC X(25)
    last_name: str = ""                 # PIC X(25)
    addr_line_1: str = ""               # PIC X(50)
    addr_line_2: str = ""               # PIC X(50)
    addr_line_3: str = ""               # PIC X(50)  (city)
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
class ValidationResult:
    """Outcome of a validation step."""
    is_valid: bool = True
    error_message: str = ""
    error_field: str = ""


@dataclass
class AccountViewResult:
    """Outcome of a view-account operation."""
    success: bool = False
    message: str = ""
    account: Optional[AccountRecord] = None
    customer: Optional[CustomerRecord] = None
    card_xref: Optional[CardXrefRecord] = None


# ---------------------------------------------------------------------------
# Repository interfaces (abstracts VSAM file I/O)
# ---------------------------------------------------------------------------

class AccountRepository:
    """
    Abstract interface for account data access.

    In the original COBOL program these are CICS READ operations against
    VSAM KSDS files.  Concrete implementations can use a database,
    in-memory dict, or any other store.
    """

    def get_account(self, acct_id: str) -> Optional[AccountRecord]:
        """
        Read an account record by account ID.

        Corresponds to READ on ACCTDAT file.
        Returns None if not found.
        """
        raise NotImplementedError


class CardXrefRepository:
    """Abstract interface for card cross-reference data access."""

    def lookup_by_account(self, acct_id: str) -> Optional[CardXrefRecord]:
        """
        Look up a card cross-reference record by account ID.

        Corresponds to READ on CXACAIX (alternate index keyed by account).
        Returns None if not found.
        """
        raise NotImplementedError

    def lookup_by_card(self, card_num: str) -> Optional[CardXrefRecord]:
        """
        Look up a card cross-reference record by card number.

        Corresponds to READ on CARDXREF (primary key is card number).
        Returns None if not found.
        """
        raise NotImplementedError


class CustomerRepository:
    """Abstract interface for customer data access."""

    def get_customer(self, cust_id: str) -> Optional[CustomerRecord]:
        """
        Read a customer record by customer ID.

        Corresponds to READ on CUSTDAT file.
        Returns None if not found.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# In-memory repositories for testing
# ---------------------------------------------------------------------------

class InMemoryAccountRepository(AccountRepository):
    """Simple in-memory implementation backed by a Python dict."""

    def __init__(self) -> None:
        self.accounts: dict[str, AccountRecord] = {}

    def add_account(self, record: AccountRecord) -> None:
        """Register an account record."""
        self.accounts[record.acct_id] = record

    def get_account(self, acct_id: str) -> Optional[AccountRecord]:
        return self.accounts.get(acct_id)


class InMemoryCardXrefRepository(CardXrefRepository):
    """Simple in-memory implementation backed by Python dicts."""

    def __init__(self) -> None:
        self.xref_by_account: dict[str, CardXrefRecord] = {}
        self.xref_by_card: dict[str, CardXrefRecord] = {}

    def add_xref(self, record: CardXrefRecord) -> None:
        """Register a cross-reference record for both lookups."""
        self.xref_by_account[record.acct_id] = record
        self.xref_by_card[record.card_num] = record

    def lookup_by_account(self, acct_id: str) -> Optional[CardXrefRecord]:
        return self.xref_by_account.get(acct_id)

    def lookup_by_card(self, card_num: str) -> Optional[CardXrefRecord]:
        return self.xref_by_card.get(card_num)


class InMemoryCustomerRepository(CustomerRepository):
    """Simple in-memory implementation backed by a Python dict."""

    def __init__(self) -> None:
        self.customers: dict[str, CustomerRecord] = {}

    def add_customer(self, record: CustomerRecord) -> None:
        """Register a customer record."""
        self.customers[record.cust_id] = record

    def get_customer(self, cust_id: str) -> Optional[CustomerRecord]:
        return self.customers.get(cust_id)


# ---------------------------------------------------------------------------
# Validation functions
# ---------------------------------------------------------------------------

def validate_account_id(acct_id_input: str) -> ValidationResult:
    """
    Validate the account ID entered by the user.

    Business rules (from 2210-EDIT-ACCOUNT):
    1. Must be supplied (not blank or spaces).
    2. Must be numeric.
    3. Must not be all zeros.
    """
    raw = acct_id_input.strip()

    if raw == "" or raw == "*":
        return ValidationResult(
            is_valid=False,
            error_message="Account number not provided",
            error_field="acct_id",
        )

    if not raw.isdigit():
        return ValidationResult(
            is_valid=False,
            error_message=(
                "Account Filter must be a non-zero 11 digit number"
            ),
            error_field="acct_id",
        )

    if int(raw) == 0:
        return ValidationResult(
            is_valid=False,
            error_message=(
                "Account Filter must be a non-zero 11 digit number"
            ),
            error_field="acct_id",
        )

    return ValidationResult(is_valid=True)


# ---------------------------------------------------------------------------
# Core view-account logic
# ---------------------------------------------------------------------------

def view_account(
    acct_id_input: str,
    acct_repo: AccountRepository,
    xref_repo: CardXrefRepository,
    cust_repo: CustomerRepository,
) -> AccountViewResult:
    """
    Full account-view workflow: validate, look up xref, account, customer.

    This is the top-level entry point that mirrors the COBOL program's
    9000-READ-ACCT paragraph chain.

    Parameters
    ----------
    acct_id_input : str
        Raw account ID string from the user.
    acct_repo : AccountRepository
        Data access for account records.
    xref_repo : CardXrefRepository
        Data access for card cross-reference records.
    cust_repo : CustomerRepository
        Data access for customer records.

    Returns
    -------
    AccountViewResult
        Contains account, customer, and xref data on success, or an
        error message on failure.
    """
    # Step 1: Validate account ID
    val = validate_account_id(acct_id_input)
    if not val.is_valid:
        return AccountViewResult(success=False, message=val.error_message)

    # Normalise to 11-digit zero-padded string
    normalised_acct = acct_id_input.strip().zfill(11)

    # Step 2: Look up cross-reference by account ID (9200-GETCARDXREF-BYACCT)
    xref = xref_repo.lookup_by_account(normalised_acct)
    if xref is None:
        return AccountViewResult(
            success=False,
            message=(
                f"Account:{normalised_acct} not found in Cross ref file."
            ),
        )

    # Step 3: Read account master (9300-GETACCTDATA-BYACCT)
    account = acct_repo.get_account(normalised_acct)
    if account is None:
        return AccountViewResult(
            success=False,
            message=(
                f"Account:{normalised_acct} not found in Acct Master file."
            ),
        )

    # Step 4: Read customer master (9400-GETCUSTDATA-BYCUST)
    customer = cust_repo.get_customer(xref.cust_id)
    if customer is None:
        return AccountViewResult(
            success=False,
            message=(
                f"CustId:{xref.cust_id} not found in customer master."
            ),
        )

    return AccountViewResult(
        success=True,
        message="Account details retrieved successfully",
        account=account,
        customer=customer,
        card_xref=xref,
    )


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def format_ssn(ssn: str) -> str:
    """
    Format a 9-digit SSN string as XXX-XX-XXXX.

    Corresponds to the STRING operation in 1200-SETUP-SCREEN-VARS.
    """
    raw = ssn.strip().zfill(9)
    return f"{raw[0:3]}-{raw[3:5]}-{raw[5:9]}"


def get_header_info() -> dict[str, str]:
    """
    Return screen header information.

    Corresponds to 1100-SCREEN-INIT setup of title, program name,
    transaction ID, date and time fields.
    """
    from datetime import datetime

    now = datetime.now()
    return {
        "title01": TITLE_01,
        "title02": TITLE_02,
        "program_name": PROGRAM_NAME,
        "transaction_id": TRANSACTION_ID,
        "current_date": now.strftime("%m/%d/%y"),
        "current_time": now.strftime("%H:%M:%S"),
    }
