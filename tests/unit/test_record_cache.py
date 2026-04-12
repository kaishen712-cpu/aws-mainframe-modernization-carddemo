"""Unit tests for RecordCache service — 90% coverage target.

Tests cache prevents redundant reads, handles missing records,
and maintains running balance via apply_delta.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from batch.models import Account, CardXref
from batch.services.record_cache import RecordCache


@pytest.fixture()
def xref(db: None) -> CardXref:
    """Create a synthetic cross-reference record."""
    return CardXref.objects.create(
        xref_card_num="4111111111111111",
        xref_cust_id="000000001",
        xref_acct_id="00000000001",
    )


@pytest.fixture()
def account(db: None) -> Account:
    """Create a synthetic account record."""
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
        acct_group_id="GROUP1",
    )


class TestRecordCacheXref:
    """Tests for cross-reference caching."""

    def test_get_xref_returns_record(self, xref: CardXref) -> None:
        """First lookup fetches from DB."""
        cache = RecordCache()
        result = cache.get_xref("4111111111111111")
        assert result is not None
        assert result.xref_acct_id == "00000000001"

    def test_get_xref_caches_result(self, xref: CardXref) -> None:
        """Second lookup uses cache — no extra DB query."""
        cache = RecordCache()
        cache.get_xref("4111111111111111")
        assert cache.xref_cache_size == 1
        # Second call returns cached value
        result = cache.get_xref("4111111111111111")
        assert result is not None
        assert cache.xref_cache_size == 1

    def test_get_xref_returns_none_for_missing(self, db: None) -> None:
        """Missing card number returns None."""
        cache = RecordCache()
        result = cache.get_xref("9999999999999999")
        assert result is None

    def test_get_xref_missing_not_cached(self, db: None) -> None:
        """Missing lookups are NOT cached (allow retry after insert)."""
        cache = RecordCache()
        cache.get_xref("9999999999999999")
        assert cache.xref_cache_size == 0


class TestRecordCacheAccount:
    """Tests for account caching."""

    def test_get_account_returns_record(self, account: Account) -> None:
        """First lookup fetches from DB."""
        cache = RecordCache()
        result = cache.get_account("00000000001")
        assert result is not None
        assert result.acct_curr_bal == Decimal("1000.00")

    def test_get_account_caches_result(self, account: Account) -> None:
        """Second lookup uses cache."""
        cache = RecordCache()
        cache.get_account("00000000001")
        assert cache.account_cache_size == 1
        result = cache.get_account("00000000001")
        assert result is not None
        assert cache.account_cache_size == 1

    def test_get_account_returns_none_for_missing(self, db: None) -> None:
        """Missing account returns None."""
        cache = RecordCache()
        result = cache.get_account("99999999999")
        assert result is None

    def test_get_account_missing_not_cached(self, db: None) -> None:
        """Missing account lookups are NOT cached."""
        cache = RecordCache()
        cache.get_account("99999999999")
        assert cache.account_cache_size == 0


class TestRecordCacheApplyDelta:
    """Tests for in-memory balance updates — CRITICAL for credit limit checks."""

    def test_apply_delta_positive(self, account: Account) -> None:
        """Positive delta increases balance and cycle credit."""
        cache = RecordCache()
        cache.get_account("00000000001")
        cache.apply_delta("00000000001", Decimal("100.00"))

        cached = cache.get_account("00000000001")
        assert cached is not None
        assert cached.acct_curr_bal == Decimal("1100.00")
        assert cached.acct_curr_cyc_credit == Decimal("600.00")

    def test_apply_delta_negative(self, account: Account) -> None:
        """Negative delta decreases balance and increases cycle debit."""
        cache = RecordCache()
        cache.get_account("00000000001")
        cache.apply_delta("00000000001", Decimal("-50.00"))

        cached = cache.get_account("00000000001")
        assert cached is not None
        assert cached.acct_curr_bal == Decimal("950.00")
        assert cached.acct_curr_cyc_debit == Decimal("150.00")

    def test_apply_delta_running_balance(self, account: Account) -> None:
        """Multiple deltas accumulate correctly (running balance)."""
        cache = RecordCache()
        cache.get_account("00000000001")
        cache.apply_delta("00000000001", Decimal("100.00"))
        cache.apply_delta("00000000001", Decimal("-30.00"))
        cache.apply_delta("00000000001", Decimal("50.00"))

        cached = cache.get_account("00000000001")
        assert cached is not None
        assert cached.acct_curr_bal == Decimal("1120.00")

    def test_apply_delta_uncached_account_no_error(self, db: None) -> None:
        """Applying delta to uncached account does nothing (no crash)."""
        cache = RecordCache()
        cache.apply_delta("99999999999", Decimal("100.00"))
        assert cache.account_cache_size == 0

    def test_apply_delta_zero_amount(self, account: Account) -> None:
        """Zero delta treated as positive (>= 0)."""
        cache = RecordCache()
        cache.get_account("00000000001")
        original_credit = Decimal("500.00")
        cache.apply_delta("00000000001", Decimal("0.00"))

        cached = cache.get_account("00000000001")
        assert cached is not None
        assert cached.acct_curr_bal == Decimal("1000.00")
        assert cached.acct_curr_cyc_credit == original_credit


class TestRecordCacheInvalidation:
    """Tests for cache invalidation."""

    def test_invalidate_account(self, account: Account) -> None:
        """Invalidation removes account from cache."""
        cache = RecordCache()
        cache.get_account("00000000001")
        assert cache.account_cache_size == 1
        cache.invalidate_account("00000000001")
        assert cache.account_cache_size == 0

    def test_invalidate_missing_account_no_error(self, db: None) -> None:
        """Invalidating a non-cached account does nothing."""
        cache = RecordCache()
        cache.invalidate_account("99999999999")
        assert cache.account_cache_size == 0

    def test_clear_empties_all_caches(
        self, xref: CardXref, account: Account
    ) -> None:
        """Clear removes all cached entries."""
        cache = RecordCache()
        cache.get_xref("4111111111111111")
        cache.get_account("00000000001")
        assert cache.xref_cache_size == 1
        assert cache.account_cache_size == 1

        cache.clear()
        assert cache.xref_cache_size == 0
        assert cache.account_cache_size == 0
