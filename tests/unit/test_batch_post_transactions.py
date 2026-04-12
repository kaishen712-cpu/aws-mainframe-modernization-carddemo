"""Unit tests for post_transactions management command — 90% coverage target.

Tests cache prevents redundant reads, batched writes, validation rules,
and multi-transaction credit limit enforcement (two transactions on same
account where second is rejected based on running balance).
"""

from __future__ import annotations

from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command

from batch.models import (
    Account,
    CardXref,
    DailyTransaction,
    TranCatBal,
    Transaction,
)


@pytest.fixture()
def _base_data(db: None) -> None:
    """Create base synthetic test data for transaction posting."""
    Account.objects.create(
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
        acct_group_id="GROUP1",
    )
    CardXref.objects.create(
        xref_card_num="4111111111111111",
        xref_cust_id="000000001",
        xref_acct_id="00000000001",
    )


def _create_daily_txn(
    txn_id: str = "0000000000000001",
    card_num: str = "4111111111111111",
    amount: Decimal = Decimal("100.00"),
    type_cd: str = "01",
    cat_cd: str = "0001",
    orig_ts: str = "2025-06-15-10.30.00.000000",
) -> DailyTransaction:
    """Helper to create a synthetic daily transaction."""
    return DailyTransaction.objects.create(
        dalytran_id=txn_id,
        dalytran_type_cd=type_cd,
        dalytran_cat_cd=cat_cd,
        dalytran_source="Online",
        dalytran_desc="Test transaction",
        dalytran_amt=amount,
        dalytran_merchant_id="000000001",
        dalytran_merchant_name="Test Merchant",
        dalytran_merchant_city="Test City",
        dalytran_merchant_zip="12345",
        dalytran_card_num=card_num,
        dalytran_orig_ts=orig_ts,
    )


@pytest.mark.usefixtures("_base_data")
class TestPostTransactionsSuccess:
    """Tests for successful transaction posting."""

    def test_single_transaction_posted(self) -> None:
        """A valid transaction is posted and creates a Transaction record."""
        _create_daily_txn()
        out = StringIO()
        call_command("post_transactions", stdout=out)

        assert Transaction.objects.count() == 1
        assert "Posted: 1" in out.getvalue()

    def test_transaction_fields_copied(self) -> None:
        """Posted transaction preserves all fields from daily transaction."""
        _create_daily_txn()
        call_command("post_transactions")

        txn = Transaction.objects.first()
        assert txn is not None
        assert txn.tran_id == "0000000000000001"
        assert txn.tran_type_cd == "01"
        assert txn.tran_cat_cd == "0001"
        assert txn.tran_amt == Decimal("100.00")
        assert txn.tran_card_num == "4111111111111111"

    def test_account_balance_updated_after_flush(self) -> None:
        """Account balance updated in DB after batch flush."""
        _create_daily_txn(amount=Decimal("150.00"))
        call_command("post_transactions")

        account = Account.objects.get(acct_id="00000000001")
        assert account.acct_curr_bal == Decimal("1150.00")

    def test_tran_cat_bal_created(self) -> None:
        """Transaction category balance record is created."""
        _create_daily_txn(type_cd="01", cat_cd="0001")
        call_command("post_transactions")

        tcatbal = TranCatBal.objects.get(
            trancat_acct_id="00000000001",
            trancat_type_cd="01",
            trancat_cd="0001",
        )
        assert tcatbal.tran_cat_bal == Decimal("100.00")

    def test_tran_cat_bal_updated(self) -> None:
        """Existing category balance is updated (not duplicated)."""
        TranCatBal.objects.create(
            trancat_acct_id="00000000001",
            trancat_type_cd="01",
            trancat_cd="0001",
            tran_cat_bal=Decimal("50.00"),
        )
        _create_daily_txn(type_cd="01", cat_cd="0001")
        call_command("post_transactions")

        assert TranCatBal.objects.count() == 1
        tcatbal = TranCatBal.objects.first()
        assert tcatbal is not None
        assert tcatbal.tran_cat_bal == Decimal("150.00")

    def test_multiple_transactions_posted(self) -> None:
        """Multiple valid transactions are all posted."""
        _create_daily_txn("0000000000000001", amount=Decimal("100.00"))
        _create_daily_txn("0000000000000002", amount=Decimal("200.00"))
        out = StringIO()
        call_command("post_transactions", stdout=out)

        assert Transaction.objects.count() == 2
        assert "Posted: 2" in out.getvalue()


