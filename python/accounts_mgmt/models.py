"""
Django models for Account and Customer entities.

Translated from COBOL copybooks:
- CVACT01Y.cpy — Account master record (300-byte VSAM record)
- CVCUS01Y.cpy — Customer master record (500-byte VSAM record)
- CVACT03Y.cpy — Card cross-reference record (50-byte VSAM record)

All monetary fields use ``DecimalField`` (never float) per migration standards.
"""

from __future__ import annotations

from django.db import models


class Account(models.Model):
    """Account master record.

    Translated from CVACT01Y.cpy ``ACCOUNT-RECORD``.
    Maps the 300-byte VSAM record layout to Django model fields.
    """

    acct_id = models.CharField(
        "Account ID",
        max_length=11,
        unique=True,
        help_text="PIC 9(11) — 11-digit numeric account identifier.",
    )
    acct_active_status = models.CharField(
        "Active Status",
        max_length=1,
        default="Y",
        help_text="PIC X(01) — Y=active, N=inactive.",
    )
    acct_curr_bal = models.DecimalField(
        "Current Balance",
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="PIC S9(10)V99 — signed current balance.",
    )
    acct_credit_limit = models.DecimalField(
        "Credit Limit",
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="PIC S9(10)V99 — credit limit.",
    )
    acct_cash_credit_limit = models.DecimalField(
        "Cash Credit Limit",
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="PIC S9(10)V99 — cash advance credit limit.",
    )
    acct_open_date = models.CharField(
        "Open Date",
        max_length=10,
        blank=True,
        default="",
        help_text="PIC X(10) — YYYY-MM-DD format.",
    )
    acct_expiration_date = models.CharField(
        "Expiration Date",
        max_length=10,
        blank=True,
        default="",
        help_text="PIC X(10) — YYYY-MM-DD format.",
    )
    acct_reissue_date = models.CharField(
        "Reissue Date",
        max_length=10,
        blank=True,
        default="",
        help_text="PIC X(10) — YYYY-MM-DD format.",
    )
    acct_curr_cyc_credit = models.DecimalField(
        "Current Cycle Credit",
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="PIC S9(10)V99 — current cycle credit total.",
    )
    acct_curr_cyc_debit = models.DecimalField(
        "Current Cycle Debit",
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="PIC S9(10)V99 — current cycle debit total.",
    )
    acct_group_id = models.CharField(
        "Group ID",
        max_length=10,
        blank=True,
        default="",
        help_text="PIC X(10) — account group identifier.",
    )

    class Meta:
        db_table = "account"
        verbose_name = "Account"
        verbose_name_plural = "Accounts"

    def __str__(self) -> str:
        return f"Account {self.acct_id}"


class Customer(models.Model):
    """Customer master record.

    Translated from CVCUS01Y.cpy ``CUSTOMER-RECORD``.
    Maps the 500-byte VSAM record layout to Django model fields.
    """

    cust_id = models.CharField(
        "Customer ID",
        max_length=9,
        unique=True,
        help_text="PIC 9(09) — 9-digit numeric customer identifier.",
    )
    cust_first_name = models.CharField(
        "First Name", max_length=25, blank=True, default="",
        help_text="PIC X(25).",
    )
    cust_middle_name = models.CharField(
        "Middle Name", max_length=25, blank=True, default="",
        help_text="PIC X(25).",
    )
    cust_last_name = models.CharField(
        "Last Name", max_length=25, blank=True, default="",
        help_text="PIC X(25).",
    )
    cust_addr_line_1 = models.CharField(
        "Address Line 1", max_length=50, blank=True, default="",
        help_text="PIC X(50).",
    )
    cust_addr_line_2 = models.CharField(
        "Address Line 2", max_length=50, blank=True, default="",
        help_text="PIC X(50).",
    )
    cust_addr_line_3 = models.CharField(
        "City", max_length=50, blank=True, default="",
        help_text="PIC X(50) — city/locality.",
    )
    cust_addr_state_cd = models.CharField(
        "State Code", max_length=2, blank=True, default="",
        help_text="PIC X(02) — US state code.",
    )
    cust_addr_country_cd = models.CharField(
        "Country Code", max_length=3, blank=True, default="",
        help_text="PIC X(03).",
    )
    cust_addr_zip = models.CharField(
        "ZIP Code", max_length=10, blank=True, default="",
        help_text="PIC X(10).",
    )
    cust_phone_num_1 = models.CharField(
        "Phone Number 1", max_length=15, blank=True, default="",
        help_text="PIC X(15) — format (NPA)NXX-XXXX.",
    )
    cust_phone_num_2 = models.CharField(
        "Phone Number 2", max_length=15, blank=True, default="",
        help_text="PIC X(15) — format (NPA)NXX-XXXX.",
    )
    cust_ssn = models.CharField(
        "SSN", max_length=9, blank=True, default="",
        help_text="PIC 9(09) — 9-digit SSN (stored without dashes).",
    )
    cust_govt_issued_id = models.CharField(
        "Government Issued ID", max_length=20, blank=True, default="",
        help_text="PIC X(20).",
    )
    cust_dob_yyyy_mm_dd = models.CharField(
        "Date of Birth", max_length=10, blank=True, default="",
        help_text="PIC X(10) — YYYY-MM-DD format.",
    )
    cust_eft_account_id = models.CharField(
        "EFT Account ID", max_length=10, blank=True, default="",
        help_text="PIC X(10).",
    )
    cust_pri_card_holder_ind = models.CharField(
        "Primary Card Holder", max_length=1, blank=True, default="",
        help_text="PIC X(01) — Y/N indicator.",
    )
    cust_fico_credit_score = models.CharField(
        "FICO Credit Score", max_length=3, blank=True, default="",
        help_text="PIC 9(03) — 300-850 range.",
    )

    class Meta:
        db_table = "customer"
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    def __str__(self) -> str:
        return f"Customer {self.cust_id}"


class CardXref(models.Model):
    """Card cross-reference record.

    Translated from CVACT03Y.cpy ``CARD-XREF-RECORD``.
    Links card numbers to customer and account IDs.
    """

    xref_card_num = models.CharField(
        "Card Number", max_length=16,
        help_text="PIC X(16) — 16-digit card number.",
    )
    xref_cust_id = models.CharField(
        "Customer ID", max_length=9,
        help_text="PIC 9(09).",
    )
    xref_acct_id = models.CharField(
        "Account ID", max_length=11,
        help_text="PIC 9(11).",
    )

    class Meta:
        db_table = "card_xref"
        verbose_name = "Card Cross Reference"
        verbose_name_plural = "Card Cross References"

    def __str__(self) -> str:
        return f"CardXref acct={self.xref_acct_id}"
