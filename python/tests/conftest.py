"""
Shared test fixtures for the CardDemo Python test suite.

Provides pre-populated in-memory repositories with realistic test data,
sample records for each entity type, and helper functions for creating
test data with sensible defaults.
"""

from __future__ import annotations

import pytest

from python.models.records import (
    AccountRecord,
    CardRecord,
    CardXrefRecord,
    CustomerRecord,
    DailyTransactionRecord,
    DisclosureGroupRecord,
    TranCatBalRecord,
    TransactionCategoryRecord,
    TransactionRecord,
    TransactionTypeRecord,
    UserSecurityRecord,
)
from python.repositories.in_memory import (
    InMemoryAccountRepository,
    InMemoryCardRepository,
    InMemoryCardXrefRepository,
    InMemoryCustomerRepository,
    InMemoryDailyTransactionRepository,
    InMemoryDisclosureGroupRepository,
    InMemoryTranCatBalRepository,
    InMemoryTransactionCategoryRepository,
    InMemoryTransactionRepository,
    InMemoryTransactionTypeRepository,
    InMemoryUserSecurityRepository,
)


# ---------------------------------------------------------------------------
# Sample record factories
# ---------------------------------------------------------------------------

def make_account(
    acct_id: str = "00000000001",
    active: str = "Y",
    balance: float = 1500.00,
    credit_limit: float = 5000.00,
) -> AccountRecord:
    """Create a sample account record with sensible defaults."""
    return AccountRecord(
        acct_id=acct_id,
        acct_active_status=active,
        acct_curr_bal=balance,
        acct_credit_limit=credit_limit,
        acct_cash_credit_limit=1000.00,
        acct_open_date="2020-01-15",
        acct_expiration_date="2027-01-15",
        acct_reissue_date="2025-01-15",
        acct_curr_cyc_credit=0.0,
        acct_curr_cyc_debit=0.0,
        acct_addr_zip="10001",
        acct_group_id="GROUP001",
    )


def make_card(
    card_num: str = "4111111111111111",
    acct_id: str = "00000000001",
    name: str = "JOHN DOE",
    active: str = "Y",
) -> CardRecord:
    """Create a sample card record with sensible defaults."""
    return CardRecord(
        card_num=card_num,
        card_acct_id=acct_id,
        card_cvv_cd="123",
        card_embossed_name=name,
        card_expiration_date="2027-12-31",
        card_active_status=active,
    )


def make_card_xref(
    card_num: str = "4111111111111111",
    cust_id: str = "000000001",
    acct_id: str = "00000000001",
) -> CardXrefRecord:
    """Create a sample card cross-reference record."""
    return CardXrefRecord(
        xref_card_num=card_num,
        xref_cust_id=cust_id,
        xref_acct_id=acct_id,
    )


def make_customer(
    cust_id: str = "000000001",
    first: str = "John",
    last: str = "Doe",
    state: str = "NY",
) -> CustomerRecord:
    """Create a sample customer record with sensible defaults."""
    return CustomerRecord(
        cust_id=cust_id,
        cust_first_name=first,
        cust_middle_name="Q",
        cust_last_name=last,
        cust_addr_line_1="123 Main St",
        cust_addr_line_2="Apt 4B",
        cust_addr_line_3="",
        cust_addr_state_cd=state,
        cust_addr_country_cd="US",
        cust_addr_zip="10001",
        cust_phone_num_1="2125551234",
        cust_phone_num_2="",
        cust_ssn="123456789",
        cust_govt_issued_id="DL12345678",
        cust_dob_yyyy_mm_dd="1985-06-15",
        cust_eft_account_id="EFT0000001",
        cust_pri_card_holder_ind="Y",
        cust_fico_credit_score="750",
    )


def make_transaction(
    tran_id: str = "0000000000000001",
    card_num: str = "4111111111111111",
    amount: float = 50.00,
    type_cd: str = "SA",
    cat_cd: str = "5001",
) -> TransactionRecord:
    """Create a sample transaction record with sensible defaults."""
    return TransactionRecord(
        tran_id=tran_id,
        tran_type_cd=type_cd,
        tran_cat_cd=cat_cd,
        tran_source="ONLINE",
        tran_desc="Test purchase",
        tran_amt=amount,
        tran_merchant_id="123456789",
        tran_merchant_name="Test Merchant",
        tran_merchant_city="New York",
        tran_merchant_zip="10001",
        tran_card_num=card_num,
        tran_orig_ts="2025-03-15",
        tran_proc_ts="2025-03-15",
    )


