"""Monthly interest calculation — batch management command.

Translated from CBACT04C.cbl (653 lines).

Original COBOL program flow:
1. Open 5 files (TCATBAL, XREF, DISCGRP, ACCOUNT, TRANSACT)
2. Read transaction category balances sequentially
3. Group by account — when account changes, compute and post interest
4. For each category balance: look up interest rate from disclosure group
5. COMPUTE WS-MONTHLY-INT = (TRAN-CAT-BAL * DIS-INT-RATE) / 1200
6. Write interest transaction records
7. Update account balances
8. Close all files

HUMAN REVIEW: Interest rate calculation uses hardcoded divisor 1200
(annual rate / 12 months * 100 for percentage). This is a business-critical
threshold that should be validated before migration.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import ROUND_HALF_EVEN, Decimal

from django.core.management.base import BaseCommand, CommandParser
from django.db.models import F

from batch.models import (
    Account,
    CardXref,
    DisclosureGroup,
    TranCatBal,
    Transaction,
)

logger = logging.getLogger(__name__)

# HUMAN REVIEW: hardcoded divisor for monthly interest calculation
# Original COBOL: COMPUTE WS-MONTHLY-INT = (TRAN-CAT-BAL * DIS-INT-RATE) / 1200
ANNUAL_TO_MONTHLY_DIVISOR = Decimal("1200")
MONETARY_QUANTIZE = Decimal("0.01")


class Command(BaseCommand):
    """Calculate monthly interest — translated from CBACT04C.cbl."""

    help = "Calculate monthly interest on transaction category balances (CBACT04C.cbl)"

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command-line arguments."""
        parser.add_argument(
            "--date",
            type=str,
            default="",
            help="Processing date YYYY-MM-DD (default: today)",
        )

    def handle(self, *args: object, **options: object) -> None:
        """Execute the monthly interest calculation batch process.

        Translated from PROCEDURE DIVISION of CBACT04C.cbl.
        Main loop: paragraph 1000-TCATBAL-GET-NEXT through 1300-COMPUTE-INTEREST.
        """
        date_str = str(options.get("date", "") or "")
        if not date_str:
            date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")

        accounts_processed = 0
        interest_txns_created = 0
        txn_suffix = 0

        # Translated from main loop in CBACT04C.cbl
        # Read TCATBAL records grouped by account
        tcatbal_records = TranCatBal.objects.all().order_by(
            "trancat_acct_id", "trancat_type_cd", "trancat_cd"
        )

        current_acct_id = ""
        total_interest = Decimal("0")

        for tcatbal in tcatbal_records:
            # Account break — when account changes, post accumulated interest
            if tcatbal.trancat_acct_id != current_acct_id:
                if current_acct_id and total_interest != Decimal("0"):
                    self._update_account_balance(current_acct_id, total_interest)
                    accounts_processed += 1
                current_acct_id = tcatbal.trancat_acct_id
                total_interest = Decimal("0")

            # Paragraph 1200-GET-INTEREST-RATE: look up disclosure group rate
            interest_rate = self._get_interest_rate(
                current_acct_id, tcatbal.trancat_type_cd, tcatbal.trancat_cd
            )

            if interest_rate is None:
                continue

            # Paragraph 1300-COMPUTE-INTEREST
            # COBOL: COMPUTE WS-MONTHLY-INT = (TRAN-CAT-BAL * DIS-INT-RATE) / 1200
            # HUMAN REVIEW: hardcoded interest calculation formula
            monthly_interest = (
                tcatbal.tran_cat_bal * interest_rate / ANNUAL_TO_MONTHLY_DIVISOR
            ).quantize(MONETARY_QUANTIZE, rounding=ROUND_HALF_EVEN)

            total_interest += monthly_interest

            # Paragraph 1300-B-WRITE-TX: write interest transaction
            txn_suffix += 1
            tran_id = f"{date_str}{txn_suffix:06d}"[:16]

            xref = self._get_xref_for_account(current_acct_id)
            card_num = xref.xref_card_num if xref else ""

            proc_ts = datetime.now(tz=UTC).strftime("%Y-%m-%d-%H.%M.%S.%f")[:26]

            # Translated from paragraph 1300-B-WRITE-TX in CBACT04C.cbl
            # COBOL: MOVE '01' TO TRAN-TYPE-CD, MOVE '05' TO TRAN-CAT-CD
            Transaction.objects.create(
                tran_id=tran_id,
                tran_type_cd="01",
                tran_cat_cd="05",
                tran_source="System",
                tran_desc=f"Int. for a/c {current_acct_id}",
                tran_amt=monthly_interest,
                tran_merchant_id="0",
                tran_merchant_name="",
                tran_merchant_city="",
                tran_merchant_zip="",
                tran_card_num=card_num,
                tran_orig_ts=proc_ts,
                tran_proc_ts=proc_ts,
            )
            interest_txns_created += 1

        # Process last account
        if current_acct_id and total_interest != Decimal("0"):
            self._update_account_balance(current_acct_id, total_interest)
            accounts_processed += 1

        self.stdout.write(
            f"Accounts processed: {accounts_processed}, "
            f"Interest transactions: {interest_txns_created}"
        )

    def _get_interest_rate(self, acct_id: str, type_cd: str, cat_cd: str) -> Decimal | None:
        """Look up the interest rate from the disclosure group.

        Translated from paragraph 1200-GET-INTEREST-RATE in CBACT04C.cbl.
        Falls back to 'DEFAULT' group if account's group not found
        (paragraph 1200-A-GET-DEFAULT-INT-RATE).

        HUMAN REVIEW: interest rates are hardcoded thresholds.
        """
        try:
            account = Account.objects.get(acct_id=acct_id)
        except Account.DoesNotExist:
            logger.error("Account not found for interest calc: %s", acct_id)
            return None

        group_id = account.acct_group_id.strip()

        # Try account's group first
        try:
            disc_group = DisclosureGroup.objects.get(
                dis_acct_group_id=group_id,
                dis_tran_type_cd=type_cd,
                dis_tran_cat_cd=cat_cd,
            )
            return disc_group.dis_int_rate
        except DisclosureGroup.DoesNotExist:
            pass

        # Fall back to DEFAULT group
        # Translated from paragraph 1200-A-GET-DEFAULT-INT-RATE
        try:
            disc_group = DisclosureGroup.objects.get(
                dis_acct_group_id="DEFAULT",
                dis_tran_type_cd=type_cd,
                dis_tran_cat_cd=cat_cd,
            )
            return disc_group.dis_int_rate
        except DisclosureGroup.DoesNotExist:
            logger.warning("No disclosure group for %s/%s/%s", group_id, type_cd, cat_cd)
            return None

    def _get_xref_for_account(self, acct_id: str) -> CardXref | None:
        """Look up the card cross-reference for an account.

        Translated from paragraph 1110-GET-XREF-DATA in CBACT04C.cbl.
        """
        return CardXref.objects.filter(xref_acct_id=acct_id).first()

    def _update_account_balance(self, acct_id: str, interest_amount: Decimal) -> None:
        """Update the account balance with accumulated interest.

        Translated from account update logic in CBACT04C.cbl.
        Interest is always a credit (positive amount).
        """
        Account.objects.filter(acct_id=acct_id).update(
            acct_curr_bal=F("acct_curr_bal") + interest_amount,
            acct_curr_cyc_credit=F("acct_curr_cyc_credit") + interest_amount,
        )
