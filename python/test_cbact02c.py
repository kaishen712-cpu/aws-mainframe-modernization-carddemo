"""
Unit tests for CBACT02C — Print Card Data.

Tests cover:
- Empty repository (no cards)
- Single card record formatting
- Multiple card records
- Start/end banners
- Field formatting and trimming
"""

from __future__ import annotations

import unittest

from cbact02c import (
    CardRecord,
    InMemoryCardRepository,
    format_card_record,
    print_card_data,
    PROGRAM_NAME,
)


def _make_card(**overrides: object) -> CardRecord:
    """Create a CardRecord with sensible defaults."""
    defaults = dict(
        card_num="4111111111111111",
        card_acct_id="00000000001",
        card_cvv_cd="123",
        card_embossed_name="JOHN DOE",
        card_expiration_date="2025-12-31",
        card_active_status="Y",
    )
    defaults.update(overrides)
    return CardRecord(**defaults)  # type: ignore[arg-type]


class TestFormatCardRecord(unittest.TestCase):
    """Tests for the format_card_record function."""

    def test_basic_formatting(self) -> None:
        card = _make_card()
        line = format_card_record(card)
        self.assertIn("4111111111111111", line)
        self.assertIn("00000000001", line)
        self.assertIn("123", line)
        self.assertIn("JOHN DOE", line)
        self.assertIn("2025-12-31", line)
        self.assertIn("Y", line)

    def test_name_trimmed(self) -> None:
        card = _make_card(card_embossed_name="JANE SMITH              ")
        line = format_card_record(card)
        self.assertIn("JANE SMITH", line)
        self.assertNotIn("JANE SMITH              ", line)

    def test_inactive_status(self) -> None:
        card = _make_card(card_active_status="N")
        line = format_card_record(card)
        self.assertIn("Status: N", line)


class TestPrintCardData(unittest.TestCase):
    """Tests for the print_card_data main function."""

    def test_empty_repo(self) -> None:
        repo = InMemoryCardRepository()
        lines = print_card_data(repo)
        self.assertEqual(len(lines), 2)
        self.assertIn(PROGRAM_NAME, lines[0])
        self.assertIn("START", lines[0])
        self.assertIn("END", lines[1])

    def test_single_card(self) -> None:
        repo = InMemoryCardRepository()
        repo.add_card(_make_card())
        lines = print_card_data(repo)
        self.assertEqual(len(lines), 3)
        self.assertIn("START", lines[0])
        self.assertIn("4111111111111111", lines[1])
        self.assertIn("END", lines[2])

    def test_multiple_cards(self) -> None:
        repo = InMemoryCardRepository()
        repo.add_card(_make_card(card_num="1111111111111111"))
        repo.add_card(_make_card(card_num="2222222222222222"))
        repo.add_card(_make_card(card_num="3333333333333333"))
        lines = print_card_data(repo)
        self.assertEqual(len(lines), 5)  # start + 3 cards + end
        self.assertIn("1111111111111111", lines[1])
        self.assertIn("2222222222222222", lines[2])
        self.assertIn("3333333333333333", lines[3])

    def test_banners_contain_program_name(self) -> None:
        repo = InMemoryCardRepository()
        lines = print_card_data(repo)
        self.assertIn(PROGRAM_NAME, lines[0])
        self.assertIn(PROGRAM_NAME, lines[-1])


if __name__ == "__main__":
    unittest.main()
