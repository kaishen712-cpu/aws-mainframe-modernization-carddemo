"""Django models for the CardDemo application.

Each model maps to a COBOL copybook / VSAM file from the original mainframe
system. Field names follow Python conventions but preserve the original COBOL
field names in comments for traceability.

All monetary fields use ``DecimalField`` — never ``FloatField`` — to prevent
floating-point rounding errors in a banking application.
"""

from __future__ import annotations

from django.db import models


class Account(models.Model):
    """Account master record.

    Mapped from: CVACT01Y.cpy (300-byte VSAM KSDS record)
    Original COBOL record name: ACCOUNT-RECORD
    """

    acct_id = models.CharField(
        max_length=11, unique=True, help_text="ACCT-ID PIC 9(11)"
    )
    acct_active_status = models.CharField(
        max_length=1, default="", help_text="ACCT-ACTIVE-STATUS PIC X(01)"
    )
    acct_curr_bal = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="ACCT-CURR-BAL PIC S9(10)V99",
    )
    acct_credit_limit = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="ACCT-CREDIT-LIMIT PIC S9(10)V99",
    )
    acct_cash_credit_limit = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="ACCT-CASH-CREDIT-LIMIT PIC S9(10)V99",
    )
    acct_open_date = models.CharField(
        max_length=10, default="", help_text="ACCT-OPEN-DATE PIC X(10)"
    )
    acct_expiration_date = models.CharField(
        max_length=10, default="", help_text="ACCT-EXPIRAION-DATE PIC X(10)"
    )
    acct_reissue_date = models.CharField(
        max_length=10, default="", help_text="ACCT-REISSUE-DATE PIC X(10)"
    )
    acct_curr_cyc_credit = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="ACCT-CURR-CYC-CREDIT PIC S9(10)V99",
    )
    acct_curr_cyc_debit = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="ACCT-CURR-CYC-DEBIT PIC S9(10)V99",
    )
    acct_addr_zip = models.CharField(
        max_length=10, default="", help_text="ACCT-ADDR-ZIP PIC X(10)"
    )
    acct_group_id = models.CharField(
        max_length=10, default="", help_text="ACCT-GROUP-ID PIC X(10)"
    )

    class Meta:
        db_table = "account"
        verbose_name = "Account"
        verbose_name_plural = "Accounts"

    def __str__(self) -> str:
        return f"Account({self.acct_id})"


class Card(models.Model):
    """Card master record.

    Mapped from: CVACT02Y.cpy (150-byte VSAM KSDS record)
    Original COBOL record name: CARD-RECORD
    """

    card_num = models.CharField(
        max_length=16, unique=True, help_text="CARD-NUM PIC X(16)"
    )
    card_acct_id = models.CharField(
        max_length=11, db_index=True, help_text="CARD-ACCT-ID PIC 9(11)"
    )
    card_cvv_cd = models.CharField(
        max_length=3, default="", help_text="CARD-CVV-CD PIC 9(03)"
    )
    card_embossed_name = models.CharField(
        max_length=50, default="", help_text="CARD-EMBOSSED-NAME PIC X(50)"
    )
    card_expiration_date = models.CharField(
        max_length=10, default="", help_text="CARD-EXPIRAION-DATE PIC X(10)"
    )
    card_active_status = models.CharField(
        max_length=1, default="", help_text="CARD-ACTIVE-STATUS PIC X(01)"
    )

    class Meta:
        db_table = "card"
        verbose_name = "Card"
        verbose_name_plural = "Cards"

    def __str__(self) -> str:
        return f"Card(****{self.card_num[-4:]})"


class CardXref(models.Model):
    """Card cross-reference record.

    Mapped from: CVACT03Y.cpy (50-byte VSAM KSDS record)
    Original COBOL record name: CARD-XREF-RECORD
    """

    xref_card_num = models.CharField(
        max_length=16, unique=True, help_text="XREF-CARD-NUM PIC X(16)"
    )
    xref_cust_id = models.CharField(
        max_length=9, db_index=True, help_text="XREF-CUST-ID PIC 9(09)"
    )
    xref_acct_id = models.CharField(
        max_length=11, db_index=True, help_text="XREF-ACCT-ID PIC 9(11)"
    )

    class Meta:
        db_table = "card_xref"
        verbose_name = "Card Cross-Reference"
        verbose_name_plural = "Card Cross-References"

    def __str__(self) -> str:
        return f"CardXref(****{self.xref_card_num[-4:]})"


