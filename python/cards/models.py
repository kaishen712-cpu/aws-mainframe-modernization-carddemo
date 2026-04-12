"""
Django ORM models for Credit Card Management.

Translated from COBOL copybooks:
- CVACT02Y.cpy → Card (card master record)
- CVACT03Y.cpy → CardXref (card cross-reference)

All monetary fields use Decimal (never float) per CPS 234 requirements.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import models


class Card(models.Model):
    """Credit card master record.

    Translated from CVACT02Y.cpy (CARDDAT VSAM file).
    Original COBOL record is 150 bytes.
    """

    card_num = models.CharField(
        max_length=16,
        unique=True,
        help_text="CARD-NUM PIC X(16) — 16-digit card number",
    )
    card_acct_id = models.CharField(
        max_length=11,
        db_index=True,
        help_text="CARD-ACCT-ID PIC 9(11) — associated account ID",
    )
    card_cvv_cd = models.CharField(
        max_length=3,
        help_text="CARD-CVV-CD PIC 9(03) — CVV code",
    )
    card_embossed_name = models.CharField(
        max_length=50,
        help_text="CARD-EMBOSSED-NAME PIC X(50)",
    )
    card_expiration_date = models.CharField(
        max_length=10,
        help_text="CARD-EXPIRAION-DATE PIC X(10) — YYYY-MM-DD",
    )
    card_active_status = models.CharField(
        max_length=1,
        default="Y",
        help_text="CARD-ACTIVE-STATUS PIC X(01) — Y/N",
    )

    class Meta:
        ordering = ["card_num"]
        verbose_name = "Credit Card"
        verbose_name_plural = "Credit Cards"

    def __str__(self) -> str:
        """Return masked card number for display (CPS 234)."""
        if len(self.card_num) >= 4:
            return f"****-****-****-{self.card_num[-4:]}"
        return "****"


class CardXref(models.Model):
    """Card cross-reference record.

    Translated from CVACT03Y.cpy (CARDXREF / CXACAIX VSAM files).
    Links card numbers to customer and account IDs.
    """

    xref_card_num = models.CharField(
        max_length=16,
        unique=True,
        help_text="XREF-CARD-NUM PIC X(16)",
    )
    xref_cust_id = models.CharField(
        max_length=9,
        help_text="XREF-CUST-ID PIC 9(09)",
    )
    xref_acct_id = models.CharField(
        max_length=11,
        db_index=True,
        help_text="XREF-ACCT-ID PIC 9(11)",
    )

    class Meta:
        ordering = ["xref_card_num"]
        verbose_name = "Card Cross-Reference"
        verbose_name_plural = "Card Cross-References"

    def __str__(self) -> str:
        """Return masked card reference (CPS 234)."""
        return f"Xref: ****{self.xref_card_num[-4:]}"


class Account(models.Model):
    """Account master record.

    Translated from CVACT01Y.cpy (ACCTDAT VSAM file).
    All monetary fields use Decimal per CPS 234 requirements.
    """

    acct_id = models.CharField(
        max_length=11,
        unique=True,
        help_text="ACCT-ID PIC 9(11)",
    )
    acct_active_status = models.CharField(
        max_length=1,
        default="Y",
        help_text="ACCT-ACTIVE-STATUS PIC X(01)",
    )
    acct_curr_bal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="ACCT-CURR-BAL PIC S9(10)V99",
    )
    acct_credit_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="ACCT-CREDIT-LIMIT PIC S9(10)V99",
    )
    acct_cash_credit_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="ACCT-CASH-CREDIT-LIMIT PIC S9(10)V99",
    )
    acct_open_date = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text="ACCT-OPEN-DATE PIC X(10)",
    )
    acct_expiration_date = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text="ACCT-EXPIRAION-DATE PIC X(10)",
    )
    acct_reissue_date = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text="ACCT-REISSUE-DATE PIC X(10)",
    )
    acct_curr_cyc_credit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="ACCT-CURR-CYC-CREDIT PIC S9(10)V99",
    )
    acct_curr_cyc_debit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="ACCT-CURR-CYC-DEBIT PIC S9(10)V99",
    )
    acct_addr_zip = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text="ACCT-ADDR-ZIP PIC X(10)",
    )
    acct_group_id = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text="ACCT-GROUP-ID PIC X(10)",
    )

    class Meta:
        ordering = ["acct_id"]
        verbose_name = "Account"
        verbose_name_plural = "Accounts"

    def __str__(self) -> str:
        """Return account ID."""
        return f"Account {self.acct_id}"
