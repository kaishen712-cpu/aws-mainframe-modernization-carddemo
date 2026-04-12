"""Factory Boy factories for CardDemo test data generation.

All test data is synthetic — NEVER use real customer data.
SECURITY: Never log account numbers, card numbers, or transaction
amounts in plain text (CPS 234 requirement).

Factories generate realistic but entirely fictional data for testing.
"""

from __future__ import annotations

from decimal import Decimal

import factory
from django.contrib.auth.models import User

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


class AccountFactory(factory.django.DjangoModelFactory):
    """Factory for synthetic Account records."""

    class Meta:
        model = Account

    acct_id = factory.Sequence(lambda n: f"{n + 1:011d}")
    acct_active_status = "Y"
    acct_curr_bal = Decimal("1000.00")
    acct_credit_limit = Decimal("5000.00")
    acct_cash_credit_limit = Decimal("1000.00")
    acct_open_date = "2020-01-01"
    acct_expiration_date = "2030-12-31"
    acct_reissue_date = "2025-01-01"
    acct_curr_cyc_credit = Decimal("0.00")
    acct_curr_cyc_debit = Decimal("0.00")
    acct_addr_zip = "10001"
    acct_group_id = "GROUP1"


class CardFactory(factory.django.DjangoModelFactory):
    """Factory for synthetic Card records."""

    class Meta:
        model = Card

    card_num = factory.Sequence(lambda n: f"4{n + 100000000000000:015d}")
    card_acct_id = factory.Sequence(lambda n: f"{n + 1:011d}")
    card_cvv_cd = "123"
    card_embossed_name = factory.Sequence(lambda n: f"TEST USER {n + 1:04d}")
    card_expiration_date = "2030-12-31"
    card_active_status = "Y"


class CardXrefFactory(factory.django.DjangoModelFactory):
    """Factory for synthetic CardXref records."""

    class Meta:
        model = CardXref

    xref_card_num = factory.Sequence(lambda n: f"4{n + 100000000000000:015d}")
    xref_cust_id = factory.Sequence(lambda n: f"{n + 1:09d}")
    xref_acct_id = factory.Sequence(lambda n: f"{n + 1:011d}")


class CustomerFactory(factory.django.DjangoModelFactory):
    """Factory for synthetic Customer records."""

    class Meta:
        model = Customer

    cust_id = factory.Sequence(lambda n: f"{n + 1:09d}")
    cust_first_name = factory.Sequence(lambda n: f"FIRST{n + 1:04d}")
    cust_middle_name = "M"
    cust_last_name = factory.Sequence(lambda n: f"LAST{n + 1:04d}")
    cust_addr_line_1 = "123 TEST STREET"
    cust_addr_line_2 = ""
    cust_addr_line_3 = ""
    cust_addr_state_cd = "NY"
    cust_addr_country_cd = "US"
    cust_addr_zip = "10001"
    cust_phone_num_1 = "5550001234"
    cust_phone_num_2 = ""
    cust_ssn = factory.Sequence(lambda n: f"{n + 1:09d}")
    cust_govt_issued_id = ""
    cust_dob_yyyy_mm_dd = "1990-01-01"
    cust_eft_account_id = ""
    cust_pri_card_holder_ind = "Y"
    cust_fico_credit_score = "750"


class TransactionFactory(factory.django.DjangoModelFactory):
    """Factory for synthetic Transaction records."""

    class Meta:
        model = Transaction

    tran_id = factory.Sequence(lambda n: f"{n + 1:016d}")
    tran_type_cd = "01"
    tran_cat_cd = "5001"
    tran_source = "ONLINE"
    tran_desc = "TEST TRANSACTION"
    tran_amt = Decimal("100.00")
    tran_merchant_id = "000000001"
    tran_merchant_name = "TEST MERCHANT"
    tran_merchant_city = "NEW YORK"
    tran_merchant_zip = "10001"
    tran_card_num = "4111111111111111"
    tran_orig_ts = "2025-01-15-10.30.00.000000"
    tran_proc_ts = "2025-01-15-10.30.01.000000"


class DailyTransactionFactory(factory.django.DjangoModelFactory):
    """Factory for synthetic DailyTransaction records."""

    class Meta:
        model = DailyTransaction

    dalytran_id = factory.Sequence(lambda n: f"{n + 1:016d}")
    dalytran_type_cd = "01"
    dalytran_cat_cd = "5001"
    dalytran_source = "BATCH"
    dalytran_desc = "TEST DAILY TXN"
    dalytran_amt = Decimal("150.00")
    dalytran_merchant_id = "000000001"
    dalytran_merchant_name = "TEST MERCHANT"
    dalytran_merchant_city = "NEW YORK"
    dalytran_merchant_zip = "10001"
    dalytran_card_num = "4111111111111111"
    dalytran_orig_ts = "2025-01-15-08.00.00.000000"
    dalytran_proc_ts = ""


class TranCatBalFactory(factory.django.DjangoModelFactory):
    """Factory for synthetic TranCatBal records."""

    class Meta:
        model = TranCatBal

    trancat_acct_id = factory.Sequence(lambda n: f"{n + 1:011d}")
    trancat_type_cd = "01"
    trancat_cd = "5001"
    tran_cat_bal = Decimal("0.00")


class DisclosureGroupFactory(factory.django.DjangoModelFactory):
    """Factory for synthetic DisclosureGroup records.

    NOTE: dis_int_rate is a hardcoded threshold field.
    HUMAN REVIEW REQUIRED before production migration.
    """

    class Meta:
        model = DisclosureGroup

    dis_acct_group_id = "GROUP1"
    dis_tran_type_cd = factory.Sequence(lambda n: f"{n + 1:02d}")
    dis_tran_cat_cd = factory.Sequence(lambda n: f"{n + 5001:04d}")
    dis_int_rate = Decimal("18.99")


class TransactionTypeFactory(factory.django.DjangoModelFactory):
    """Factory for synthetic TransactionType records."""

    class Meta:
        model = TransactionType

    tran_type = factory.Sequence(lambda n: f"{n + 1:02d}")
    tran_type_desc = factory.Sequence(lambda n: f"TYPE {n + 1:02d}")


class TransactionCategoryFactory(factory.django.DjangoModelFactory):
    """Factory for synthetic TransactionCategory records."""

    class Meta:
        model = TransactionCategory

    tran_type_cd = "01"
    tran_cat_cd = factory.Sequence(lambda n: f"{n + 5001:04d}")
    tran_cat_type_desc = factory.Sequence(lambda n: f"CATEGORY {n + 1}")


class UserSecurityFactory(factory.django.DjangoModelFactory):
    """Factory for synthetic UserSecurity records."""

    class Meta:
        model = UserSecurity

    sec_usr_id = factory.Sequence(lambda n: f"USR{n + 1:05d}")
    sec_usr_fname = factory.Sequence(lambda n: f"First{n + 1}")
    sec_usr_lname = factory.Sequence(lambda n: f"Last{n + 1}")
    sec_usr_pwd = "hashed_placeholder"  # noqa: S105
    sec_usr_type = "U"


class DjangoUserFactory(factory.django.DjangoModelFactory):
    """Factory for Django auth User records."""

    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"testuser{n + 1}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@test.example.com")
    first_name = factory.Sequence(lambda n: f"Test{n + 1}")
    last_name = "User"
    is_active = True
    password = factory.django.Password("testpassword123")  # noqa: S106