class Customer(models.Model):
    """Customer master record.

    Mapped from: CVCUS01Y.cpy (500-byte VSAM KSDS record)
    Original COBOL record name: CUSTOMER-RECORD
    """

    cust_id = models.CharField(
        max_length=9, unique=True, help_text="CUST-ID PIC 9(09)"
    )
    cust_first_name = models.CharField(
        max_length=25, default="", help_text="CUST-FIRST-NAME PIC X(25)"
    )
    cust_middle_name = models.CharField(
        max_length=25, default="", help_text="CUST-MIDDLE-NAME PIC X(25)"
    )
    cust_last_name = models.CharField(
        max_length=25, default="", help_text="CUST-LAST-NAME PIC X(25)"
    )
    cust_addr_line_1 = models.CharField(
        max_length=50, default="", help_text="CUST-ADDR-LINE-1 PIC X(50)"
    )
    cust_addr_line_2 = models.CharField(
        max_length=50, default="", help_text="CUST-ADDR-LINE-2 PIC X(50)"
    )
    cust_addr_line_3 = models.CharField(
        max_length=50, default="", help_text="CUST-ADDR-LINE-3 PIC X(50)"
    )
    cust_addr_state_cd = models.CharField(
        max_length=2, default="", help_text="CUST-ADDR-STATE-CD PIC X(02)"
    )
    cust_addr_country_cd = models.CharField(
        max_length=3, default="", help_text="CUST-ADDR-COUNTRY-CD PIC X(03)"
    )
    cust_addr_zip = models.CharField(
        max_length=10, default="", help_text="CUST-ADDR-ZIP PIC X(10)"
    )
    cust_phone_num_1 = models.CharField(
        max_length=15, default="", help_text="CUST-PHONE-NUM-1 PIC X(15)"
    )
    cust_phone_num_2 = models.CharField(
        max_length=15, default="", help_text="CUST-PHONE-NUM-2 PIC X(15)"
    )
    cust_ssn = models.CharField(
        max_length=9, default="", help_text="CUST-SSN PIC 9(09)"
    )
    cust_govt_issued_id = models.CharField(
        max_length=20, default="", help_text="CUST-GOVT-ISSUED-ID PIC X(20)"
    )
    cust_dob_yyyy_mm_dd = models.CharField(
        max_length=10, default="", help_text="CUST-DOB-YYYY-MM-DD PIC X(10)"
    )
    cust_eft_account_id = models.CharField(
        max_length=10, default="", help_text="CUST-EFT-ACCOUNT-ID PIC X(10)"
    )
    cust_pri_card_holder_ind = models.CharField(
        max_length=1, default="", help_text="CUST-PRI-CARD-HOLDER-IND PIC X(01)"
    )
    cust_fico_credit_score = models.CharField(
        max_length=3, default="", help_text="CUST-FICO-CREDIT-SCORE PIC 9(03)"
    )

    class Meta:
        db_table = "customer"
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    def __str__(self) -> str:
        return f"Customer({self.cust_id})"