def make_daily_transaction(
    tran_id: str = "0000000000000001",
    card_num: str = "4111111111111111",
    amount: float = 25.00,
) -> DailyTransactionRecord:
    """Create a sample daily transaction record."""
    return DailyTransactionRecord(
        dalytran_id=tran_id,
        dalytran_type_cd="SA",
        dalytran_cat_cd="5001",
        dalytran_source="ONLINE",
        dalytran_desc="Daily test purchase",
        dalytran_amt=amount,
        dalytran_merchant_id="123456789",
        dalytran_merchant_name="Test Merchant",
        dalytran_merchant_city="New York",
        dalytran_merchant_zip="10001",
        dalytran_card_num=card_num,
        dalytran_orig_ts="2025-03-15",
        dalytran_proc_ts="2025-03-15",
    )


def make_user(
    user_id: str = "USER0001",
    first: str = "Test",
    last: str = "User",
    password: str = "pass1234",
    user_type: str = "U",
) -> UserSecurityRecord:
    """Create a sample user security record."""
    return UserSecurityRecord(
        sec_usr_id=user_id,
        sec_usr_fname=first,
        sec_usr_lname=last,
        sec_usr_pwd=password,
        sec_usr_type=user_type,
    )


def make_transaction_type(
    type_cd: str = "SA",
    desc: str = "Sale",
) -> TransactionTypeRecord:
    """Create a sample transaction type record."""
    return TransactionTypeRecord(tran_type=type_cd, tran_type_desc=desc)


def make_transaction_category(
    type_cd: str = "SA",
    cat_cd: str = "5001",
    desc: str = "Retail Sale",
) -> TransactionCategoryRecord:
    """Create a sample transaction category record."""
    return TransactionCategoryRecord(
        tran_type_cd=type_cd,
        tran_cat_cd=cat_cd,
        tran_cat_type_desc=desc,
    )


# ---------------------------------------------------------------------------
# Individual repository fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def account_repo() -> InMemoryAccountRepository:
    """Empty account repository."""
    return InMemoryAccountRepository()


@pytest.fixture
def card_repo() -> InMemoryCardRepository:
    """Empty card repository."""
    return InMemoryCardRepository()


@pytest.fixture
def card_xref_repo() -> InMemoryCardXrefRepository:
    """Empty card cross-reference repository."""
    return InMemoryCardXrefRepository()


@pytest.fixture
def customer_repo() -> InMemoryCustomerRepository:
    """Empty customer repository."""
    return InMemoryCustomerRepository()


@pytest.fixture
def transaction_repo() -> InMemoryTransactionRepository:
    """Empty transaction repository."""
    return InMemoryTransactionRepository()


@pytest.fixture
def daily_transaction_repo() -> InMemoryDailyTransactionRepository:
    """Empty daily transaction repository."""
    return InMemoryDailyTransactionRepository()


@pytest.fixture
def user_repo() -> InMemoryUserSecurityRepository:
    """Empty user security repository."""
    return InMemoryUserSecurityRepository()


@pytest.fixture
def tran_type_repo() -> InMemoryTransactionTypeRepository:
    """Empty transaction type repository."""
    return InMemoryTransactionTypeRepository()


@pytest.fixture
def tran_cat_repo() -> InMemoryTransactionCategoryRepository:
    """Empty transaction category repository."""
    return InMemoryTransactionCategoryRepository()


@pytest.fixture
def tran_cat_bal_repo() -> InMemoryTranCatBalRepository:
    """Empty transaction category balance repository."""
    return InMemoryTranCatBalRepository()


@pytest.fixture
def disclosure_repo() -> InMemoryDisclosureGroupRepository:
    """Empty disclosure group repository."""
    return InMemoryDisclosureGroupRepository()


