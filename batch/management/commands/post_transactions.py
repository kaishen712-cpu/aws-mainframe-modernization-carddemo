"""Daily transaction posting — batch management command.

Translated from CBTRN02C.cbl (732 lines).
Uses BOTH performance improvements:
- RecordCache for cross-reference and account lookups
- BatchAccountUpdater for atomic balance updates

Original COBOL program flow:
1. Open 6 files (DALYTRAN, TRANSACT, XREF, DALYREJS, ACCOUNT, TCATBAL)
2. Read daily transactions sequentially
3. For each transaction: validate -> post -> update balances
4. Write rejected transactions to reject file
5. Close all files

CRITICAL: Credit limit checks use the cache's RUNNING balance, not the
original DB balance, so that multiple transactions on the same account
are validated correctly.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandParser

from batch.models import DailyTransaction, TranCatBal, Transaction
from batch.services.batch_account_updater import BatchAccountUpdater
from batch.services.record_cache import RecordCache

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Post daily transactions — translated from CBTRN02C.cbl."""

    help = "Post daily transactions to accounts (CBTRN02C.cbl)"

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command-line arguments."""
        parser.add_argument(
            "--reject-file",
            type=str,
            default="",
            help="Path to write rejected transactions (default: none)",
        )

    def handle(self, *args: object, **options: object) -> None:
        """Execute the daily transaction posting batch process.

        Translated from PROCEDURE DIVISION of CBTRN02C.cbl.
        Main loop: paragraphs 1000-DALYTRAN-READ through 2900-WRITE-TRANSACTION-FILE.
        """
        reject_file_path = str(options.get("reject_file", "") or "")
        cache = RecordCache()
        updater = BatchAccountUpdater()

        posted_count = 0
        rejected_count = 0
        reject_lines: list[str] = []

        daily_transactions = DailyTransaction.objects.all().order_by("dalytran_id")

        for daily_txn in daily_transactions:
            fail_reason, fail_desc = self._validate_transaction(daily_txn, cache)

            if fail_reason != 0:
                # Translated from paragraph 2500-WRITE-REJECT-REC
                rejected_count += 1
                reject_lines.append(f"{daily_txn.dalytran_id}|{fail_reason}|{fail_desc}")
                continue

            self._post_transaction(daily_txn, cache, updater)
            posted_count += 1

        # Flush all accumulated balance updates atomically
        failed_ids = updater.flush()

        # Write reject file if requested
        # Translated from DALYREJS file operations in CBTRN02C.cbl
        if reject_file_path and reject_lines:
            self._write_reject_file(reject_file_path, reject_lines)

        self.stdout.write(
            f"Posted: {posted_count}, Rejected: {rejected_count}, "
            f"Flush failures: {len(failed_ids)}"
        )

    def _validate_transaction(
        self,
        daily_txn: DailyTransaction,
        cache: RecordCache,
    ) -> tuple[int, str]:
        """Validate a daily transaction before posting.

        Returns (0, "") on success, or (reason_code, description) on failure.

        Translated from paragraphs 1500-A-LOOKUP-XREF and
        1500-B-LOOKUP-ACCT in CBTRN02C.cbl.
        """
        # Paragraph 1500-A-LOOKUP-XREF: look up cross-reference by card number
        xref = cache.get_xref(daily_txn.dalytran_card_num)
        if xref is None:
            # COBOL: MOVE 100 TO WS-VALIDATION-FAIL-REASON
            return (100, "INVALID CARD NUMBER FOUND")

        # Paragraph 1500-B-LOOKUP-ACCT: look up account by cross-reference
        account = cache.get_account(xref.xref_acct_id)
        if account is None:
            # COBOL: MOVE 101 TO WS-VALIDATION-FAIL-REASON
            return (101, "ACCOUNT RECORD NOT FOUND")

        # COBOL business rule: credit limit check using RUNNING balance
        # COMPUTE WS-TEMP-BAL = ACCT-CURR-CYC-CREDIT
        #                     - ACCT-CURR-CYC-DEBIT
        #                     + DALYTRAN-AMT
        # HUMAN REVIEW: hardcoded credit limit threshold comparison
        temp_bal = (
            account.acct_curr_cyc_credit - account.acct_curr_cyc_debit + daily_txn.dalytran_amt
        )
        if account.acct_credit_limit < temp_bal:
            # COBOL: MOVE 102 TO WS-VALIDATION-FAIL-REASON
            return (102, "OVERLIMIT TRANSACTION")

        # COBOL business rule: expiration date check
        # IF ACCT-EXPIRAION-DATE >= DALYTRAN-ORIG-TS(1:10)
        txn_date = daily_txn.dalytran_orig_ts[:10]
        if account.acct_expiration_date < txn_date:
            # COBOL: MOVE 103 TO WS-VALIDATION-FAIL-REASON
            return (103, "TRANSACTION RECEIVED AFTER ACCT EXPIRATION")

        return (0, "")

    def _post_transaction(
        self,
        daily_txn: DailyTransaction,
        cache: RecordCache,
        updater: BatchAccountUpdater,
    ) -> None:
        """Post a validated daily transaction.

        Translated from paragraph 2000-POST-TRANSACTION in CBTRN02C.cbl.
        """
        xref = cache.get_xref(daily_txn.dalytran_card_num)
        assert xref is not None  # already validated  # noqa: S101

        # Generate processing timestamp
        # Translated from Z-GET-DB2-FORMAT-TIMESTAMP in CBTRN02C.cbl
        proc_ts = datetime.now(tz=UTC).strftime("%Y-%m-%d-%H.%M.%S.%f")[:26]

        # Paragraph 2700-UPDATE-TCATBAL: update transaction category balance
        self._update_tran_cat_bal(
            xref.xref_acct_id,
            daily_txn.dalytran_type_cd,
            daily_txn.dalytran_cat_cd,
            daily_txn.dalytran_amt,
        )

        # Paragraph 2800-UPDATE-ACCOUNT-REC: accumulate balance delta
        # Uses BatchAccountUpdater instead of direct REWRITE
        updater.accumulate(xref.xref_acct_id, daily_txn.dalytran_amt)
        # Keep cache in sync for subsequent credit limit checks
        cache.apply_delta(xref.xref_acct_id, daily_txn.dalytran_amt)

        # Paragraph 2900-WRITE-TRANSACTION-FILE: write transaction record
        Transaction.objects.create(
            tran_id=daily_txn.dalytran_id,
            tran_type_cd=daily_txn.dalytran_type_cd,
            tran_cat_cd=daily_txn.dalytran_cat_cd,
            tran_source=daily_txn.dalytran_source,
            tran_desc=daily_txn.dalytran_desc,
            tran_amt=daily_txn.dalytran_amt,
            tran_merchant_id=daily_txn.dalytran_merchant_id,
            tran_merchant_name=daily_txn.dalytran_merchant_name,
            tran_merchant_city=daily_txn.dalytran_merchant_city,
            tran_merchant_zip=daily_txn.dalytran_merchant_zip,
            tran_card_num=daily_txn.dalytran_card_num,
            tran_orig_ts=daily_txn.dalytran_orig_ts,
            tran_proc_ts=proc_ts,
        )

    def _update_tran_cat_bal(
        self,
        acct_id: str,
        type_cd: str,
        cat_cd: str,
        amount: Decimal,
    ) -> None:
        """Update or create a transaction category balance record.

        Translated from paragraph 2700-UPDATE-TCATBAL in CBTRN02C.cbl.
        Creates a new record if not found (paragraph 2700-A-CREATE-TCATBAL-REC),
        otherwise updates existing (paragraph 2700-B-UPDATE-TCATBAL-REC).
        """
        tcatbal, created = TranCatBal.objects.get_or_create(
            trancat_acct_id=acct_id,
            trancat_type_cd=type_cd,
            trancat_cd=cat_cd,
            defaults={"tran_cat_bal": amount},
        )
        if not created:
            tcatbal.tran_cat_bal += amount
            tcatbal.save()

    def _write_reject_file(self, file_path: str, reject_lines: list[str]) -> None:
        """Write rejected transactions to a file.

        Translated from paragraph 2500-WRITE-REJECT-REC in CBTRN02C.cbl.
        """
        output_path = Path(file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(reject_lines) + "\n")