class Transaction(models.Model):
    """Transaction record.

    Mapped from: CVTRA05Y.cpy (350-byte VSAM KSDS record)
    Original COBOL record name: TRAN-RECORD
    """

    tran_id = models.CharField(
        max_length=16, unique=True, help_text="TRAN-ID PIC X(16)"
    )
    tran_type_cd = models.CharField(
        max_length=2, default="", help_text="TRAN-TYPE-CD PIC X(02)"
    )
    tran_cat_cd = models.CharField(
        max_length=4, default="", help_text="TRAN-CAT-CD PIC 9(04)"
    )
    tran_source = models.CharField(
        max_length=10, default="", help_text="TRAN-SOURCE PIC X(10)"
    )
    tran_desc = models.CharField(
        max_length=100, default="", help_text="TRAN-DESC PIC X(100)"
    )
    tran_amt = models.DecimalField(
        max_digits=11, decimal_places=2, default=0,
        help_text="TRAN-AMT PIC S9(09)V99",
    )
    tran_merchant_id = models.CharField(
        max_length=9, default="", help_text="TRAN-MERCHANT-ID PIC 9(09)"
    )
    tran_merchant_name = models.CharField(
        max_length=50, default="", help_text="TRAN-MERCHANT-NAME PIC X(50)"
    )
    tran_merchant_city = models.CharField(
        max_length=50, default="", help_text="TRAN-MERCHANT-CITY PIC X(50)"
    )
    tran_merchant_zip = models.CharField(
        max_length=10, default="", help_text="TRAN-MERCHANT-ZIP PIC X(10)"
    )
    tran_card_num = models.CharField(
        max_length=16, db_index=True, help_text="TRAN-CARD-NUM PIC X(16)"
    )
    tran_orig_ts = models.CharField(
        max_length=26, default="", help_text="TRAN-ORIG-TS PIC X(26)"
    )
    tran_proc_ts = models.CharField(
        max_length=26, default="", help_text="TRAN-PROC-TS PIC X(26)"
    )

    class Meta:
        db_table = "transaction"
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"

    def __str__(self) -> str:
        return f"Transaction({self.tran_id})"


class DailyTransaction(models.Model):
    """Daily transaction record — input for batch posting.

    Mapped from: CVTRA06Y.cpy (350-byte sequential record)
    Original COBOL record name: DALYTRAN-RECORD
    """

    dalytran_id = models.CharField(
        max_length=16, unique=True, help_text="DALYTRAN-ID PIC X(16)"
    )
    dalytran_type_cd = models.CharField(
        max_length=2, default="", help_text="DALYTRAN-TYPE-CD PIC X(02)"
    )
    dalytran_cat_cd = models.CharField(
        max_length=4, default="", help_text="DALYTRAN-CAT-CD PIC 9(04)"
    )
    dalytran_source = models.CharField(
        max_length=10, default="", help_text="DALYTRAN-SOURCE PIC X(10)"
    )
    dalytran_desc = models.CharField(
        max_length=100, default="", help_text="DALYTRAN-DESC PIC X(100)"
    )
    dalytran_amt = models.DecimalField(
        max_digits=11, decimal_places=2, default=0,
        help_text="DALYTRAN-AMT PIC S9(09)V99",
    )
    dalytran_merchant_id = models.CharField(
        max_length=9, default="", help_text="DALYTRAN-MERCHANT-ID PIC 9(09)"
    )
    dalytran_merchant_name = models.CharField(
        max_length=50, default="", help_text="DALYTRAN-MERCHANT-NAME PIC X(50)"
    )
    dalytran_merchant_city = models.CharField(
        max_length=50, default="", help_text="DALYTRAN-MERCHANT-CITY PIC X(50)"
    )
    dalytran_merchant_zip = models.CharField(
        max_length=10, default="", help_text="DALYTRAN-MERCHANT-ZIP PIC X(10)"
    )
    dalytran_card_num = models.CharField(
        max_length=16, db_index=True, help_text="DALYTRAN-CARD-NUM PIC X(16)"
    )
    dalytran_orig_ts = models.CharField(
        max_length=26, default="", help_text="DALYTRAN-ORIG-TS PIC X(26)"
    )
    dalytran_proc_ts = models.CharField(
        max_length=26, default="", help_text="DALYTRAN-PROC-TS PIC X(26)"
    )

    class Meta:
        db_table = "daily_transaction"
        verbose_name = "Daily Transaction"
        verbose_name_plural = "Daily Transactions"

    def __str__(self) -> str:
        return f"DailyTransaction({self.dalytran_id})"


