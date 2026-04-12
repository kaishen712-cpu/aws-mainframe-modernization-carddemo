"""In-memory record cache for batch processing performance.

Performance Improvement 1 — avoids per-transaction database reads by caching
cross-reference and account lookups. The cache maintains a running balance
so that credit-limit validation for subsequent transactions on the same
account reflects previously posted (but not yet flushed) deltas.

Translated from the VSAM READ patterns in CBTRN02C.cbl paragraphs
1500-A-LOOKUP-XREF and 1500-B-LOOKUP-ACCT.
"""

from __future__ import annotations

from decimal import Decimal

from batch.models import Account, CardXref


class RecordCache:
    """Cache for cross-reference and account lookups during batch runs.

    Attributes:
        _xref_cache: Card-number -> CardXref mapping.
        _account_cache: Account-ID -> Account mapping.
    """

    def __init__(self) -> None:
        self._xref_cache: dict[str, CardXref] = {}
        self._account_cache: dict[str, Account] = {}

    # ------------------------------------------------------------------
    # Cross-reference lookups
    # ------------------------------------------------------------------

    def get_xref(self, card_num: str) -> CardXref | None:
        """Return the cross-reference for *card_num*, using cache if available.

        Translated from paragraph 1500-A-LOOKUP-XREF in CBTRN02C.cbl:
        ``READ XREF-FILE INTO CARD-XREF-RECORD``
        """
        if card_num in self._xref_cache:
            return self._xref_cache[card_num]
        try:
            xref = CardXref.objects.get(xref_card_num=card_num)
        except CardXref.DoesNotExist:
            return None
        self._xref_cache[card_num] = xref
        return xref

    # ------------------------------------------------------------------
    # Account lookups
    # ------------------------------------------------------------------

    def get_account(self, acct_id: str) -> Account | None:
        """Return the account for *acct_id*, using cache if available.

        Translated from paragraph 1500-B-LOOKUP-ACCT in CBTRN02C.cbl:
        ``READ ACCOUNT-FILE INTO ACCOUNT-RECORD``
        """
        if acct_id in self._account_cache:
            return self._account_cache[acct_id]
        try:
            account = Account.objects.get(acct_id=acct_id)
        except Account.DoesNotExist:
            return None
        self._account_cache[acct_id] = account
        return account

    # ------------------------------------------------------------------
    # In-memory balance updates
    # ------------------------------------------------------------------

    def apply_delta(self, acct_id: str, amount: Decimal) -> None:
        """Update the cached account's running balance after a transaction.

        CRITICAL: This keeps the in-memory balance consistent so that
        credit-limit checks for subsequent transactions on the same
        account reflect all previously posted deltas — not just the
        original DB balance.

        Translated from paragraph 2800-UPDATE-ACCOUNT-REC in CBTRN02C.cbl:
        ``ADD DALYTRAN-AMT TO ACCT-CURR-BAL``
        ``IF DALYTRAN-AMT >= 0 ADD ... TO ACCT-CURR-CYC-CREDIT``
        ``ELSE ADD ... TO ACCT-CURR-CYC-DEBIT``
        """
        account = self._account_cache.get(acct_id)
        if account is None:
            return
        account.acct_curr_bal += amount
        if amount >= Decimal("0"):
            account.acct_curr_cyc_credit += amount
        else:
            account.acct_curr_cyc_debit += amount

    # ------------------------------------------------------------------
    # Cache invalidation
    # ------------------------------------------------------------------

    def invalidate_account(self, acct_id: str) -> None:
        """Remove an account from the cache, forcing a DB re-read next time."""
        self._account_cache.pop(acct_id, None)

    def clear(self) -> None:
        """Clear all cached entries."""
        self._xref_cache.clear()
        self._account_cache.clear()

    # ------------------------------------------------------------------
    # Introspection helpers (useful for testing)
    # ------------------------------------------------------------------

    @property
    def xref_cache_size(self) -> int:
        """Number of cached cross-reference entries."""
        return len(self._xref_cache)

    @property
    def account_cache_size(self) -> int:
        """Number of cached account entries."""
        return len(self._account_cache)
