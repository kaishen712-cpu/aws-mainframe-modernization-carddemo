"""Unit tests for calc_interest management command — 90% coverage target.

Tests interest calculation, disclosure group lookup with fallback,
transaction record creation, and account balance updates.
"""

from __future__ import annotations

from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command

from batch.models import (
    Account,
    CardXref,
    DisclosureGroup,
    TranCatBal,
    Transaction,
)


@pytest.fixture()
def _interest_data(db: None) -> None:
    """Create synthetic test data for interest calculation."""
    Account.objects.create(
        acct_id="00000000001",
        acct_active_status="Y",
        acct_curr_bal=Decimal("1000.00"),
        acct_credit_limit=Decimal("5000.00"),
        acct_curr_cyc_credit=Decimal("0.00"),
        acct_curr_cyc_debit=Decimal("0.00"),
        acct_group_id="GROUP1",
    )
    CardXref.objects.create(
        xref_card_num="4111111111111111",
        xref_cust_id="000000001",
        xref_acct_id="00000000001",
    )
    TranCatBal.objects.create(
        trancat_acct_id="00000000001",
        trancat_type_cd="01",
        trancat_cd="0001",
        tran_cat_bal=Decimal("1200.00"),
    )
    # HUMAN REVIEW: hardcoded interest rate for testing (18% annual)
    DisclosureGroup.objects.create(
        dis_acct_group_id="GROUP1",
        dis_tran_type_cd="01",
        dis_tran_cat_cd="0001",
        dis_int_rate=Decimal("18.00"),
    )


@pytest.mark.usefixtures("_interest_data")
class TestCalcInterestBasic:
    """Basic interest calculation tests."""

    def test_interest_calculated(self) -> None:
        """Interest transaction created with correct amount.

        COBOL formula: (TRAN-CAT-BAL * DIS-INT-RATE) / 1200
        = (1200.00 * 18.00) / 1200 = 18.00
        """
        out = StringIO()
        call_command("calc_interest", date="2025-06-15", stdout=out)

        assert Transaction.objects.count() == 1
        txn = Transaction.objects.first()
        assert txn is not None
        assert txn.tran_amt == Decimal("18.00")
        assert "Interest transactions: 1" in out.getvalue()

    def test_interest_transaction_fields(self) -> None:
        """Interest transaction has correct type/category/source."""
        call_command("calc_interest", date="2025-06-15")
        txn = Transaction.objects.first()
        assert txn is not None
        # Translated from CBACT04C.cbl paragraph 1300-B-WRITE-TX
        assert txn.tran_type_cd == "01"
        assert txn.tran_cat_cd == "05"
        assert txn.tran_source == "System"
        assert "Int. for a/c" in txn.tran_desc

    def test_account_balance_updated(self) -> None:
        """Account balance reflects posted interest."""
        call_command("calc_interest", date="2025-06-15")
        account = Account.objects.get(acct_id="00000000001")
        # Original 1000 + 18 interest = 1018
        assert account.acct_curr_bal == Decimal("1018.00")

    def test_account_cycle_credit_updated(self) -> None:
        """Account cycle credit reflects posted interest."""
        call_command("calc_interest", date="2025-06-15")
        account = Account.objects.get(acct_id="00000000001")
        assert account.acct_curr_cyc_credit == Decimal("18.00")