class TranCatBal(models.Model):
    """Transaction category balance record.

    Mapped from: CVTRA01Y.cpy (50-byte VSAM KSDS record)
    Original COBOL record name: TRAN-CAT-BAL-RECORD
    Composite key: (TRANCAT-ACCT-ID, TRANCAT-TYPE-CD, TRANCAT-CD)
    """

    trancat_acct_id = models.CharField(
        max_length=11, help_text="TRANCAT-ACCT-ID PIC 9(11)"
    )
    trancat_type_cd = models.CharField(
        max_length=2, help_text="TRANCAT-TYPE-CD PIC X(02)"
    )
    trancat_cd = models.CharField(
        max_length=4, help_text="TRANCAT-CD PIC 9(04)"
    )
    tran_cat_bal = models.DecimalField(
        max_digits=11, decimal_places=2, default=0,
        help_text="TRAN-CAT-BAL PIC S9(09)V99",
    )

    class Meta:
        db_table = "tran_cat_bal"
        unique_together = [("trancat_acct_id", "trancat_type_cd", "trancat_cd")]
        verbose_name = "Transaction Category Balance"
        verbose_name_plural = "Transaction Category Balances"

    def __str__(self) -> str:
        return f"TranCatBal({self.trancat_acct_id}/{self.trancat_type_cd}/{self.trancat_cd})"


class DisclosureGroup(models.Model):
    """Disclosure group record — interest rates by account group + category.

    Mapped from: CVTRA02Y.cpy (50-byte VSAM KSDS record)
    Original COBOL record name: DIS-GROUP-RECORD
    Composite key: (DIS-ACCT-GROUP-ID, DIS-TRAN-TYPE-CD, DIS-TRAN-CAT-CD)

    NOTE: dis_int_rate is a hardcoded threshold field.
    HUMAN REVIEW REQUIRED — interest rates are business-critical values
    that should be validated before migration.
    """

    dis_acct_group_id = models.CharField(
        max_length=10, help_text="DIS-ACCT-GROUP-ID PIC X(10)"
    )
    dis_tran_type_cd = models.CharField(
        max_length=2, help_text="DIS-TRAN-TYPE-CD PIC X(02)"
    )
    dis_tran_cat_cd = models.CharField(
        max_length=4, help_text="DIS-TRAN-CAT-CD PIC 9(04)"
    )
    dis_int_rate = models.DecimalField(
        max_digits=6, decimal_places=2, default=0,
        help_text="DIS-INT-RATE PIC S9(04)V99 — HUMAN REVIEW: hardcoded interest rate",
    )

    class Meta:
        db_table = "disclosure_group"
        unique_together = [
            ("dis_acct_group_id", "dis_tran_type_cd", "dis_tran_cat_cd")
        ]
        verbose_name = "Disclosure Group"
        verbose_name_plural = "Disclosure Groups"

    def __str__(self) -> str:
        return (
            f"DisclosureGroup({self.dis_acct_group_id}"
            f"/{self.dis_tran_type_cd}/{self.dis_tran_cat_cd})"
        )


class TransactionType(models.Model):
    """Transaction type record.

    Mapped from: CVTRA03Y.cpy (60-byte VSAM KSDS record)
    Original COBOL record name: TRAN-TYPE-RECORD
    """

    tran_type = models.CharField(
        max_length=2, unique=True, help_text="TRAN-TYPE PIC X(02)"
    )
    tran_type_desc = models.CharField(
        max_length=50, default="", help_text="TRAN-TYPE-DESC PIC X(50)"
    )

    class Meta:
        db_table = "transaction_type"
        verbose_name = "Transaction Type"
        verbose_name_plural = "Transaction Types"

    def __str__(self) -> str:
        return f"TransactionType({self.tran_type})"


