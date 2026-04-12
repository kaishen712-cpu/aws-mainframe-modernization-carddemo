"""
Django ORM models for Transaction Management.

Translated from COBOL copybook CVTRA05Y.cpy (TRANSACT VSAM file).
All monetary fields use Decimal (never float) per CPS 234 requirements.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import models


class Transaction(models.Model):
    """Transaction record.

    Translated from CVTRA05Y.cpy (TRANSACT VSAM file).
    Original COBOL record is 350 bytes.
    """

    tran_id = models.CharField(
        max_length=16,
        unique=True,
        help_text="TRAN-ID PIC X(16) — auto-generated transaction ID",
    )
    tran_type_cd = models.CharField(
        max_length=2,
        help_text="TRAN-TYPE-CD PIC X(02)",
    )
    tran_cat_cd = models.CharField(
        max_length=4,
        help_text="TRAN-CAT-CD PIC 9(04)",
    )
    tran_source = models.CharField(
        max_length=10,
        help_text="TRAN-SOURCE PIC X(10)",
    )
    tran_desc = models.CharField(
        max_length=100,
        help_text="TRAN-DESC PIC X(100)",
    )
    tran_amt = models.DecimalField(
        max_digits=11,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="TRAN-AMT PIC S9(09)V99",
    )
    tran_merchant_id = models.CharField(
        max_length=9,
        help_text="TRAN-MERCHANT-ID PIC 9(09)",
    )
    tran_merchant_name = models.CharField(
        max_length=50,
        help_text="TRAN-MERCHANT-NAME PIC X(50)",
    )
    tran_merchant_city = models.CharField(
        max_length=50,
        help_text="TRAN-MERCHANT-CITY PIC X(50)",
    )
    tran_merchant_zip = models.CharField(
        max_length=10,
        help_text="TRAN-MERCHANT-ZIP PIC X(10)",
    )
    tran_card_num = models.CharField(
        max_length=16,
        db_index=True,
        help_text="TRAN-CARD-NUM PIC X(16)",
    )
    tran_orig_ts = models.CharField(
        max_length=26,
        help_text="TRAN-ORIG-TS PIC X(26) — origination timestamp",
    )
    tran_proc_ts = models.CharField(
        max_length=26,
        help_text="TRAN-PROC-TS PIC X(26) — processing timestamp",
    )

    class Meta:
        ordering = ["-tran_id"]
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"

    def __str__(self) -> str:
        """Return transaction ID (no sensitive data per CPS 234)."""
        return f"Transaction {self.tran_id}"
