"""
Unit tests for CBACT03C — Print Card Cross-Reference Data.

Tests cover:
- Empty repository (no xrefs)
- Single xref record formatting
- Multiple xref records
- Start/end banners
"""

from __future__ import annotations

import unittest

from cbact03c import (
    CardXrefRecord,
    InMemoryXrefRepository,
    format_xref_record,
    print_card_xref_data,
    PROGRAM_NAME,
)


def _make_xref(**overrides: object) -> CardXrefRecord:
    """Create a CardXrefRecord with sensible defaults."""
    defaults = dict(
        xref_card_num="4111111111111111",
        xref_cust_id="000000001",
        xref_acct_id="00000000001",
    )
    defaults.update(overrides)
    return CardXrefRecord(**defaults)  # type: ignore[arg-type]


class TestFormatXrefRecord(unittest.TestCase):
    """Tests for the format_xref_record function."""

    def test_basic_formatting(self) -> None:
        xref = _make_xref()
        line = format_xref_record(xref)
        self.assertIn("4111111111111111", line)
        self.assertIn("000000001", line)
        self.assertIn("00000000001", line)

    def test_all_fields_present(self) -> None:
        xref = _make_xref(
            xref_card_num="9999888877776666",
            xref_cust_id="123456789",
            xref_acct_id="98765432101",
        )
        line = format_xref_record(xref)
        self.assertIn("9999888877776666", line)
        self.assertIn("123456789", line)
        self.assertIn("98765432101", line)


class TestPrintCardXrefData(unittest.TestCase):
    """Tests for the print_card_xref_data main function."""

    def test_empty_repo(self) -> None:
        repo = InMemoryXrefRepository()
        lines = print_card_xref_data(repo)
        self.assertEqual(len(lines), 2)
        self.assertIn("START", lines[0])
        self.assertIn("END", lines[1])

    def test_single_xref(self) -> None:
        repo = InMemoryXrefRepository()
        repo.add_xref(_make_xref())
        lines = print_card_xref_data(repo)
        self.assertEqual(len(lines), 3)
        self.assertIn("4111111111111111", lines[1])

    def test_multiple_xrefs(self) -> None:
        repo = InMemoryXrefRepository()
        repo.add_xref(_make_xref(xref_card_num="1111111111111111"))
        repo.add_xref(_make_xref(xref_card_num="2222222222222222"))
        lines = print_card_xref_data(repo)
        self.assertEqual(len(lines), 4)  # start + 2 + end
        self.assertIn("1111111111111111", lines[1])
        self.assertIn("2222222222222222", lines[2])

    def test_banners_contain_program_name(self) -> None:
        repo = InMemoryXrefRepository()
        lines = print_card_xref_data(repo)
        self.assertIn(PROGRAM_NAME, lines[0])
        self.assertIn(PROGRAM_NAME, lines[-1])


if __name__ == "__main__":
    unittest.main()