class TransactionCategory(models.Model):
    """Transaction category record.

    Mapped from: CVTRA04Y.cpy (60-byte VSAM KSDS record)
    Original COBOL record name: TRAN-CAT-TYPE-RECORD
    Composite key: (TRAN-TYPE-CD, TRAN-CAT-CD)
    """

    tran_type_cd = models.CharField(
        max_length=2, help_text="TRAN-TYPE-CD PIC X(02)"
    )
    tran_cat_cd = models.CharField(
        max_length=4, help_text="TRAN-CAT-CD PIC 9(04)"
    )
    tran_cat_type_desc = models.CharField(
        max_length=50, default="", help_text="TRAN-CAT-TYPE-DESC PIC X(50)"
    )

    class Meta:
        db_table = "transaction_category"
        unique_together = [("tran_type_cd", "tran_cat_cd")]
        verbose_name = "Transaction Category"
        verbose_name_plural = "Transaction Categories"

    def __str__(self) -> str:
        return f"TransactionCategory({self.tran_type_cd}/{self.tran_cat_cd})"


class UserSecurity(models.Model):
    """User security record.

    Mapped from: CSUSR01Y.cpy (80-byte VSAM KSDS record)
    Original COBOL record name: SEC-USER-DATA
    """

    sec_usr_id = models.CharField(
        max_length=8, unique=True, help_text="SEC-USR-ID PIC X(08)"
    )
    sec_usr_fname = models.CharField(
        max_length=20, default="", help_text="SEC-USR-FNAME PIC X(20)"
    )
    sec_usr_lname = models.CharField(
        max_length=20, default="", help_text="SEC-USR-LNAME PIC X(20)"
    )
    sec_usr_pwd = models.CharField(
        max_length=128, default="", help_text="SEC-USR-PWD — hashed, never plain text"
    )
    sec_usr_type = models.CharField(
        max_length=1, default="", help_text="SEC-USR-TYPE PIC X(01)"
    )

    class Meta:
        db_table = "user_security"
        verbose_name = "User Security"
        verbose_name_plural = "User Security Records"

    def __str__(self) -> str:
        return f"UserSecurity({self.sec_usr_id})"


class TransactionIndex(models.Model):
    """Transaction index record — alternate-index view for reporting.

    Mapped from: COSTM01.CPY
    Original COBOL record name: TRNX-RECORD
    Key: CARD-NUM + TRAN-ID
    """

    trnx_card_num = models.CharField(
        max_length=16, db_index=True, help_text="TRNX-CARD-NUM PIC X(16)"
    )
    trnx_id = models.CharField(
        max_length=16, help_text="TRNX-ID PIC X(16)"
    )
    trnx_type_cd = models.CharField(
        max_length=2, default="", help_text="TRNX-TYPE-CD PIC X(02)"
    )
    trnx_cat_cd = models.CharField(
        max_length=4, default="", help_text="TRNX-CAT-CD PIC 9(04)"
    )
    trnx_source = models.CharField(
        max_length=10, default="", help_text="TRNX-SOURCE PIC X(10)"
    )
    trnx_desc = models.CharField(
        max_length=100, default="", help_text="TRNX-DESC PIC X(100)"
    )
    trnx_amt = models.DecimalField(
        max_digits=11, decimal_places=2, default=0,
        help_text="TRNX-AMT PIC S9(09)V99",
    )
    trnx_merchant_id = models.CharField(
        max_length=9, default="", help_text="TRNX-MERCHANT-ID PIC 9(09)"
    )
    trnx_merchant_name = models.CharField(
        max_length=50, default="", help_text="TRNX-MERCHANT-NAME PIC X(50)"
    )
    trnx_merchant_city = models.CharField(
        max_length=50, default="", help_text="TRNX-MERCHANT-CITY PIC X(50)"
    )
    trnx_merchant_zip = models.CharField(
        max_length=10, default="", help_text="TRNX-MERCHANT-ZIP PIC X(10)"
    )
    trnx_orig_ts = models.CharField(
        max_length=26, default="", help_text="TRNX-ORIG-TS PIC X(26)"
    )
    trnx_proc_ts = models.CharField(
        max_length=26, default="", help_text="TRNX-PROC-TS PIC X(26)"
    )

    class Meta:
        db_table = "transaction_index"
        unique_together = [("trnx_card_num", "trnx_id")]
        verbose_name = "Transaction Index"
        verbose_name_plural = "Transaction Indexes"

    def __str__(self) -> str:
        return f"TransactionIndex(****{self.trnx_card_num[-4:]}/{self.trnx_id})"