# ---------------------------------------------------------------------------
# Pre-populated system fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def populated_system() -> dict:
    """A complete test environment with interrelated data.

    Returns a dict containing all pre-populated repositories and
    the sample records seeded into them.

    Relationships:
    - Customer 000000001 (John Doe) owns Account 00000000001
    - Customer 000000002 (Jane Smith) owns Account 00000000002
    - Card 4111111111111111 is linked to Account 00000000001 / Customer 000000001
    - Card 4222222222222222 is linked to Account 00000000002 / Customer 000000002
    - Transactions exist on both cards
    - Users ADMIN001 (admin) and USER0001 (regular) are registered
    - Transaction types SA (Sale) and CR (Credit) are defined
    - Category 5001 (Retail Sale) and 5002 (Grocery) are defined
    """

    # -- Repositories --
    acct_repo = InMemoryAccountRepository()
    card_repo = InMemoryCardRepository()
    xref_repo = InMemoryCardXrefRepository()
    cust_repo = InMemoryCustomerRepository()
    txn_repo = InMemoryTransactionRepository()
    daily_repo = InMemoryDailyTransactionRepository()
    user_repo = InMemoryUserSecurityRepository()
    ttype_repo = InMemoryTransactionTypeRepository()
    tcat_repo = InMemoryTransactionCategoryRepository()
    tcbal_repo = InMemoryTranCatBalRepository()
    disc_repo = InMemoryDisclosureGroupRepository()

    # -- Customers --
    cust1 = make_customer(cust_id="000000001", first="John", last="Doe")
    cust2 = make_customer(cust_id="000000002", first="Jane", last="Smith", state="CA")
    cust_repo.seed(cust1)
    cust_repo.seed(cust2)

    # -- Accounts --
    acct1 = make_account(acct_id="00000000001", balance=1500.00)
    acct2 = make_account(acct_id="00000000002", balance=3200.00, credit_limit=10000.00)
    acct_repo.seed(acct1)
    acct_repo.seed(acct2)

    # -- Cards --
    card1 = make_card(card_num="4111111111111111", acct_id="00000000001", name="JOHN DOE")
    card2 = make_card(card_num="4222222222222222", acct_id="00000000002", name="JANE SMITH")
    card_repo.seed(card1)
    card_repo.seed(card2)

    # -- Cross-references --
    xref1 = make_card_xref(
        card_num="4111111111111111", cust_id="000000001", acct_id="00000000001"
    )
    xref2 = make_card_xref(
        card_num="4222222222222222", cust_id="000000002", acct_id="00000000002"
    )
    xref_repo.seed(xref1)
    xref_repo.seed(xref2)

    # -- Transactions --
    txn1 = make_transaction(
        tran_id="0000000000000001",
        card_num="4111111111111111",
        amount=50.00,
        type_cd="SA",
        cat_cd="5001",
    )
    txn2 = make_transaction(
        tran_id="0000000000000002",
        card_num="4111111111111111",
        amount=120.50,
        type_cd="SA",
        cat_cd="5002",
    )
    txn3 = make_transaction(
        tran_id="0000000000000003",
        card_num="4222222222222222",
        amount=75.25,
        type_cd="CR",
        cat_cd="5001",
    )
    txn_repo.seed(txn1)
    txn_repo.seed(txn2)
    txn_repo.seed(txn3)

    # -- Daily transactions --
    daily1 = make_daily_transaction(
        tran_id="0000000000000004",
        card_num="4111111111111111",
        amount=30.00,
    )
    daily_repo.seed(daily1)

    # -- Users --
    admin_user = make_user(
        user_id="ADMIN001", first="Admin", last="User",
        password="adm12345", user_type="A",
    )
    regular_user = make_user(
        user_id="USER0001", first="Regular", last="User",
        password="usr12345", user_type="U",
    )
    user_repo.seed(admin_user)
    user_repo.seed(regular_user)

    # -- Transaction types --
    sale_type = make_transaction_type(type_cd="SA", desc="Sale")
    credit_type = make_transaction_type(type_cd="CR", desc="Credit")
    ttype_repo.seed(sale_type)
    ttype_repo.seed(credit_type)

    # -- Transaction categories --
    retail_cat = make_transaction_category(type_cd="SA", cat_cd="5001", desc="Retail Sale")
    grocery_cat = make_transaction_category(type_cd="SA", cat_cd="5002", desc="Grocery")
    credit_cat = make_transaction_category(type_cd="CR", cat_cd="5001", desc="Credit Return")
    tcat_repo.seed(retail_cat)
    tcat_repo.seed(grocery_cat)
    tcat_repo.seed(credit_cat)

    # -- Transaction category balances --
    tcbal_repo.seed(TranCatBalRecord(
        trancat_acct_id="00000000001",
        trancat_type_cd="SA",
        trancat_cd="5001",
        tran_cat_bal=50.00,
    ))
    tcbal_repo.seed(TranCatBalRecord(
        trancat_acct_id="00000000001",
        trancat_type_cd="SA",
        trancat_cd="5002",
        tran_cat_bal=120.50,
    ))

    # -- Disclosure groups --
    disc_repo.seed(DisclosureGroupRecord(
        dis_acct_group_id="GROUP001",
        dis_tran_type_cd="SA",
        dis_tran_cat_cd="5001",
        dis_int_rate=18.99,
    ))

    return {
        "account_repo": acct_repo,
        "card_repo": card_repo,
        "card_xref_repo": xref_repo,
        "customer_repo": cust_repo,
        "transaction_repo": txn_repo,
        "daily_transaction_repo": daily_repo,
        "user_repo": user_repo,
        "tran_type_repo": ttype_repo,
        "tran_cat_repo": tcat_repo,
        "tran_cat_bal_repo": tcbal_repo,
        "disclosure_repo": disc_repo,
        # Sample records for convenience
        "customers": [cust1, cust2],
        "accounts": [acct1, acct2],
        "cards": [card1, card2],
        "xrefs": [xref1, xref2],
        "transactions": [txn1, txn2, txn3],
    }
