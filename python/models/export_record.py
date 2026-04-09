"""
Multi-record export structure dataclasses.

Translated from CVEXPORT.cpy — the export file layout used for branch
migration.  The 500-byte record has a common header (record type,
timestamp, sequence number, branch/region) followed by a union of
sub-record types selected by EXPORT-REC-TYPE.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Sub-record variants (REDEFINES of EXPORT-RECORD-DATA)
# ---------------------------------------------------------------------------

@dataclass
class ExportCustomerData:
    """Customer sub-record within an export record (EXPORT-CUSTOMER-DATA)."""

    exp_cust_id: int = 0                        # EXP-CUST-ID         PIC 9(09) COMP
    exp_cust_first_name: str = ""               # EXP-CUST-FIRST-NAME PIC X(25)
    exp_cust_middle_name: str = ""              # EXP-CUST-MIDDLE-NAME PIC X(25)
    exp_cust_last_name: str = ""                # EXP-CUST-LAST-NAME  PIC X(25)
    exp_cust_addr_lines: list[str] = field(     # EXP-CUST-ADDR-LINES OCCURS 3
        default_factory=lambda: ["", "", ""]
    )
    exp_cust_addr_state_cd: str = ""            # EXP-CUST-ADDR-STATE-CD PIC X(02)
    exp_cust_addr_country_cd: str = ""          # EXP-CUST-ADDR-COUNTRY-CD PIC X(03)
    exp_cust_addr_zip: str = ""                 # EXP-CUST-ADDR-ZIP   PIC X(10)
    exp_cust_phone_nums: list[str] = field(     # EXP-CUST-PHONE-NUMS OCCURS 2
        default_factory=lambda: ["", ""]
    )
    exp_cust_ssn: str = ""                      # EXP-CUST-SSN        PIC 9(09)
    exp_cust_govt_issued_id: str = ""           # EXP-CUST-GOVT-ISSUED-ID PIC X(20)
    exp_cust_dob_yyyy_mm_dd: str = ""           # EXP-CUST-DOB-YYYY-MM-DD PIC X(10)
    exp_cust_eft_account_id: str = ""           # EXP-CUST-EFT-ACCOUNT-ID PIC X(10)
    exp_cust_pri_card_holder_ind: str = ""      # EXP-CUST-PRI-CARD-HOLDER-IND PIC X(01)
    exp_cust_fico_credit_score: int = 0         # EXP-CUST-FICO-CREDIT-SCORE PIC 9(03) COMP-3


@dataclass
class ExportAccountData:
    """Account sub-record within an export record (EXPORT-ACCOUNT-DATA)."""

    exp_acct_id: str = ""                       # EXP-ACCT-ID         PIC 9(11)
    exp_acct_active_status: str = ""            # EXP-ACCT-ACTIVE-STATUS PIC X(01)
    exp_acct_curr_bal: float = 0.0              # EXP-ACCT-CURR-BAL   PIC S9(10)V99 COMP-3
    exp_acct_credit_limit: float = 0.0          # EXP-ACCT-CREDIT-LIMIT PIC S9(10)V99
    exp_acct_cash_credit_limit: float = 0.0     # EXP-ACCT-CASH-CREDIT-LIMIT PIC S9(10)V99 COMP-3
    exp_acct_open_date: str = ""                # EXP-ACCT-OPEN-DATE  PIC X(10)
    exp_acct_expiration_date: str = ""          # EXP-ACCT-EXPIRAION-DATE PIC X(10)
    exp_acct_reissue_date: str = ""             # EXP-ACCT-REISSUE-DATE PIC X(10)
    exp_acct_curr_cyc_credit: float = 0.0       # EXP-ACCT-CURR-CYC-CREDIT PIC S9(10)V99
    exp_acct_curr_cyc_debit: float = 0.0        # EXP-ACCT-CURR-CYC-DEBIT PIC S9(10)V99 COMP
    exp_acct_addr_zip: str = ""                 # EXP-ACCT-ADDR-ZIP   PIC X(10)
    exp_acct_group_id: str = ""                 # EXP-ACCT-GROUP-ID   PIC X(10)


@dataclass
class ExportTransactionData:
    """Transaction sub-record within an export record (EXPORT-TRANSACTION-DATA)."""

    exp_tran_id: str = ""                       # EXP-TRAN-ID         PIC X(16)
    exp_tran_type_cd: str = ""                  # EXP-TRAN-TYPE-CD    PIC X(02)
    exp_tran_cat_cd: str = ""                   # EXP-TRAN-CAT-CD     PIC 9(04)
    exp_tran_source: str = ""                   # EXP-TRAN-SOURCE     PIC X(10)
    exp_tran_desc: str = ""                     # EXP-TRAN-DESC       PIC X(100)
    exp_tran_amt: float = 0.0                   # EXP-TRAN-AMT        PIC S9(09)V99 COMP-3
    exp_tran_merchant_id: int = 0               # EXP-TRAN-MERCHANT-ID PIC 9(09) COMP
    exp_tran_merchant_name: str = ""            # EXP-TRAN-MERCHANT-NAME PIC X(50)
    exp_tran_merchant_city: str = ""            # EXP-TRAN-MERCHANT-CITY PIC X(50)
    exp_tran_merchant_zip: str = ""             # EXP-TRAN-MERCHANT-ZIP PIC X(10)
    exp_tran_card_num: str = ""                 # EXP-TRAN-CARD-NUM   PIC X(16)
    exp_tran_orig_ts: str = ""                  # EXP-TRAN-ORIG-TS    PIC X(26)
    exp_tran_proc_ts: str = ""                  # EXP-TRAN-PROC-TS    PIC X(26)


@dataclass
class ExportCardXrefData:
    """Card cross-reference sub-record within an export record (EXPORT-CARD-XREF-DATA)."""

    exp_xref_card_num: str = ""                 # EXP-XREF-CARD-NUM   PIC X(16)
    exp_xref_cust_id: str = ""                  # EXP-XREF-CUST-ID    PIC 9(09)
    exp_xref_acct_id: int = 0                   # EXP-XREF-ACCT-ID    PIC 9(11) COMP


@dataclass
class ExportCardData:
    """Card sub-record within an export record (EXPORT-CARD-DATA)."""

    exp_card_num: str = ""                      # EXP-CARD-NUM        PIC X(16)
    exp_card_acct_id: int = 0                   # EXP-CARD-ACCT-ID    PIC 9(11) COMP
    exp_card_cvv_cd: int = 0                    # EXP-CARD-CVV-CD     PIC 9(03) COMP
    exp_card_embossed_name: str = ""            # EXP-CARD-EMBOSSED-NAME PIC X(50)
    exp_card_expiration_date: str = ""          # EXP-CARD-EXPIRAION-DATE PIC X(10)
    exp_card_active_status: str = ""            # EXP-CARD-ACTIVE-STATUS PIC X(01)


# Record type constants
EXPORT_REC_TYPE_CUSTOMER = "C"
EXPORT_REC_TYPE_ACCOUNT = "A"
EXPORT_REC_TYPE_TRANSACTION = "T"
EXPORT_REC_TYPE_CARD_XREF = "X"
EXPORT_REC_TYPE_CARD = "D"


@dataclass
class ExportRecord:
    """Top-level export record (CVEXPORT.cpy — 500-byte record).

    The ``record_data`` field holds one of the typed sub-record variants
    depending on the value of ``export_rec_type``.
    """

    export_rec_type: str = ""                   # EXPORT-REC-TYPE     PIC X(1)
    export_timestamp: str = ""                  # EXPORT-TIMESTAMP    PIC X(26)
    export_sequence_num: int = 0                # EXPORT-SEQUENCE-NUM PIC 9(9) COMP
    export_branch_id: str = ""                  # EXPORT-BRANCH-ID    PIC X(4)
    export_region_code: str = ""                # EXPORT-REGION-CODE  PIC X(5)

    # Union field — one of the typed sub-record dataclasses
    record_data: (
        ExportCustomerData
        | ExportAccountData
        | ExportTransactionData
        | ExportCardXrefData
        | ExportCardData
        | None
    ) = None

    @property
    def export_date(self) -> str:
        """Extract the date portion (first 10 chars) from the timestamp."""
        return self.export_timestamp[:10] if len(self.export_timestamp) >= 10 else ""

    @property
    def export_time(self) -> str:
        """Extract the time portion (chars 11-26) from the timestamp."""
        return self.export_timestamp[11:] if len(self.export_timestamp) > 11 else ""
