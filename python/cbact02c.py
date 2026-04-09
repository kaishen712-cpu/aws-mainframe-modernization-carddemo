"""
CBACT02C - Print Card Data (Python Translation)

Translated from the COBOL program CBACT02C.CBL in the AWS CardDemo
mainframe modernization project. This module reads card records and
produces formatted output lines for each card.

Original: Batch COBOL program reading a VSAM KSDS card file sequentially
and printing each record via DISPLAY.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROGRAM_NAME = "CBACT02C"


# ---------------------------------------------------------------------------
# Data structures (from copybook CVACT02Y — card entity, RECLN 150)
# ---------------------------------------------------------------------------

@dataclass
class CardRecord:
    """Card record layout (CVACT02Y - 150 bytes)."""
    card_num: str = ""              # PIC X(16)
    card_acct_id: str = ""          # PIC 9(11)
    card_cvv_cd: str = ""           # PIC 9(03)
    card_embossed_name: str = ""    # PIC X(50)
    card_expiration_date: str = ""  # PIC X(10)
    card_active_status: str = ""    # PIC X(01)


# ---------------------------------------------------------------------------
# Repository interface
# ---------------------------------------------------------------------------

class CardRepository:
    """
    Abstract interface for card data access.

    In the original COBOL program this is a sequential read of a VSAM
    KSDS file. Concrete implementations can use any data source.
    """

    def get_all_cards(self) -> List[CardRecord]:
        """Return all card records in sequential order."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# In-memory repository for testing
# ---------------------------------------------------------------------------

class InMemoryCardRepository(CardRepository):
    """Simple in-memory implementation backed by a list."""

    def __init__(self) -> None:
        self.cards: List[CardRecord] = []

    def add_card(self, record: CardRecord) -> None:
        """Add a card record."""
        self.cards.append(record)

    def get_all_cards(self) -> List[CardRecord]:
        return list(self.cards)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def format_card_record(record: CardRecord) -> str:
    """
    Format a single card record as a display line.

    Mirrors the COBOL DISPLAY CARD-RECORD statement which prints the
    entire record structure.
    """
    return (
        f"Card Num: {record.card_num}  "
        f"Acct ID: {record.card_acct_id}  "
        f"CVV: {record.card_cvv_cd}  "
        f"Name: {record.card_embossed_name.strip()}  "
        f"Exp: {record.card_expiration_date}  "
        f"Status: {record.card_active_status}"
    )


def print_card_data(repo: CardRepository) -> List[str]:
    """
    Read all card records and produce formatted output lines.

    This is the main entry point corresponding to the COBOL program's
    PROCEDURE DIVISION. Returns a list of formatted strings (one per line)
    rather than writing to stdout.

    Args:
        repo: A CardRepository providing card records.

    Returns:
        A list of formatted output lines including start/end banners.
    """
    lines: List[str] = []
    lines.append(f"START OF EXECUTION OF PROGRAM {PROGRAM_NAME}")

    cards = repo.get_all_cards()
    for card in cards:
        lines.append(format_card_record(card))

    lines.append(f"END OF EXECUTION OF PROGRAM {PROGRAM_NAME}")
    return lines
