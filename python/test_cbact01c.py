"""
Unit tests for CBACT01C — Read Accounts & Write Output.

Tests cover:
- Date formatting (replacing COBDATFT assembler)
- Account display formatting
- Output record building with date reformatting and default debit
- Array record building with fixed balance/debit slots
- Variable-length record building
- Full batch processing with multiple accounts
"""

from __future__ import annotations

import unittest

from cbact01c import (
    AccountRecord,
    InMemoryAccountRepository,
    build_array_record,
    build_output_account_record,
    build_vbrc_records,
    format_account_display,
    format_date_cobdatft,
    process_accounts,
    PROGRAM_NAME,
)


def _make_account(**overrides: object) -> AccountRecord:
    """Create an AccountRecord with sensible defaults."""
    defaults = dict(
        acct_id="00000000001",
        acct_active_status="Y",
        acct_curr_bal=5000.00,
        acct_credit_limit=10000.00,
        acct_cash_credit_limit=2000.00,
        acct_open_date="2020-01-15",
        acct_expiration_date="2025-12-31",
        acct_reissue_date="2023-06-01",
        acct_curr_cyc_credit=1000.00,
        acct_curr_cyc_debit=500.00,
        acct_addr_zip="10001",
        acct_group_id="GRP001",
    )
    defaults.update(overrides)
    return AccountRecord(**defaults)  # type: ignore[arg-type]


class TestFormatDateCobdatft(unittest.TestCase):
    """Tests for the format_date_cobdatft function (COBDATFT replacement)."""

    def test_yyyymmdd_to_formatted(self) -> None:
        result = format_date_cobdatft("20230615", input_type="1", output_type="1")
        self.assertEqual(result, "2023-06-15")

    def test_yyyy_mm_dd_to_compact(self) -> None:
        result = format_date_cobdatft("2023-06-15", input_type="2", output_type="2")
        self.assertEqual(result, "20230615")

    def test_yyyy_mm_dd_to_formatted(self) -> None:
        result = format_date_cobdatft("2023-06-15", input_type="2", output_type="1")
        self.assertEqual(result, "2023-06-15")

    def test_yyyymmdd_to_compact(self) -> None:
        result = format_date_cobdatft("20230615", input_type="1", output_type="2")
        self.assertEqual(result, "20230615")

    def test_invalid_date_returns_original(self) -> None:
        result = format_date_cobdatft("NOT-A-DATE", input_type="2", output_type="1")
        self.assertEqual(result, "NOT-A-DATE")

    def test_empty_string_returns_original(self) -> None:
        result = format_date_cobdatft("", input_type="1", output_type="1")
        self.assertEqual(result, "")

    def test_short_string_returns_original(self) -> None:
        result = format_date_cobdatft("2023", input_type="1", output_type="1")
        self.assertEqual(result, "2023")


class TestFormatAccountDisplay(unittest.TestCase):
    """Tests for the format_account_display function."""

    def test_display_contains_all_fields(self) -> None:
        acct = _make_account()
        lines = format_account_display(acct)
        self.assertTrue(any("00000000001" in l for l in lines))
        self.assertTrue(any("Y" in l for l in lines))
        self.assertTrue(any("5000" in l for l in lines))
        self.assertTrue(any("10000" in l for l in lines))
        self.assertTrue(any("2020-01-15" in l for l in lines))
        self.assertTrue(any("GRP001" in l for l in lines))

    def test_display_ends_with_separator(self) -> None:
        acct = _make_account()
        lines = format_account_display(acct)
        self.assertTrue(lines[-1].startswith("-"))

    def test_display_line_count(self) -> None:
        acct = _make_account()
        lines = format_account_display(acct)
        # 11 field lines + 1 separator
        self.assertEqual(len(lines), 12)


class TestBuildOutputAccountRecord(unittest.TestCase):
    """Tests for the build_output_account_record function."""

    def test_basic_fields_copied(self) -> None:
        acct = _make_account()
        out = build_output_account_record(acct)
        self.assertEqual(out.acct_id, "00000000001")
        self.assertEqual(out.acct_active_status, "Y")
        self.assertEqual(out.acct_curr_bal, 5000.00)
        self.assertEqual(out.acct_credit_limit, 10000.00)

    def test_reissue_date_reformatted(self) -> None:
        acct = _make_account(acct_reissue_date="2023-06-01")
        out = build_output_account_record(acct)
        self.assertEqual(out.acct_reissue_date, "20230601")

    def test_zero_debit_defaults_to_2525(self) -> None:
        acct = _make_account(acct_curr_cyc_debit=0.0)
        out = build_output_account_record(acct)
        self.assertEqual(out.acct_curr_cyc_debit, 2525.00)

    def test_nonzero_debit_preserved(self) -> None:
        acct = _make_account(acct_curr_cyc_debit=750.00)
        out = build_output_account_record(acct)
        self.assertEqual(out.acct_curr_cyc_debit, 750.00)


