"""Unit tests for BatchAccountUpdater service — 90% coverage target.

Tests accumulation, atomic flush, failed delta preservation,
and banker's rounding.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from batch.models import Account
from batch.services.batch_account_updater import (
    BalanceDelta,
    BatchAccountUpdater,
)


@pytest.fixture()
def account(db: None) -> Account:
    """Create a synthetic account record."""
    return Account.objects.create(
        acct_id="00000000001",
        acct_active_status="Y",
        acct_curr_bal=Decimal("1000.00"),
        acct_credit_limit=Decimal("5000.00"),
        acct_curr_cyc_credit=Decimal("500.00"),
        acct_curr_cyc_debit=Decimal("200.00"),
        acct_group_id="GROUP1",
    )


@pytest.fixture()
def second_account(db: None) -> Account:
    """Create a second synthetic account."""
    return Account.objects.create(
        acct_id="00000000002",
        acct_active_status="Y",
        acct_curr_bal=Decimal("2000.00"),
        acct_credit_limit=Decimal("10000.00"),
        acct_curr_cyc_credit=Decimal("0.00"),
        acct_curr_cyc_debit=Decimal("0.00"),
        acct_group_id="GROUP1",
    )


class TestBalanceDelta:
    """Tests for the BalanceDelta dataclass."""

    def test_default_values(self) -> None:
        """All fields default to zero."""
        delta = BalanceDelta()
        assert delta.curr_bal_delta == Decimal("0")
        assert delta.curr_cyc_credit_delta == Decimal("0")
        assert delta.curr_cyc_debit_delta == Decimal("0")


class TestBatchAccountUpdaterAccumulate:
    """Tests for the accumulate method."""

    def test_accumulate_positive_amount(self) -> None:
        """Positive amount updates balance and credit deltas."""
        updater = BatchAccountUpdater()
        updater.accumulate("00000000001", Decimal("100.00"))

        delta = updater.get_delta("00000000001")
        assert delta is not None
        assert delta.curr_bal_delta == Decimal("100.00")
        assert delta.curr_cyc_credit_delta == Decimal("100.00")
        assert delta.curr_cyc_debit_delta == Decimal("0")

    def test_accumulate_negative_amount(self) -> None:
        """Negative amount updates balance and debit deltas."""
        updater = BatchAccountUpdater()
        updater.accumulate("00000000001", Decimal("-50.00"))

        delta = updater.get_delta("00000000001")
        assert delta is not None
        assert delta.curr_bal_delta == Decimal("-50.00")
        assert delta.curr_cyc_credit_delta == Decimal("0")
        assert delta.curr_cyc_debit_delta == Decimal("-50.00")

    def test_accumulate_multiple_transactions(self) -> None:
        """Multiple transactions on same account accumulate correctly."""
        updater = BatchAccountUpdater()
        updater.accumulate("00000000001", Decimal("100.00"))
        updater.accumulate("00000000001", Decimal("-30.00"))
        updater.accumulate("00000000001", Decimal("50.00"))

        delta = updater.get_delta("00000000001")
        assert delta is not None
        assert delta.curr_bal_delta == Decimal("120.00")
        assert delta.curr_cyc_credit_delta == Decimal("150.00")
        assert delta.curr_cyc_debit_delta == Decimal("-30.00")

    def test_accumulate_multiple_accounts(self) -> None:
        """Deltas tracked independently per account."""
        updater = BatchAccountUpdater()
        updater.accumulate("00000000001", Decimal("100.00"))
        updater.accumulate("00000000002", Decimal("200.00"))

        assert updater.pending_count == 2
        d1 = updater.get_delta("00000000001")
        d2 = updater.get_delta("00000000002")
        assert d1 is not None and d1.curr_bal_delta == Decimal("100.00")
        assert d2 is not None and d2.curr_bal_delta == Decimal("200.00")

    def test_accumulate_bankers_rounding(self) -> None:
        """Banker's rounding (ROUND_HALF_EVEN) applied to monetary values."""
        updater = BatchAccountUpdater()
        # 0.005 rounds to 0.00 (even), 0.015 rounds to 0.02 (even)
        updater.accumulate("00000000001", Decimal("0.005"))
        delta = updater.get_delta("00000000001")
        assert delta is not None
        assert delta.curr_bal_delta == Decimal("0.00")

    def test_pending_count(self) -> None:
        """Pending count reflects unflushed accounts."""
        updater = BatchAccountUpdater()
        assert updater.pending_count == 0
        updater.accumulate("00000000001", Decimal("10.00"))
        assert updater.pending_count == 1

    def test_get_delta_missing_returns_none(self) -> None:
        """Getting delta for non-existent account returns None."""
        updater = BatchAccountUpdater()
        assert updater.get_delta("99999999999") is None