@pytest.mark.usefixtures("_interest_data")
class TestCalcInterestDisclosureGroupFallback:
    """Tests for disclosure group lookup with DEFAULT fallback."""

    def test_fallback_to_default_group(self) -> None:
        """Uses DEFAULT group when account's group rate not found.

        Translated from paragraph 1200-A-GET-DEFAULT-INT-RATE in CBACT04C.cbl.
        """
        # Remove account-specific rate
        DisclosureGroup.objects.filter(dis_acct_group_id="GROUP1").delete()
        # Add DEFAULT rate
        # HUMAN REVIEW: hardcoded default interest rate
        DisclosureGroup.objects.create(
            dis_acct_group_id="DEFAULT",
            dis_tran_type_cd="01",
            dis_tran_cat_cd="0001",
            dis_int_rate=Decimal("12.00"),
        )

        call_command("calc_interest", date="2025-06-15")
        txn = Transaction.objects.first()
        assert txn is not None
        # (1200 * 12) / 1200 = 12.00
        assert txn.tran_amt == Decimal("12.00")

    def test_no_rate_found_skips_category(self) -> None:
        """Category with no rate (account or DEFAULT) is skipped."""
        DisclosureGroup.objects.all().delete()

        out = StringIO()
        call_command("calc_interest", date="2025-06-15", stdout=out)

        assert Transaction.objects.count() == 0
        assert "Accounts processed: 0" in out.getvalue()


class TestCalcInterestMultipleAccounts:
    """Tests for multi-account interest processing."""

    def test_multiple_accounts_processed(self, db: None) -> None:
        """Interest calculated for each account independently."""
        for i in range(1, 3):
            acct_id = f"{i:011d}"
            Account.objects.create(
                acct_id=acct_id,
                acct_active_status="Y",
                acct_curr_bal=Decimal("1000.00"),
                acct_credit_limit=Decimal("5000.00"),
                acct_group_id="GROUP1",
            )
            CardXref.objects.create(
                xref_card_num=f"411111111111{i:04d}",
                xref_cust_id=f"{i:09d}",
                xref_acct_id=acct_id,
            )
            TranCatBal.objects.create(
                trancat_acct_id=acct_id,
                trancat_type_cd="01",
                trancat_cd="0001",
                tran_cat_bal=Decimal("600.00"),
            )

        DisclosureGroup.objects.create(
            dis_acct_group_id="GROUP1",
            dis_tran_type_cd="01",
            dis_tran_cat_cd="0001",
            dis_int_rate=Decimal("18.00"),
        )

        out = StringIO()
        call_command("calc_interest", date="2025-06-15", stdout=out)

        assert Transaction.objects.count() == 2
        assert "Accounts processed: 2" in out.getvalue()

    def test_empty_database_no_errors(self, db: None) -> None:
        """No errors when database is empty."""
        out = StringIO()
        call_command("calc_interest", date="2025-06-15", stdout=out)
        assert "Accounts processed: 0" in out.getvalue()


@pytest.mark.usefixtures("_interest_data")
class TestCalcInterestMultipleCategories:
    """Tests for accounts with multiple category balances."""

    def test_multiple_categories_summed(self) -> None:
        """Interest from multiple categories sums for account update."""
        # Add second category balance
        TranCatBal.objects.create(
            trancat_acct_id="00000000001",
            trancat_type_cd="02",
            trancat_cd="0002",
            tran_cat_bal=Decimal("600.00"),
        )
        DisclosureGroup.objects.create(
            dis_acct_group_id="GROUP1",
            dis_tran_type_cd="02",
            dis_tran_cat_cd="0002",
            dis_int_rate=Decimal("24.00"),
        )

        call_command("calc_interest", date="2025-06-15")

        # Cat 1: (1200 * 18) / 1200 = 18.00
        # Cat 2: (600 * 24) / 1200 = 12.00
        # Total interest: 30.00
        account = Account.objects.get(acct_id="00000000001")
        assert account.acct_curr_bal == Decimal("1030.00")
        assert Transaction.objects.count() == 2


@pytest.mark.usefixtures("_interest_data")
class TestCalcInterestDateHandling:
    """Tests for date parameter handling."""

    def test_default_date_used(self) -> None:
        """Default date (today) used when not specified."""
        out = StringIO()
        call_command("calc_interest", stdout=out)
        assert "Interest transactions: 1" in out.getvalue()

    def test_custom_date_in_tran_id(self) -> None:
        """Custom date appears in generated transaction ID."""
        call_command("calc_interest", date="2025-06-15")
        txn = Transaction.objects.first()
        assert txn is not None
        assert txn.tran_id.startswith("2025-06-15")
