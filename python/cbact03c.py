"""
CBACT03C - Print Card Cross-Reference Data (Python Translation)

Translated from the COBOL program CBACT03C.CBL in the AWS CardDemo
mainframe modernization project. This module reads card cross-reference
records and produces formatted output lines for each record.

Original: Batch COBOL program reading a VSAM KSDS cross-reference file
sequentially and printing each record via DISPLAY.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROGRAM_NAME = "CBACT03C"


# ---------------------------------------------------------------------------
# Data structures (from copybook CVACT03Y — card xref, RECLN 50)
# ---------------------------------------------------------------------------

@dataclass
class CardXrefRecord:
    """Card cross-reference record layout (CVACT03Y - 50 bytes)."""
    xref_card_num: str = ""   # PIC X(16)
    xref_cust_id: str = ""    # PIC 9(09)
    xref_acct_id: str = ""    # PIC 9(11)


# ---------------------------------------------------------------------------
# Repository interface
# ---------------------------------------------------------------------------

class XrefRepository:
    """
    Abstract interface for card cross-reference data access.

    In the original COBOL program this is a sequential read of a VSAM
    KSDS file. Concrete implementations can use any data source.
    """

    def get_all_xrefs(self) -> List[CardXrefRecord]:
        """Return all cross-reference records in sequential order."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# In-memory repository for testing
# ---------------------------------------------------------------------------

class InMemoryXrefRepository(XrefRepository):
    """Simple in-memory implementation backed by a list."""

    def __init__(self) -> None:
        self.xrefs: List[CardXrefRecord] = []

    def add_xref(self, record: CardXrefRecord) -> None:
        """Add a cross-reference record."""
        self.xrefs.append(record)

    def get_all_xrefs(self) -> List[CardXrefRecord]:
        return list(self.xrefs)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def format_xref_record(record: CardXrefRecord) -> str:
    """
    Format a single cross-reference record as a display line.

    Mirrors the COBOL DISPLAY CARD-XREF-RECORD statement.
    """
    return (
        f"Card Num: {record.xref_card_num}  "
        f"Cust ID: {record.xref_cust_id}  "
        f"Acct ID: {record.xref_acct_id}"
    )


def print_card_xref_data(repo: XrefRepository) -> List[str]:
    """
    Read all cross-reference records and produce formatted output lines.

    This is the main entry point corresponding to the COBOL program's
    PROCEDURE DIVISION. Returns a list of formatted strings (one per line)
    rather than writing to stdout.

    Args:
        repo: An XrefRepository providing cross-reference records.

    Returns:
        A list of formatted output lines including start/end banners.
    """
    lines: List[str] = []
    lines.append(f"START OF EXECUTION OF PROGRAM {PROGRAM_NAME}")

    xrefs = repo.get_all_xrefs()
    for xref in xrefs:
        lines.append(format_xref_record(xref))

    lines.append(f"END OF EXECUTION OF PROGRAM {PROGRAM_NAME}")
    return lines