class TestBuildArrayRecord(unittest.TestCase):
    """Tests for the build_array_record function."""

    def test_acct_id_copied(self) -> None:
        acct = _make_account()
        arr = build_array_record(acct)
        self.assertEqual(arr.acct_id, "00000000001")

    def test_first_balance_slot(self) -> None:
        acct = _make_account(acct_curr_bal=5000.00)
        arr = build_array_record(acct)
        self.assertEqual(arr.balances[0], 5000.00)
        self.assertEqual(arr.debits[0], 1005.00)

    def test_second_balance_slot(self) -> None:
        acct = _make_account(acct_curr_bal=5000.00)
        arr = build_array_record(acct)
        self.assertEqual(arr.balances[1], 5000.00)
        self.assertEqual(arr.debits[1], 1525.00)

    def test_third_slot_negative(self) -> None:
        acct = _make_account()
        arr = build_array_record(acct)
        self.assertEqual(arr.balances[2], -1025.00)
        self.assertEqual(arr.debits[2], -2500.00)

    def test_remaining_slots_zero(self) -> None:
        acct = _make_account()
        arr = build_array_record(acct)
        self.assertEqual(arr.balances[3], 0.0)
        self.assertEqual(arr.debits[3], 0.0)
        self.assertEqual(arr.balances[4], 0.0)
        self.assertEqual(arr.debits[4], 0.0)


class TestBuildVbrcRecords(unittest.TestCase):
    """Tests for the build_vbrc_records function."""

    def test_vbrc1_fields(self) -> None:
        acct = _make_account()
        vb1, _ = build_vbrc_records(acct)
        self.assertEqual(vb1.acct_id, "00000000001")
        self.assertEqual(vb1.acct_active_status, "Y")

    def test_vbrc2_fields(self) -> None:
        acct = _make_account()
        _, vb2 = build_vbrc_records(acct)
        self.assertEqual(vb2.acct_id, "00000000001")
        self.assertEqual(vb2.acct_curr_bal, 5000.00)
        self.assertEqual(vb2.acct_credit_limit, 10000.00)
        self.assertEqual(vb2.acct_reissue_yyyy, "2023")

    def test_short_reissue_date(self) -> None:
        acct = _make_account(acct_reissue_date="20")
        _, vb2 = build_vbrc_records(acct)
        self.assertEqual(vb2.acct_reissue_yyyy, "20")

    def test_empty_reissue_date(self) -> None:
        acct = _make_account(acct_reissue_date="")
        _, vb2 = build_vbrc_records(acct)
        self.assertEqual(vb2.acct_reissue_yyyy, "")


class TestProcessAccounts(unittest.TestCase):
    """Tests for the process_accounts main batch function."""

    def test_empty_repo(self) -> None:
        repo = InMemoryAccountRepository()
        result = process_accounts(repo)
        self.assertEqual(len(result.display_lines), 2)
        self.assertIn("START", result.display_lines[0])
        self.assertIn("END", result.display_lines[-1])
        self.assertEqual(len(result.output_records), 0)

    def test_single_account(self) -> None:
        repo = InMemoryAccountRepository()
        repo.add_account(_make_account())
        result = process_accounts(repo)
        self.assertEqual(len(result.output_records), 1)
        self.assertEqual(len(result.array_records), 1)
        self.assertEqual(len(result.vbrc_records_1), 1)
        self.assertEqual(len(result.vbrc_records_2), 1)

    def test_multiple_accounts(self) -> None:
        repo = InMemoryAccountRepository()
        repo.add_account(_make_account(acct_id="00000000001"))
        repo.add_account(_make_account(acct_id="00000000002"))
        repo.add_account(_make_account(acct_id="00000000003"))
        result = process_accounts(repo)
        self.assertEqual(len(result.output_records), 3)
        self.assertEqual(len(result.array_records), 3)

    def test_display_lines_include_all_accounts(self) -> None:
        repo = InMemoryAccountRepository()
        repo.add_account(_make_account(acct_id="00000000001"))
        repo.add_account(_make_account(acct_id="00000000002"))
        result = process_accounts(repo)
        all_text = "\n".join(result.display_lines)
        self.assertIn("00000000001", all_text)
        self.assertIn("00000000002", all_text)

    def test_banners_contain_program_name(self) -> None:
        repo = InMemoryAccountRepository()
        result = process_accounts(repo)
        self.assertIn(PROGRAM_NAME, result.display_lines[0])
        self.assertIn(PROGRAM_NAME, result.display_lines[-1])


if __name__ == "__main__":
    unittest.main()
