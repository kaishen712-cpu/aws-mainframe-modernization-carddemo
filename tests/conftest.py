"""Shared pytest fixtures for the CardDemo test suite.

All test data is synthetic — NEVER use real customer data.
SECURITY: Never log account numbers, card numbers, or transaction
amounts in plain text (CPS 234 requirement).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from batch.models import (
    Account,
    Card,
    CardXref,
    Customer,
    DailyTransaction,
    DisclosureGroup,
    TranCatBal,
    Transaction,
    TransactionCategory,
    TransactionType,
    UserSecurity,
)

# ---------------------------------------------------------------------------
# Individual record fixtures — synthetic data only
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_account(db: None) -> Account:
    """Synthetic account record for testing."""
    return Account.objects.create(
        acct_id="00000000001",
        acct_active_status="Y",
        acct_curr_bal=Decimal("1000.00"),
        acct_credit_limit=Decimal("5000.00"),
        acct_cash_credit_limit=Decimal("1000.00"),
        acct_open_date="2020-01-01",
        acct_expiration_date="2030-12-31",
        acct_reissue_date="2025-01-01",
        acct_curr_cyc_credit=Decimal("500.00"),
        acct_curr_cyc_debit=Decimal("200.00"),
        acct_addr_zip="10001",
        acct_group_id="GROUP1",
    )


@pytest.fixture()
def sample_account_2(db: None) -> Account:
    """Second synthetic account record."""
    return Account.objects.create(
        acct_id="00000000002",
        acct_active_status="Y",
        acct_curr_bal=Decimal("2500.00"),
        acct_credit_limit=Decimal("10000.00"),
        acct_cash_credit_limit=Decimal("2000.00"),
        acct_open_date="2019-06-15",
        acct_expiration_date="2029-06-15",
        acct_reissue_date="2024-06-15",
        acct_curr_cyc_credit=Decimal("0.00"),
        acct_curr_cyc_debit=Decimal("0.00"),
        acct_addr_zip="90210",
        acct_group_id="GROUP1",
    )


@pytest.fixture()
def sample_card(db: None) -> Card:
    """Synthetic card record."""
    return Card.objects.create(
        card_num="4111111111111111",
        card_acct_id="00000000001",
        card_cvv_cd="123",
        card_embossed_name="TEST USER ONE",
        card_expiration_date="2030-12-31",
        card_active_status="Y",
    )


@pytest.fixture()
def sample_card_2(db: None) -> Card:
    """Second synthetic card record."""
    return Card.objects.create(
        card_num="4222222222222222",
        card_acct_id="00000000002",
        card_cvv_cd="456",
        card_embossed_name="TEST USER TWO",
        card_expiration_date="2029-06-15",
        card_active_status="Y",
    )


@pytest.fixture()
def sample_xref(db: None) -> CardXref:
    """Synthetic cross-reference record."""
    return CardXref.objects.create(
        xref_card_num="4111111111111111",
        xref_cust_id="000000001",
        xref_acct_id="00000000001",
    )


@pytest.fixture()
def sample_xref_2(db: None) -> CardXref:
    """Second synthetic cross-reference record."""
    return CardXref.objects.create(
        xref_card_num="4222222222222222",
        xref_cust_id="000000002",
        xref_acct_id="00000000002",
    )


@pytest.fixture()
def sample_customer(db: None) -> Customer:
    """Synthetic customer record."""
    return Customer.objects.create(
        cust_id="000000001",
        cust_first_name="TEST",
        cust_middle_name="M",
        cust_last_name="USER",
        cust_addr_line_1="123 TEST ST",
        cust_addr_state_cd="NY",
        cust_addr_country_cd="US",
        cust_addr_zip="10001",
        cust_phone_num_1="5551234567",
        cust_ssn="000000000",
        cust_dob_yyyy_mm_dd="1990-01-01",
        cust_fico_credit_score="750",
    )


@pytest.fixture()
def sample_transaction(db: None) -> Transaction:
    """Synthetic transaction record."""
    return Transaction.objects.create(
        tran_id="0000000000000001",
        tran_type_cd="01",
        tran_cat_cd="5001",
        tran_source="ONLINE",
        tran_desc="TEST PURCHASE",
        tran_amt=Decimal("100.00"),
        tran_merchant_id="000000001",
        tran_merchant_name="TEST MERCHANT",
        tran_merchant_city="NEW YORK",
        tran_merchant_zip="10001",
        tran_card_num="4111111111111111",
        tran_orig_ts="2025-01-15-10.30.00.000000",
        tran_proc_ts="2025-01-15-10.30.01.000000",
    )


@pytest.fixture()
def sample_daily_transaction(db: None) -> DailyTransaction:
    """Synthetic daily transaction record for batch posting."""
    return DailyTransaction.objects.create(
        dalytran_id="0000000000000001",
        dalytran_type_cd="01",
        dalytran_cat_cd="5001",
        dalytran_source="BATCH",
        dalytran_desc="TEST DAILY TXN",
        dalytran_amt=Decimal("150.00"),
        dalytran_merchant_id="000000001",
        dalytran_merchant_name="TEST MERCHANT",
        dalytran_merchant_city="NEW YORK",
        dalytran_merchant_zip="10001",
        dalytran_card_num="4111111111111111",
        dalytran_orig_ts="2025-01-15-08.00.00.000000",
    )


@pytest.fixture()
def sample_disclosure_group(db: None) -> DisclosureGroup:
    """Synthetic disclosure group record.

    NOTE: dis_int_rate is a hardcoded threshold field.
    HUMAN REVIEW REQUIRED before production use.
    """
    return DisclosureGroup.objects.create(
        dis_acct_group_id="GROUP1",
        dis_tran_type_cd="01",
        dis_tran_cat_cd="5001",
        dis_int_rate=Decimal("18.99"),
    )


@pytest.fixture()
def sample_transaction_type(db: None) -> TransactionType:
    """Synthetic transaction type record."""
    return TransactionType.objects.create(
        tran_type="01",
        tran_type_desc="PURCHASE",
    )


@pytest.fixture()
def sample_transaction_category(db: None) -> TransactionCategory:
    """Synthetic transaction category record."""
    return TransactionCategory.objects.create(
        tran_type_cd="01",
        tran_cat_cd="5001",
        tran_cat_type_desc="RETAIL PURCHASE",
    )


@pytest.fixture()
def sample_tran_cat_bal(db: None) -> TranCatBal:
    """Synthetic transaction category balance record."""
    return TranCatBal.objects.create(
        trancat_acct_id="00000000001",
        trancat_type_cd="01",
        trancat_cd="5001",
        tran_cat_bal=Decimal("500.00"),
    )


@pytest.fixture()
def sample_user_security(db: None) -> UserSecurity:
    """Synthetic user security record."""
    return UserSecurity.objects.create(
        sec_usr_id="TESTUSR1",
        sec_usr_fname="Test",
        sec_usr_lname="User",
        sec_usr_pwd="hashed_password_placeholder",
        sec_usr_type="U",
    )


@pytest.fixture()
def sample_admin_security(db: None) -> UserSecurity:
    """Synthetic admin user security record."""
    return UserSecurity.objects.create(
        sec_usr_id="ADMIN001",
        sec_usr_fname="Admin",
        sec_usr_lname="User",
        sec_usr_pwd="hashed_password_placeholder",
        sec_usr_type="A",
    )


# ---------------------------------------------------------------------------
# Composite fixtures — sets up a complete test scenario
# ---------------------------------------------------------------------------


@pytest.fixture()
def complete_account_setup(
    sample_account: Account,
    sample_card: Card,
    sample_xref: CardXref,
    sample_customer: Customer,
    sample_disclosure_group: DisclosureGroup,
    sample_transaction_type: TransactionType,
    sample_transaction_category: TransactionCategory,
    sample_tran_cat_bal: TranCatBal,
) -> dict[str, object]:
    """Complete account setup with all related records.

    Returns a dict containing all created records for easy access.
    """
    return {
        "account": sample_account,
        "card": sample_card,
        "xref": sample_xref,
        "customer": sample_customer,
        "disclosure_group": sample_disclosure_group,
        "transaction_type": sample_transaction_type,
        "transaction_category": sample_transaction_category,
        "tran_cat_bal": sample_tran_cat_bal,
    }
