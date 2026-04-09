"""
Report formatting structures for the daily transaction report.

Translated from CVTRA07Y.cpy — header, detail-line, and summary
structures used by the batch report program (CBTRN02C / CREASTMT).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ReportNameHeader:
    """Report title / name header (REPORT-NAME-HEADER).

    Contains the short name, long name, date range header text, and
    placeholders for start/end dates.
    """

    rept_short_name: str = "DALYREPT"
    rept_long_name: str = "Daily Transaction Report"
    rept_date_header: str = "Date Range: "
    rept_start_date: str = ""           # PIC X(10) — filled at runtime
    rept_end_date: str = ""             # PIC X(10) — filled at runtime

    def format_header(self) -> str:
        """Return the formatted report header line."""
        return (
            f"{self.rept_short_name:<38}"
            f"{self.rept_long_name:<41}"
            f"{self.rept_date_header}"
            f"{self.rept_start_date}"
            f" to "
            f"{self.rept_end_date}"
        )


# Column headers (TRANSACTION-HEADER-1)
TRANSACTION_HEADER_1 = (
    f"{'Transaction ID':<17}"
    f"{'Account ID':<12}"
    f"{'Transaction Type':<19}"
    f"{'Tran Category':<35}"
    f"{'Tran Source':<14}"
    " "
    f"{'Amount':>16}"
)

# Separator line (TRANSACTION-HEADER-2)
TRANSACTION_HEADER_2 = "-" * 133


@dataclass
class TransactionDetailReport:
    """Single transaction detail line (TRANSACTION-DETAIL-REPORT)."""

    tran_report_trans_id: str = ""      # PIC X(16)
    tran_report_account_id: str = ""    # PIC X(11)
    tran_report_type_cd: str = ""       # PIC X(02)
    tran_report_type_desc: str = ""     # PIC X(15)
    tran_report_cat_cd: str = ""        # PIC 9(04)
    tran_report_cat_desc: str = ""      # PIC X(29)
    tran_report_source: str = ""        # PIC X(10)
    tran_report_amt: float = 0.0        # PIC -ZZZ,ZZZ,ZZZ.ZZ

    def format_line(self) -> str:
        """Return a formatted detail line matching the COBOL report layout."""
        return (
            f"{self.tran_report_trans_id:<16} "
            f"{self.tran_report_account_id:<11} "
            f"{self.tran_report_type_cd}-{self.tran_report_type_desc:<15} "
            f"{self.tran_report_cat_cd}-{self.tran_report_cat_desc:<29} "
            f"{self.tran_report_source:<10}    "
            f"{self.tran_report_amt:>16,.2f}  "
        )


@dataclass
class ReportPageTotals:
    """Page total line (REPORT-PAGE-TOTALS)."""

    rept_page_total: float = 0.0        # PIC +ZZZ,ZZZ,ZZZ.ZZ

    def format_line(self) -> str:
        """Return the formatted page total line."""
        label = "Page Total"
        dots = "." * 86
        return f"{label:<11}{dots}{self.rept_page_total:>+16,.2f}"


@dataclass
class ReportAccountTotals:
    """Account total line (REPORT-ACCOUNT-TOTALS)."""

    rept_account_total: float = 0.0     # PIC +ZZZ,ZZZ,ZZZ.ZZ

    def format_line(self) -> str:
        """Return the formatted account total line."""
        label = "Account Total"
        dots = "." * 84
        return f"{label:<13}{dots}{self.rept_account_total:>+16,.2f}"


@dataclass
class ReportGrandTotals:
    """Grand total line (REPORT-GRAND-TOTALS)."""

    rept_grand_total: float = 0.0       # PIC +ZZZ,ZZZ,ZZZ.ZZ

    def format_line(self) -> str:
        """Return the formatted grand total line."""
        label = "Grand Total"
        dots = "." * 86
        return f"{label:<11}{dots}{self.rept_grand_total:>+16,.2f}"
