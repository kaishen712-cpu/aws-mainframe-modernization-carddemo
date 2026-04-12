"""Batched account balance updater for atomic flush operations.

Performance Improvement 2 — accumulates per-account balance deltas in
memory during batch processing, then writes them all in a single atomic
database transaction.  Failed deltas are preserved for retry.

Design from ``docs/execution_plan.md`` Performance Improvement 2 section.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import ROUND_HALF_EVEN, Decimal

from django.db import transaction as db_transaction

from batch.models import Account

logger = logging.getLogger(__name__)

# Banker's rounding context for monetary calculations
MONETARY_QUANTIZE = Decimal("0.01")


@dataclass
class BalanceDelta:
    """Accumulated balance changes for a single account.

    All fields use Decimal with banker's rounding (ROUND_HALF_EVEN)
    to match COBOL COMP-3 arithmetic behaviour.
    """

    curr_bal_delta: Decimal = field(default_factory=lambda: Decimal("0"))
    curr_cyc_credit_delta: Decimal = field(default_factory=lambda: Decimal("0"))
    curr_cyc_debit_delta: Decimal = field(default_factory=lambda: Decimal("0"))


class BatchAccountUpdater:
    """Accumulates balance deltas and flushes them atomically.

    Usage::

        updater = BatchAccountUpdater()
        updater.accumulate("00000000001", Decimal("150.00"))
        updater.accumulate("00000000001", Decimal("-25.50"))
        failed = updater.flush()

    Attributes:
        _deltas: Mapping of account-ID to accumulated BalanceDelta.
    """

    def __init__(self) -> None:
        self._deltas: dict[str, BalanceDelta] = {}

    # ------------------------------------------------------------------
    # Accumulate
    # ------------------------------------------------------------------

    def accumulate(self, acct_id: str, amount: Decimal) -> None:
        """Add a transaction amount to the running delta for *acct_id*.

        Positive amounts increase ``curr_cyc_credit_delta``; negative
        amounts increase ``curr_cyc_debit_delta``.  Both update
        ``curr_bal_delta``.

        Translated from paragraph 2800-UPDATE-ACCOUNT-REC in CBTRN02C.cbl:
        ``ADD DALYTRAN-AMT TO ACCT-CURR-BAL``
        """
        if acct_id not in self._deltas:
            self._deltas[acct_id] = BalanceDelta()

        delta = self._deltas[acct_id]
        delta.curr_bal_delta = (delta.curr_bal_delta + amount).quantize(
            MONETARY_QUANTIZE, rounding=ROUND_HALF_EVEN
        )
        if amount >= Decimal("0"):
            delta.curr_cyc_credit_delta = (
                delta.curr_cyc_credit_delta + amount
            ).quantize(MONETARY_QUANTIZE, rounding=ROUND_HALF_EVEN)
        else:
            delta.curr_cyc_debit_delta = (
                delta.curr_cyc_debit_delta + amount
            ).quantize(MONETARY_QUANTIZE, rounding=ROUND_HALF_EVEN)

    # ------------------------------------------------------------------
    # Flush
    # ------------------------------------------------------------------

    def flush(self) -> list[str]:
        """Write all accumulated deltas to the database atomically.

        Returns a list of account IDs that failed to update.  Successfully
        flushed deltas are removed; failed deltas are preserved for retry.

        Uses ``@db_transaction.atomic`` so either ALL updates in the
        batch succeed, or NONE do — matching COBOL's sequential REWRITE
        behaviour from paragraph 2800-UPDATE-ACCOUNT-REC in CBTRN02C.cbl.
        """
        failed_ids: list[str] = []
        succeeded_ids: list[str] = []

        for acct_id, delta in self._deltas.items():
            try:
                with db_transaction.atomic():
                    account = Account.objects.select_for_update().get(
                        acct_id=acct_id
                    )
                    account.acct_curr_bal = (
                        account.acct_curr_bal + delta.curr_bal_delta
                    ).quantize(MONETARY_QUANTIZE, rounding=ROUND_HALF_EVEN)
                    account.acct_curr_cyc_credit = (
                        account.acct_curr_cyc_credit
                        + delta.curr_cyc_credit_delta
                    ).quantize(MONETARY_QUANTIZE, rounding=ROUND_HALF_EVEN)
                    account.acct_curr_cyc_debit = (
                        account.acct_curr_cyc_debit
                        + delta.curr_cyc_debit_delta
                    ).quantize(MONETARY_QUANTIZE, rounding=ROUND_HALF_EVEN)
                    account.save()
                    succeeded_ids.append(acct_id)
            except Account.DoesNotExist:
                logger.error("Account %s not found during flush", acct_id)
                failed_ids.append(acct_id)
            except Exception:
                logger.exception("Failed to flush delta for account %s", acct_id)
                failed_ids.append(acct_id)

        # Only clear successfully written deltas
        for acct_id in succeeded_ids:
            del self._deltas[acct_id]

        return failed_ids

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def pending_count(self) -> int:
        """Number of accounts with pending (unflushed) deltas."""
        return len(self._deltas)

    def get_delta(self, acct_id: str) -> BalanceDelta | None:
        """Return the pending delta for *acct_id*, or None."""
        return self._deltas.get(acct_id)

    def clear(self) -> None:
        """Discard all pending deltas without flushing."""
        self._deltas.clear()
