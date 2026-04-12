"""Integration tests for the batch processing pipeline.

End-to-end: load sample data -> post transactions -> calculate interest
-> generate statements.

All test data is synthetic — NEVER use real customer data.
SECURITY: Never log account numbers, card numbers, or transaction
amounts in plain text (CPS 234 requirement).
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest

from batch.models import (
    Account,
    Card,
    CardXref,
    DailyTransaction,
    DisclosureGroup,
    TranCatBal,
    TransactionCategory,
    TransactionType,
)
from batch.services.batch_account_updater import BatchAccountUpdater
from batch.services.record_cache import RecordCache

# ---------------------------------------------------------------------------
# Fixtures — synthetic batch pipeline data
# ---------------------------------------------------------------------------


@pytest.fixture()
def batch_data(db: None) -> dict[str, object]:
    """Set up complete synthetic data for a batch pipeline run."""
    account = Account.objects.create(
        acct_id="00000000001",
        acct_active_status="Y",
        acct_curr_bal=Decimal("1000.00"),
        acct_credit_limit=Decimal("5000.00"),
        acct_cash_credit_limit=Decimal("1000.00"),
        acct_open_date="2020-01-01",
        acct_expiration_date="2030-12-31",
        acct_reissue_date="2025-01-01",
        acct_curr_cyc_credit=Decimal("0.00"),
        acct_curr_cyc_debit=Decimal("0.00"),
        acct_addr_zip="10001",
        acct_group_id="GROUP1",
    )
    account_2 = Account.objects.create(
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
    card = Card.objects.create(
        card_num="4111111111111111",
        card_acct_id="00000000001",
        card_cvv_cd="123",
        card_embossed_name="TEST USER ONE",
        card_expiration_date="2030-12-31",
        card_active_status="Y",
    )
    card_2 = Card.objects.create(
        card_num="4222222222222222",
        card_acct_id="00000000002",
        card_cvv_cd="456",
        card_embossed_name="TEST USER TWO",
        card_expiration_date="2029-06-15",
        card_active_status="Y",
    )
    xref = CardXref.objects.create(
        xref_card_num="4111111111111111",
        xref_cust_id="000000001",
        xref_acct_id="00000000001",
    )
    xref_2 = CardXref.objects.create(
        xref_card_num="4222222222222222",
        xref_cust_id="000000002",
        xref_acct_id="00000000002",
    )
    tran_type = TransactionType.objects.create(
        tran_type="01",
        tran_type_desc="PURCHASE",
    )
    tran_cat = TransactionCategory.objects.create(
        tran_type_cd="01",
        tran_cat_cd="5001",
        tran_cat_type_desc="RETAIL PURCHASE",
    )
    disclosure = DisclosureGroup.objects.create(
        dis_acct_group_id="GROUP1",
        dis_tran_type_cd="01",
        dis_tran_cat_cd="5001",
        dis_int_rate=Decimal("18.99"),
    )
    tran_cat_bal = TranCatBal.objects.create(
        trancat_acct_id="00000000001",
        trancat_type_cd="01",
        trancat_cd="5001",
        tran_cat_bal=Decimal("0.00"),
    )
    tran_cat_bal_2 = TranCatBal.objects.create(
        trancat_acct_id="00000000002",
        trancat_type_cd="01",
        trancat_cd="5001",
        tran_cat_bal=Decimal("0.00"),
    )

    # Daily transactions to post
    dtxn1 = DailyTransaction.objects.create(
        dalytran_id="0000000000000001",
        dalytran_type_cd="01",
        dalytran_cat_cd="5001",
        dalytran_source="BATCH",
        dalytran_desc="PURCHASE AT STORE A",
        dalytran_amt=Decimal("150.00"),
        dalytran_merchant_id="000000001",
        dalytran_merchant_name="STORE A",
        dalytran_merchant_city="NEW YORK",
        dalytran_merchant_zip="10001",
        dalytran_card_num="4111111111111111",
        dalytran_orig_ts="2025-01-15-08.00.00.000000",
    )
    dtxn2 = DailyTransaction.objects.create(
        dalytran_id="0000000000000002",
        dalytran_type_cd="01",
        dalytran_cat_cd="5001",
        dalytran_source="BATCH",
        dalytran_desc="PURCHASE AT STORE B",
        dalytran_amt=Decimal("250.00"),
        dalytran_merchant_id="000000002",
        dalytran_merchant_name="STORE B",
        dalytran_merchant_city="LOS ANGELES",
        dalytran_merchant_zip="90210",
        dalytran_card_num="4111111111111111",
        dalytran_orig_ts="2025-01-15-09.00.00.000000",
    )
    dtxn3 = DailyTransaction.objects.create(
        dalytran_id="0000000000000003",
        dalytran_type_cd="01",
        dalytran_cat_cd="5001",
        dalytran_source="BATCH",
        dalytran_desc="PURCHASE AT STORE C",
        dalytran_amt=Decimal("500.00"),
        dalytran_merchant_id="000000003",
        dalytran_merchant_name="STORE C",
        dalytran_merchant_city="CHICAGO",
        dalytran_merchant_zip="60601",
        dalytran_card_num="4222222222222222",
        dalytran_orig_ts="2025-01-15-10.00.00.000000",
    )

    return {
        "accounts": [account, account_2],
        "cards": [card, card_2],
        "xrefs": [xref, xref_2],
        "daily_transactions": [dtxn1, dtxn2, dtxn3],
        "disclosure": disclosure,
        "tran_type": tran_type,
        "tran_cat": tran_cat,
        "tran_cat_bals": [tran_cat_bal, tran_cat_bal_2],
    }


# ---------------------------------------------------------------------------
# RecordCache integration tests
# ---------------------------------------------------------------------------


class TestRecordCachePreventsRedundantReads:
    """Verify RecordCache prevents redundant database reads."""

    def test_cache_reuses_xref_across_lookups(self, batch_data: dict[str, object]) -> None:
        """Multiple xref lookups for the same card hit DB only once."""
        cache = RecordCache()

        with patch.object(CardXref.objects, "get", wraps=CardXref.objects.get) as mock_get:
            cache.get_xref("4111111111111111")
            cache.get_xref("4111111111111111")
            cache.get_xref("4111111111111111")

            assert mock_get.call_count == 1

    def test_cache_reuses_account_across_lookups(self, batch_data: dict[str, object]) -> None:
        """Multiple account lookups for the same acct_id hit DB only once."""
        cache = RecordCache()

        with patch.object(Account.objects, "get", wraps=Account.objects.get) as mock_get:
            cache.get_account("00000000001")
            cache.get_account("00000000001")
            cache.get_account("00000000001")

            assert mock_get.call_count == 1

    def test_cache_different_keys_hit_db_separately(self, batch_data: dict[str, object]) -> None:
        """Different card numbers each require one DB hit."""
        cache = RecordCache()

        with patch.object(CardXref.objects, "get", wraps=CardXref.objects.get) as mock_get:
            cache.get_xref("4111111111111111")
            cache.get_xref("4222222222222222")

            assert mock_get.call_count == 2


# ---------------------------------------------------------------------------
# BatchAccountUpdater integration tests
# ---------------------------------------------------------------------------


class TestBatchAccountUpdaterWritesOncePerAccount:
    """Verify BatchAccountUpdater writes once per account, not per transaction."""

    def test_multiple_transactions_single_write(self, batch_data: dict[str, object]) -> None:
        """Three transactions on two accounts produce exactly two DB writes."""
        updater = BatchAccountUpdater()

        # Simulate posting three transactions
        updater.accumulate("00000000001", Decimal("150.00"))
        updater.accumulate("00000000001", Decimal("250.00"))
        updater.accumulate("00000000002", Decimal("500.00"))

        # Three accumulates but only two accounts => flush writes twice
        assert updater.pending_count == 2

        failed = updater.flush()
        assert failed == []
        # All deltas flushed — no pending accounts remain
        assert updater.pending_count == 0

        # Verify balances to confirm exactly one write per account
        acct1 = Account.objects.get(acct_id="00000000001")
        acct2 = Account.objects.get(acct_id="00000000002")
        assert acct1.acct_curr_bal == Decimal("1400.00")
        assert acct2.acct_curr_bal == Decimal("3000.00")

    def test_accumulated_balance_correct(self, batch_data: dict[str, object]) -> None:
        """Account balances reflect the sum of all transactions."""
        updater = BatchAccountUpdater()

        updater.accumulate("00000000001", Decimal("150.00"))
        updater.accumulate("00000000001", Decimal("250.00"))
        updater.accumulate("00000000002", Decimal("500.00"))

        failed = updater.flush()
        assert failed == []

        acct1 = Account.objects.get(acct_id="00000000001")
        acct2 = Account.objects.get(acct_id="00000000002")

        # Account 1: 1000 + 150 + 250 = 1400
        assert acct1.acct_curr_bal == Decimal("1400.00")
        assert acct1.acct_curr_cyc_credit == Decimal("400.00")

        # Account 2: 2500 + 500 = 3000
        assert acct2.acct_curr_bal == Decimal("3000.00")
        assert acct2.acct_curr_cyc_credit == Decimal("500.00")


# ---------------------------------------------------------------------------
# Decimal precision tests
# ---------------------------------------------------------------------------


class TestDecimalPrecision:
    """Validate Decimal precision matches expected output."""

    def test_banker_rounding_on_accumulate(self, batch_data: dict[str, object]) -> None:
        """Banker's rounding (ROUND_HALF_EVEN) applied during accumulation."""
        updater = BatchAccountUpdater()

        # 0.005 rounds to 0.00 with ROUND_HALF_EVEN
        updater.accumulate("00000000001", Decimal("0.005"))
        delta = updater.get_delta("00000000001")
        assert delta is not None
        assert delta.curr_bal_delta == Decimal("0.00")

        # 0.015 rounds to 0.02 with ROUND_HALF_EVEN
        updater.accumulate("00000000001", Decimal("0.015"))
        delta = updater.get_delta("00000000001")
        assert delta is not None
        assert delta.curr_bal_delta == Decimal("0.02")

    def test_large_transaction_precision(self, batch_data: dict[str, object]) -> None:
        """Large monetary values maintain precision."""
        updater = BatchAccountUpdater()

        updater.accumulate("00000000001", Decimal("999999999.99"))
        failed = updater.flush()
        assert failed == []

        acct = Account.objects.get(acct_id="00000000001")
        assert acct.acct_curr_bal == Decimal("1000000999.99")

    def test_negative_balance_precision(self, batch_data: dict[str, object]) -> None:
        """Negative balance deltas maintain precision."""
        updater = BatchAccountUpdater()

        updater.accumulate("00000000001", Decimal("-123.45"))
        updater.accumulate("00000000001", Decimal("-67.89"))

        failed = updater.flush()
        assert failed == []

        acct = Account.objects.get(acct_id="00000000001")
        # 1000 - 123.45 - 67.89 = 808.66
        assert acct.acct_curr_bal == Decimal("808.66")


