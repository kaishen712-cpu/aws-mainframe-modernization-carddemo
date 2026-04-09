"""
VSAM record type dataclasses for the CardDemo application.

Each dataclass corresponds to a COBOL copybook in app/cpy/ and represents
a fixed-length record stored in a VSAM KSDS (or sequential) file.

Field names follow Python conventions but map directly to the original
COBOL field names documented in the comments.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AccountRecord:
    """Account master record (CVACT01Y.cpy — 300-byte record)."""

    acct_id: str = ""                   # ACCT-ID              PIC 9(11)
    acct_active_status: str = ""        # ACCT-ACTIVE-STATUS   PIC X(01)
    acct_curr_bal: float = 0.0          # ACCT-CURR-BAL        PIC S9(10)V99
    acct_credit_limit: float = 0.0      # ACCT-CREDIT-LIMIT    PIC S9(10)V99
    acct_cash_credit_limit: float = 0.0  # ACCT-CASH-CREDIT-LIMIT PIC S9(10)V99
    acct_open_date: str = ""            # ACCT-OPEN-DATE       PIC X(10)
    acct_expiration_date: str = ""      # ACCT-EXPIRAION-DATE  PIC X(10)
    acct_reissue_date: str = ""         # ACCT-REISSUE-DATE    PIC X(10)
    acct_curr_cyc_credit: float = 0.0   # ACCT-CURR-CYC-CREDIT PIC S9(10)V99
    acct_curr_cyc_debit: float = 0.0    # ACCT-CURR-CYC-DEBIT  PIC S9(10)V99
    acct_addr_zip: str = ""             # ACCT-ADDR-ZIP        PIC X(10)
    acct_group_id: str = ""             # ACCT-GROUP-ID        PIC X(10)


@dataclass
class CardRecord:
    """Card master record (CVACT02Y.cpy — 150-byte record)."""

    card_num: str = ""                  # CARD-NUM             PIC X(16)
    card_acct_id: str = ""              # CARD-ACCT-ID         PIC 9(11)
    card_cvv_cd: str = ""               # CARD-CVV-CD          PIC 9(03)
    card_embossed_name: str = ""        # CARD-EMBOSSED-NAME   PIC X(50)
    card_expiration_date: str = ""      # CARD-EXPIRAION-DATE  PIC X(10)
    card_active_status: str = ""        # CARD-ACTIVE-STATUS   PIC X(01)


@dataclass
class CardXrefRecord:
    """Card cross-reference record (CVACT03Y.cpy — 50-byte record)."""

    xref_card_num: str = ""             # XREF-CARD-NUM        PIC X(16)
    xref_cust_id: str = ""              # XREF-CUST-ID         PIC 9(09)
    xref_acct_id: str = ""              # XREF-ACCT-ID         PIC 9(11)


@dataclass
class CustomerRecord:
    """Customer master record (CVCUS01Y.cpy — 500-byte record)."""

    cust_id: str = ""                   # CUST-ID              PIC 9(09)
    cust_first_name: str = ""           # CUST-FIRST-NAME      PIC X(25)
    cust_middle_name: str = ""          # CUST-MIDDLE-NAME     PIC X(25)
    cust_last_name: str = ""            # CUST-LAST-NAME       PIC X(25)
    cust_addr_line_1: str = ""          # CUST-ADDR-LINE-1     PIC X(50)
    cust_addr_line_2: str = ""          # CUST-ADDR-LINE-2     PIC X(50)
    cust_addr_line_3: str = ""          # CUST-ADDR-LINE-3     PIC X(50)
    cust_addr_state_cd: str = ""        # CUST-ADDR-STATE-CD   PIC X(02)
    cust_addr_country_cd: str = ""      # CUST-ADDR-COUNTRY-CD PIC X(03)
    cust_addr_zip: str = ""             # CUST-ADDR-ZIP        PIC X(10)
    cust_phone_num_1: str = ""          # CUST-PHONE-NUM-1     PIC X(15)
    cust_phone_num_2: str = ""          # CUST-PHONE-NUM-2     PIC X(15)
    cust_ssn: str = ""                  # CUST-SSN             PIC 9(09)
    cust_govt_issued_id: str = ""       # CUST-GOVT-ISSUED-ID  PIC X(20)
    cust_dob_yyyy_mm_dd: str = ""       # CUST-DOB-YYYY-MM-DD  PIC X(10)
    cust_eft_account_id: str = ""       # CUST-EFT-ACCOUNT-ID  PIC X(10)
    cust_pri_card_holder_ind: str = ""  # CUST-PRI-CARD-HOLDER-IND PIC X(01)
    cust_fico_credit_score: str = ""    # CUST-FICO-CREDIT-SCORE PIC 9(03)


@dataclass
class TransactionRecord:
    """Transaction record (CVTRA05Y.cpy — 350-byte record)."""

    tran_id: str = ""                   # TRAN-ID              PIC X(16)
    tran_type_cd: str = ""              # TRAN-TYPE-CD         PIC X(02)
    tran_cat_cd: str = ""               # TRAN-CAT-CD          PIC 9(04)
    tran_source: str = ""               # TRAN-SOURCE          PIC X(10)
    tran_desc: str = ""                 # TRAN-DESC            PIC X(100)
    tran_amt: float = 0.0              # TRAN-AMT             PIC S9(09)V99
    tran_merchant_id: str = ""          # TRAN-MERCHANT-ID     PIC 9(09)
    tran_merchant_name: str = ""        # TRAN-MERCHANT-NAME   PIC X(50)
    tran_merchant_city: str = ""        # TRAN-MERCHANT-CITY   PIC X(50)
    tran_merchant_zip: str = ""         # TRAN-MERCHANT-ZIP    PIC X(10)
    tran_card_num: str = ""             # TRAN-CARD-NUM        PIC X(16)
    tran_orig_ts: str = ""              # TRAN-ORIG-TS         PIC X(26)
    tran_proc_ts: str = ""              # TRAN-PROC-TS         PIC X(26)


@dataclass
class DailyTransactionRecord:
    """Daily transaction record (CVTRA06Y.cpy — 350-byte record).

    Same layout as TransactionRecord but uses DALYTRAN- prefix in COBOL.
    """

    dalytran_id: str = ""               # DALYTRAN-ID          PIC X(16)
    dalytran_type_cd: str = ""          # DALYTRAN-TYPE-CD     PIC X(02)
    dalytran_cat_cd: str = ""           # DALYTRAN-CAT-CD      PIC 9(04)
    dalytran_source: str = ""           # DALYTRAN-SOURCE      PIC X(10)
    dalytran_desc: str = ""             # DALYTRAN-DESC        PIC X(100)
    dalytran_amt: float = 0.0          # DALYTRAN-AMT         PIC S9(09)V99
    dalytran_merchant_id: str = ""      # DALYTRAN-MERCHANT-ID PIC 9(09)
    dalytran_merchant_name: str = ""    # DALYTRAN-MERCHANT-NAME PIC X(50)
    dalytran_merchant_city: str = ""    # DALYTRAN-MERCHANT-CITY PIC X(50)
    dalytran_merchant_zip: str = ""     # DALYTRAN-MERCHANT-ZIP PIC X(10)
    dalytran_card_num: str = ""         # DALYTRAN-CARD-NUM    PIC X(16)
    dalytran_orig_ts: str = ""          # DALYTRAN-ORIG-TS     PIC X(26)
    dalytran_proc_ts: str = ""          # DALYTRAN-PROC-TS     PIC X(26)


@dataclass
class TranCatBalRecord:
    """Transaction category balance record (CVTRA01Y.cpy — 50-byte record)."""

    trancat_acct_id: str = ""           # TRANCAT-ACCT-ID      PIC 9(11)
    trancat_type_cd: str = ""           # TRANCAT-TYPE-CD      PIC X(02)
    trancat_cd: str = ""                # TRANCAT-CD           PIC 9(04)
    tran_cat_bal: float = 0.0          # TRAN-CAT-BAL         PIC S9(09)V99


@dataclass
class DisclosureGroupRecord:
    """Disclosure group record (CVTRA02Y.cpy — 50-byte record)."""

    dis_acct_group_id: str = ""         # DIS-ACCT-GROUP-ID    PIC X(10)
    dis_tran_type_cd: str = ""          # DIS-TRAN-TYPE-CD     PIC X(02)
    dis_tran_cat_cd: str = ""           # DIS-TRAN-CAT-CD      PIC 9(04)
    dis_int_rate: float = 0.0          # DIS-INT-RATE         PIC S9(04)V99


@dataclass
class TransactionTypeRecord:
    """Transaction type record (CVTRA03Y.cpy — 60-byte record)."""

    tran_type: str = ""                 # TRAN-TYPE            PIC X(02)
    tran_type_desc: str = ""            # TRAN-TYPE-DESC       PIC X(50)


@dataclass
class TransactionCategoryRecord:
    """Transaction category record (CVTRA04Y.cpy — 60-byte record)."""

    tran_type_cd: str = ""              # TRAN-TYPE-CD         PIC X(02)
    tran_cat_cd: str = ""               # TRAN-CAT-CD          PIC 9(04)
    tran_cat_type_desc: str = ""        # TRAN-CAT-TYPE-DESC   PIC X(50)


@dataclass
class UserSecurityRecord:
    """User security record (CSUSR01Y.cpy — 80-byte record)."""

    sec_usr_id: str = ""                # SEC-USR-ID           PIC X(08)
    sec_usr_fname: str = ""             # SEC-USR-FNAME        PIC X(20)
    sec_usr_lname: str = ""             # SEC-USR-LNAME        PIC X(20)
    sec_usr_pwd: str = ""               # SEC-USR-PWD          PIC X(08)
    sec_usr_type: str = ""              # SEC-USR-TYPE         PIC X(01)


@dataclass
class TransactionIndexRecord:
    """Transaction index record (COSTM01.CPY).

    Keyed by CARD-NUM + TRAN-ID for alternate-index access used in reporting.
    Contains the same transaction fields reorganised under the TRNX- prefix.
    """

    trnx_card_num: str = ""             # TRNX-CARD-NUM        PIC X(16)
    trnx_id: str = ""                   # TRNX-ID              PIC X(16)
    trnx_type_cd: str = ""              # TRNX-TYPE-CD         PIC X(02)
    trnx_cat_cd: str = ""               # TRNX-CAT-CD          PIC 9(04)
    trnx_source: str = ""               # TRNX-SOURCE          PIC X(10)
    trnx_desc: str = ""                 # TRNX-DESC            PIC X(100)
    trnx_amt: float = 0.0             # TRNX-AMT             PIC S9(09)V99
    trnx_merchant_id: str = ""          # TRNX-MERCHANT-ID     PIC 9(09)
    trnx_merchant_name: str = ""        # TRNX-MERCHANT-NAME   PIC X(50)
    trnx_merchant_city: str = ""        # TRNX-MERCHANT-CITY   PIC X(50)
    trnx_merchant_zip: str = ""         # TRNX-MERCHANT-ZIP    PIC X(10)
    trnx_orig_ts: str = ""              # TRNX-ORIG-TS         PIC X(26)
    trnx_proc_ts: str = ""              # TRNX-PROC-TS         PIC X(26)