class TestBatchAccountUpdaterFlush:
    """Tests for the flush method."""

    def test_flush_updates_account(self, account: Account) -> None:
        """Flush writes accumulated deltas to database."""
        updater = BatchAccountUpdater()
        updater.accumulate("00000000001", Decimal("150.00"))

        failed = updater.flush()
        assert failed == []

        account.refresh_from_db()
        assert account.acct_curr_bal == Decimal("1150.00")
        assert account.acct_curr_cyc_credit == Decimal("650.00")

    def test_flush_clears_successful_deltas(self, account: Account) -> None:
        """Successfully flushed deltas are removed."""
        updater = BatchAccountUpdater()
        updater.accumulate("00000000001", Decimal("100.00"))
        updater.flush()
        assert updater.pending_count == 0

    def test_flush_preserves_failed_deltas(self, db: None) -> None:
        """Failed deltas are preserved for retry."""
        updater = BatchAccountUpdater()
        updater.accumulate("99999999999", Decimal("100.00"))  # non-existent

        failed = updater.flush()
        assert "99999999999" in failed
        assert updater.pending_count == 1  # preserved for retry

    def test_flush_mixed_success_failure(self, account: Account) -> None:
        """Mixed: successful deltas cleared, failed preserved."""
        updater = BatchAccountUpdater()
        updater.accumulate("00000000001", Decimal("100.00"))  # exists
        updater.accumulate("99999999999", Decimal("50.00"))  # missing

        failed = updater.flush()
        assert "99999999999" in failed
        assert "00000000001" not in failed
        assert updater.pending_count == 1  # only failed remains

        account.refresh_from_db()
        assert account.acct_curr_bal == Decimal("1100.00")

    def test_flush_multiple_accounts(
        self, account: Account, second_account: Account
    ) -> None:
        """Flush updates multiple accounts correctly."""
        updater = BatchAccountUpdater()
        updater.accumulate("00000000001", Decimal("100.00"))
        updater.accumulate("00000000002", Decimal("-200.00"))

        failed = updater.flush()
        assert failed == []

        account.refresh_from_db()
        second_account.refresh_from_db()
        assert account.acct_curr_bal == Decimal("1100.00")
        assert second_account.acct_curr_bal == Decimal("1800.00")

    def test_flush_empty_no_error(self, db: None) -> None:
        """Flushing with no pending deltas succeeds with empty result."""
        updater = BatchAccountUpdater()
        failed = updater.flush()
        assert failed == []

    def test_flush_negative_delta(self, account: Account) -> None:
        """Negative deltas update debit correctly."""
        updater = BatchAccountUpdater()
        updater.accumulate("00000000001", Decimal("-75.00"))

        failed = updater.flush()
        assert failed == []

        account.refresh_from_db()
        assert account.acct_curr_bal == Decimal("925.00")
        assert account.acct_curr_cyc_debit == Decimal("125.00")


class TestBatchAccountUpdaterClear:
    """Tests for the clear method."""

    def test_clear_discards_pending(self) -> None:
        """Clear removes all pending deltas without flushing."""
        updater = BatchAccountUpdater()
        updater.accumulate("00000000001", Decimal("100.00"))
        updater.accumulate("00000000002", Decimal("200.00"))
        assert updater.pending_count == 2

        updater.clear()
        assert updater.pending_count == 0