# ---------------------------------------------------------------------------
# End-to-end batch pipeline simulation
# ---------------------------------------------------------------------------


class TestBatchPipelineEndToEnd:
    """End-to-end test: load data -> post transactions -> verify balances."""

    def test_full_pipeline_simulation(self, batch_data: dict[str, object]) -> None:
        """Simulate the full batch pipeline with cache and updater."""
        cache = RecordCache()
        updater = BatchAccountUpdater()

        daily_txns = DailyTransaction.objects.all().order_by("dalytran_id")

        for dtxn in daily_txns:
            # Step 1: Look up cross-reference (cached)
            xref = cache.get_xref(dtxn.dalytran_card_num)
            assert xref is not None

            # Step 2: Look up account (cached)
            account = cache.get_account(xref.xref_acct_id)
            assert account is not None

            # Step 3: Validate account is active
            assert account.acct_active_status == "Y"

            # Step 4: Accumulate balance delta (not writing to DB yet)
            updater.accumulate(xref.xref_acct_id, dtxn.dalytran_amt)

            # Step 5: Apply delta to cache for credit-limit checks
            cache.apply_delta(xref.xref_acct_id, dtxn.dalytran_amt)

        # Step 6: Verify cache prevented redundant reads
        # 3 txns on 2 cards -> 2 xref reads, 2 account reads
        assert cache.xref_cache_size == 2
        assert cache.account_cache_size == 2

        # Step 7: Verify running balance in cache
        cached_acct1 = cache.get_account("00000000001")
        assert cached_acct1 is not None
        assert cached_acct1.acct_curr_bal == Decimal("1400.00")

        cached_acct2 = cache.get_account("00000000002")
        assert cached_acct2 is not None
        assert cached_acct2.acct_curr_bal == Decimal("3000.00")

        # Step 8: Flush all updates atomically
        failed = updater.flush()
        assert failed == []
        assert updater.pending_count == 0

        # Step 9: Verify database state
        acct1 = Account.objects.get(acct_id="00000000001")
        acct2 = Account.objects.get(acct_id="00000000002")

        assert acct1.acct_curr_bal == Decimal("1400.00")
        assert acct1.acct_curr_cyc_credit == Decimal("400.00")

        assert acct2.acct_curr_bal == Decimal("3000.00")
        assert acct2.acct_curr_cyc_credit == Decimal("500.00")

    def test_pipeline_with_credit_limit_check(self, batch_data: dict[str, object]) -> None:
        """Credit limit check uses running balance, not original DB balance.

        Two transactions on the same account where the second should be
        rejected based on the running balance from the first.
        """
        cache = RecordCache()
        updater = BatchAccountUpdater()

        # Account 1 has $1000 balance and $5000 credit limit
        # Available credit = 5000 - 1000 = 4000

        # Transaction 1: $3500 purchase (should pass: 4000 available)
        xref = cache.get_xref("4111111111111111")
        assert xref is not None
        acct = cache.get_account(xref.xref_acct_id)
        assert acct is not None

        txn1_amount = Decimal("3500.00")
        available_credit = acct.acct_credit_limit - acct.acct_curr_bal
        assert txn1_amount <= available_credit  # 3500 <= 4000

        updater.accumulate(xref.xref_acct_id, txn1_amount)
        cache.apply_delta(xref.xref_acct_id, txn1_amount)

        # Transaction 2: $1000 purchase (should fail: only 500 available)
        acct_updated = cache.get_account(xref.xref_acct_id)
        assert acct_updated is not None

        txn2_amount = Decimal("1000.00")
        available_credit = acct_updated.acct_credit_limit - acct_updated.acct_curr_bal
        # Running balance: 1000 + 3500 = 4500; available: 5000 - 4500 = 500
        assert available_credit == Decimal("500.00")
        assert txn2_amount > available_credit  # 1000 > 500 -> REJECT

        # Flush only the first transaction
        failed = updater.flush()
        assert failed == []

        acct1 = Account.objects.get(acct_id="00000000001")
        assert acct1.acct_curr_bal == Decimal("4500.00")