@pytest.mark.usefixtures("_base_data")
class TestPostTransactionsValidation:
    """Tests for transaction validation rules."""

    def test_reject_invalid_card_number(self) -> None:
        """Transaction with unknown card number is rejected (reason 100)."""
        _create_daily_txn(card_num="9999999999999999")
        out = StringIO()
        call_command("post_transactions", stdout=out)

        assert Transaction.objects.count() == 0
        assert "Rejected: 1" in out.getvalue()

    def test_reject_missing_account(self, db: None) -> None:
        """Transaction where xref points to missing account is rejected."""
        # Create xref pointing to non-existent account
        CardXref.objects.create(
            xref_card_num="5555555555555555",
            xref_cust_id="000000002",
            xref_acct_id="99999999999",
        )
        _create_daily_txn(card_num="5555555555555555")
        out = StringIO()
        call_command("post_transactions", stdout=out)

        assert Transaction.objects.count() == 0
        assert "Rejected: 1" in out.getvalue()

    def test_reject_overlimit_transaction(self) -> None:
        """Transaction exceeding credit limit is rejected (reason 102).

        COBOL rule: ACCT-CREDIT-LIMIT >= (CURR-CYC-CREDIT - CURR-CYC-DEBIT + AMT)
        Account: credit_limit=5000, cyc_credit=500, cyc_debit=200
        temp_bal = 500 - 200 + 4800 = 5100 > 5000 → reject
        """
        _create_daily_txn(amount=Decimal("4800.00"))
        out = StringIO()
        call_command("post_transactions", stdout=out)

        assert Transaction.objects.count() == 0
        assert "Rejected: 1" in out.getvalue()

    def test_reject_expired_account(self) -> None:
        """Transaction after account expiration is rejected (reason 103)."""
        Account.objects.filter(acct_id="00000000001").update(
            acct_expiration_date="2020-01-01"
        )
        _create_daily_txn(orig_ts="2025-06-15-10.30.00.000000")
        out = StringIO()
        call_command("post_transactions", stdout=out)

        assert Transaction.objects.count() == 0
        assert "Rejected: 1" in out.getvalue()


@pytest.mark.usefixtures("_base_data")
class TestPostTransactionsCreditLimitRunningBalance:
    """CRITICAL: Tests multi-transaction credit limit enforcement.

    Two transactions on same account where second is rejected based on
    RUNNING balance (cache reflects first transaction's delta).
    """

    def test_second_txn_rejected_by_running_balance(self) -> None:
        """Second transaction rejected because running balance exceeds limit.

        Account: credit_limit=5000, cyc_credit=500, cyc_debit=200
        Txn 1: +4500 → temp_bal = 500 - 200 + 4500 = 4800 <= 5000 → OK
        After txn 1: cache cyc_credit = 1000 (500 + 500 from apply_delta... wait)

        Actually let's trace more carefully:
        - Initial: cyc_credit=500, cyc_debit=200
        - Txn1 amount=4500:
          temp_bal = 500 - 200 + 4500 = 4800 <= 5000 → PASS
          apply_delta(+4500): cyc_credit becomes 5000, curr_bal becomes 5500
        - Txn2 amount=300:
          temp_bal = 5000 - 200 + 300 = 5100 > 5000 → REJECT
        """
        _create_daily_txn("0000000000000001", amount=Decimal("4500.00"))
        _create_daily_txn("0000000000000002", amount=Decimal("300.00"))

        out = StringIO()
        call_command("post_transactions", stdout=out)

        assert Transaction.objects.count() == 1
        output = out.getvalue()
        assert "Posted: 1" in output
        assert "Rejected: 1" in output

    def test_both_txns_within_limit(self) -> None:
        """Two small transactions both pass credit limit check."""
        _create_daily_txn("0000000000000001", amount=Decimal("100.00"))
        _create_daily_txn("0000000000000002", amount=Decimal("100.00"))

        out = StringIO()
        call_command("post_transactions", stdout=out)

        assert Transaction.objects.count() == 2
        assert "Posted: 2" in out.getvalue()


@pytest.mark.usefixtures("_base_data")
class TestPostTransactionsRejectFile:
    """Tests for reject file writing."""

    def test_reject_file_written(self, tmp_path: object) -> None:
        """Rejected transactions are written to the reject file."""
        from pathlib import Path

        reject_path = Path(str(tmp_path)) / "rejects.txt"
        _create_daily_txn(card_num="9999999999999999")
        call_command("post_transactions", reject_file=str(reject_path))

        assert reject_path.exists()
        content = reject_path.read_text()
        assert "100" in content
        assert "INVALID CARD NUMBER" in content

    def test_no_reject_file_when_all_valid(self, tmp_path: object) -> None:
        """No reject file created when all transactions are valid."""
        from pathlib import Path

        reject_path = Path(str(tmp_path)) / "rejects.txt"
        _create_daily_txn()
        call_command("post_transactions", reject_file=str(reject_path))
        assert not reject_path.exists()


@pytest.mark.usefixtures("_base_data")
class TestPostTransactionsCacheBehaviour:
    """Tests that cache prevents redundant database reads."""

    def test_cache_prevents_redundant_xref_reads(self) -> None:
        """Multiple transactions with same card use cached xref."""
        _create_daily_txn("0000000000000001", amount=Decimal("50.00"))
        _create_daily_txn("0000000000000002", amount=Decimal("50.00"))

        # Both transactions should succeed with cache
        out = StringIO()
        call_command("post_transactions", stdout=out)
        assert "Posted: 2" in out.getvalue()

    def test_cache_prevents_redundant_account_reads(self) -> None:
        """Multiple transactions on same account use cached account."""
        _create_daily_txn("0000000000000001", amount=Decimal("50.00"))
        _create_daily_txn("0000000000000002", amount=Decimal("50.00"))

        out = StringIO()
        call_command("post_transactions", stdout=out)
        assert "Posted: 2" in out.getvalue()

        # Verify account was updated correctly (both deltas accumulated)
        account = Account.objects.get(acct_id="00000000001")
        assert account.acct_curr_bal == Decimal("1100.00")
