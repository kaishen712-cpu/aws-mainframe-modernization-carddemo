"""
CardDemo data models package.

Python dataclass representations of all VSAM record types,
communication areas, export structures, and report formats
derived from the COBOL copybooks in app/cpy/.
"""

from python.models.records import (
    AccountRecord,
    CardRecord,
    CardXrefRecord,
    CustomerRecord,
    TransactionRecord,
    DailyTransactionRecord,
    TranCatBalRecord,
    DisclosureGroupRecord,
    TransactionTypeRecord,
    TransactionCategoryRecord,
    UserSecurityRecord,
    TransactionIndexRecord,
)
from python.models.commarea import CardDemoCommarea
from python.models.export_record import (
    ExportRecord,
    ExportCustomerData,
    ExportAccountData,
    ExportTransactionData,
    ExportCardXrefData,
    ExportCardData,
)
from python.models.report import (
    ReportNameHeader,
    TransactionDetailReport,
    ReportPageTotals,
    ReportAccountTotals,
    ReportGrandTotals,
)

__all__ = [
    "AccountRecord",
    "CardRecord",
    "CardXrefRecord",
    "CustomerRecord",
    "TransactionRecord",
    "DailyTransactionRecord",
    "TranCatBalRecord",
    "DisclosureGroupRecord",
    "TransactionTypeRecord",
    "TransactionCategoryRecord",
    "UserSecurityRecord",
    "TransactionIndexRecord",
    "CardDemoCommarea",
    "ExportRecord",
    "ExportCustomerData",
    "ExportAccountData",
    "ExportTransactionData",
    "ExportCardXrefData",
    "ExportCardData",
    "ReportNameHeader",
    "TransactionDetailReport",
    "ReportPageTotals",
    "ReportAccountTotals",
    "ReportGrandTotals",
]
