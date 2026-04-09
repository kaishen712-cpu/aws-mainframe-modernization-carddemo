"""
Unit tests for cotrn00c.py — the Python translation of COTRN00C.CBL.

These tests verify the same business rules that the original COBOL program
enforces, organised by functional area.
"""

import unittest

from cotrn00c import (
    InMemoryTransactionRepository,
    TransactionRecord,
    build_display_row,
    format_tran_amount,
    format_tran_date,
    get_header_info,
    list_transactions_backward,
    list_transactions_forward,
    process_enter_key,
    process_pf7,
    process_pf8,
    validate_selection,
    validate_tran_id_filter,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_repo(count: int = 25) -> InMemoryTransactionRepository:
    """Return a repo pre-loaded with `count` transactions."""
    repo = InMemoryTransactionRepository()
    for i in range(1, count + 1):
        repo.add_transaction(
            TransactionRecord(
                tran_id=str(i).zfill(16),
                tran_type_cd="01",
                tran_cat_cd="5000",
                tran_source="ONLINE",
                tran_desc=f"Transaction {i}",
                tran_amt=float(i) * 10.0,
                tran_merchant_id="123456789",
                tran_merchant_name="ACME Store",
                tran_merchant_city="Seattle",
                tran_merchant_zip="98101",
                tran_card_num="4000123456789010",
                tran_orig_ts=f"2024-06-{min(i, 28):02d} 12:00:00.000000",
                tran_proc_ts=f"2024-06-{min(i, 28):02d} 12:00:00.000000",
            )
        )
    return repo


# ===========================================================================
# 1. Transaction ID filter validation
# ===========================================================================

class TestValidateTranIdFilter(unittest.TestCase):
    """Tests for the transaction ID filter input."""

    def test_empty_filter_is_valid(self):
        is_valid, norm, err = validate_tran_id_filter("")
        self.assertTrue(is_valid)
        self.assertEqual(norm, "")
        self.assertEqual(err, "")

    def test_spaces_filter_is_valid(self):
        is_valid, norm, err = validate_tran_id_filter("   ")
        self.assertTrue(is_valid)
        self.assertEqual(norm, "")

    def test_numeric_filter_is_valid(self):
        is_valid, norm, err = validate_tran_id_filter("42")
        self.assertTrue(is_valid)
        self.assertEqual(norm, "0000000000000042")
        self.assertEqual(err, "")

    def test_non_numeric_filter_is_invalid(self):
        is_valid, norm, err = validate_tran_id_filter("ABC")
        self.assertFalse(is_valid)
        self.assertIn("Tran ID must be Numeric", err)

    def test_mixed_alphanumeric_is_invalid(self):
        is_valid, norm, err = validate_tran_id_filter("12AB")
        self.assertFalse(is_valid)
        self.assertIn("Tran ID must be Numeric", err)

    def test_zero_padded_input(self):
        is_valid, norm, err = validate_tran_id_filter("0000000000000001")
        self.assertTrue(is_valid)
        self.assertEqual(norm, "0000000000000001")


# ===========================================================================
# 2. Selection validation
# ===========================================================================

class TestValidateSelection(unittest.TestCase):
    """Tests for row selection flag validation."""

    def test_s_uppercase_is_valid(self):
        is_valid, err = validate_selection("S")
        self.assertTrue(is_valid)
        self.assertEqual(err, "")

    def test_s_lowercase_is_valid(self):
        is_valid, err = validate_selection("s")
        self.assertTrue(is_valid)

    def test_empty_is_valid(self):
        is_valid, err = validate_selection("")
        self.assertTrue(is_valid)

    def test_spaces_is_valid(self):
        is_valid, err = validate_selection("   ")
        self.assertTrue(is_valid)

    def test_invalid_selection(self):
        is_valid, err = validate_selection("X")
        self.assertFalse(is_valid)
        self.assertIn("Invalid selection", err)

    def test_digit_selection_is_invalid(self):
        is_valid, err = validate_selection("1")
        self.assertFalse(is_valid)
        self.assertIn("Invalid selection", err)


# ===========================================================================
# 3. Display formatting
# ===========================================================================

class TestFormatting(unittest.TestCase):
    """Tests for date and amount formatting."""

    def test_format_tran_date_normal(self):
        result = format_tran_date("2024-06-15 12:00:00.000000")
        self.assertEqual(result, "06/15/24")

    def test_format_tran_date_short_timestamp(self):
        result = format_tran_date("2024-01-05")
        self.assertEqual(result, "01/05/24")

    def test_format_tran_date_empty(self):
        result = format_tran_date("")
        self.assertEqual(result, "00/00/00")

    def test_format_tran_date_none_like(self):
        result = format_tran_date("short")
        self.assertEqual(result, "00/00/00")

    def test_format_tran_amount_positive(self):
        result = format_tran_amount(100.50)
        self.assertEqual(result, "+00000100.50")

    def test_format_tran_amount_negative(self):
        result = format_tran_amount(-25.00)
        self.assertEqual(result, "-00000025.00")

    def test_format_tran_amount_zero(self):
        result = format_tran_amount(0.0)
        self.assertEqual(result, "+00000000.00")

    def test_build_display_row(self):
        record = TransactionRecord(
            tran_id="0000000000000001",
            tran_desc="Test purchase",
            tran_amt=100.50,
            tran_orig_ts="2024-06-15 12:00:00.000000",
        )
        row = build_display_row(record)
        self.assertEqual(row.tran_id, "0000000000000001")
        self.assertEqual(row.tran_date, "06/15/24")
        self.assertEqual(row.tran_desc, "Test purchase")
        self.assertEqual(row.tran_amt, "+00000100.50")


# ===========================================================================
# 4. Forward pagination
# ===========================================================================

class TestListTransactionsForward(unittest.TestCase):
    """Tests for forward pagination."""

    def test_first_page(self):
        repo = _make_repo(25)
        page = list_transactions_forward(repo, "", 0)
        self.assertEqual(len(page.rows), 10)
        self.assertEqual(page.page_num, 1)
        self.assertTrue(page.has_next_page)
        self.assertEqual(page.first_tran_id, "0000000000000001")
        self.assertEqual(page.last_tran_id, "0000000000000010")

    def test_second_page(self):
        repo = _make_repo(25)
        page = list_transactions_forward(repo, "0000000000000011", 1)
        self.assertEqual(len(page.rows), 10)
        self.assertEqual(page.page_num, 2)
        self.assertTrue(page.has_next_page)
        self.assertEqual(page.first_tran_id, "0000000000000011")

    def test_last_page_partial(self):
        repo = _make_repo(25)
        page = list_transactions_forward(repo, "0000000000000021", 2)
        self.assertEqual(len(page.rows), 5)
        self.assertEqual(page.page_num, 3)
        self.assertFalse(page.has_next_page)

    def test_empty_repo(self):
        repo = InMemoryTransactionRepository()
        page = list_transactions_forward(repo, "", 0)
        self.assertEqual(len(page.rows), 0)
        self.assertIn("bottom", page.message.lower())

    def test_start_id_beyond_all(self):
        repo = _make_repo(5)
        page = list_transactions_forward(repo, "9999999999999999", 0)
        self.assertEqual(len(page.rows), 0)

    def test_exact_page_boundary(self):
        """When record count is exactly a multiple of PAGE_SIZE."""
        repo = _make_repo(10)
        page = list_transactions_forward(repo, "", 0)
        self.assertEqual(len(page.rows), 10)
        self.assertFalse(page.has_next_page)


# ===========================================================================
# 5. Backward pagination
# ===========================================================================

class TestListTransactionsBackward(unittest.TestCase):
    """Tests for backward pagination."""

    def test_backward_from_middle(self):
        repo = _make_repo(25)
        page = list_transactions_backward(repo, "0000000000000010", 2)
        self.assertEqual(len(page.rows), 10)
        self.assertEqual(page.page_num, 1)
        self.assertTrue(page.has_next_page)

    def test_backward_from_beginning(self):
        repo = _make_repo(5)
        page = list_transactions_backward(repo, "0000000000000005", 1)
        self.assertEqual(len(page.rows), 5)

    def test_backward_empty_repo(self):
        repo = InMemoryTransactionRepository()
        page = list_transactions_backward(repo, "", 1)
        self.assertEqual(len(page.rows), 0)
        self.assertIn("top", page.message.lower())


# ===========================================================================
# 6. Process Enter Key
# ===========================================================================

class TestProcessEnterKey(unittest.TestCase):
    """Tests for the Enter key processing."""

    def test_enter_with_no_filter_loads_first_page(self):
        repo = _make_repo(15)
        sel_result, page = process_enter_key(repo, "")
        self.assertIsNone(sel_result)
        self.assertIsNotNone(page)
        self.assertEqual(len(page.rows), 10)
        self.assertEqual(page.page_num, 1)

    def test_enter_with_numeric_filter(self):
        repo = _make_repo(25)
        sel_result, page = process_enter_key(repo, "11")
        self.assertIsNone(sel_result)
        self.assertIsNotNone(page)
        self.assertEqual(page.first_tran_id, "0000000000000011")

    def test_enter_with_invalid_filter(self):
        repo = _make_repo(10)
        sel_result, page = process_enter_key(repo, "ABC")
        self.assertIsNone(sel_result)
        self.assertIsNotNone(page)
        self.assertIn("Numeric", page.message)

    def test_enter_with_valid_selection(self):
        repo = _make_repo(10)
        selections = [("S", "0000000000000005")]
        sel_result, page = process_enter_key(repo, "", selections)
        self.assertIsNotNone(sel_result)
        self.assertIsNone(page)
        self.assertTrue(sel_result.selected)
        self.assertEqual(sel_result.tran_id, "0000000000000005")
        self.assertEqual(sel_result.transfer_program, "COTRN01C")

    def test_enter_with_invalid_selection(self):
        repo = _make_repo(10)
        selections = [("X", "0000000000000005")]
        sel_result, page = process_enter_key(repo, "", selections)
        self.assertIsNotNone(sel_result)
        self.assertFalse(sel_result.selected)
        self.assertIn("Invalid selection", sel_result.error_message)

    def test_enter_with_empty_selections(self):
        repo = _make_repo(10)
        selections = [("", ""), ("", "")]
        sel_result, page = process_enter_key(repo, "", selections)
        self.assertIsNone(sel_result)
        self.assertIsNotNone(page)


# ===========================================================================
# 7. PF7 / PF8 keys
# ===========================================================================

class TestPF7PF8(unittest.TestCase):
    """Tests for page backward/forward key handling."""

    def test_pf7_at_page_1_shows_message(self):
        repo = _make_repo(25)
        page = process_pf7(repo, "0000000000000001", 1)
        self.assertIn("top", page.message.lower())
        self.assertEqual(page.page_num, 1)

    def test_pf7_at_page_2_goes_back(self):
        repo = _make_repo(25)
        page = process_pf7(repo, "0000000000000011", 2)
        self.assertEqual(len(page.rows), 10)
        self.assertEqual(page.page_num, 1)

    def test_pf8_with_next_page(self):
        repo = _make_repo(25)
        page = process_pf8(repo, "0000000000000010", 1, True)
        self.assertEqual(len(page.rows), 10)
        self.assertEqual(page.page_num, 2)

    def test_pf8_at_end_shows_message(self):
        repo = _make_repo(10)
        page = process_pf8(repo, "0000000000000010", 1, False)
        self.assertIn("bottom", page.message.lower())
        self.assertEqual(page.page_num, 1)


# ===========================================================================
# 8. Header info
# ===========================================================================

class TestHeaderInfo(unittest.TestCase):
    """Tests for header information generation."""

    def test_header_contains_required_fields(self):
        info = get_header_info()
        self.assertIn("title01", info)
        self.assertIn("title02", info)
        self.assertIn("transaction_id", info)
        self.assertIn("program_name", info)
        self.assertIn("current_date", info)
        self.assertIn("current_time", info)
        self.assertEqual(info["program_name"], "COTRN00C")
        self.assertEqual(info["transaction_id"], "CT00")


# ===========================================================================
# 9. Edge cases
# ===========================================================================

class TestEdgeCases(unittest.TestCase):
    """Edge case tests."""

    def test_single_transaction(self):
        repo = InMemoryTransactionRepository()
        repo.add_transaction(
            TransactionRecord(
                tran_id="0000000000000001",
                tran_desc="Only one",
                tran_amt=50.0,
                tran_orig_ts="2024-01-01 00:00:00.000000",
            )
        )
        page = list_transactions_forward(repo, "", 0)
        self.assertEqual(len(page.rows), 1)
        self.assertFalse(page.has_next_page)
        self.assertEqual(page.page_num, 1)

    def test_format_date_with_unusual_timestamp(self):
        """Timestamp without time part."""
        result = format_tran_date("2024-12-31")
        self.assertEqual(result, "12/31/24")

    def test_large_amount_formatting(self):
        result = format_tran_amount(99999999.99)
        self.assertEqual(result, "+99999999.99")

    def test_selection_with_lowercase_s(self):
        repo = _make_repo(10)
        selections = [("s", "0000000000000003")]
        sel_result, page = process_enter_key(repo, "", selections)
        self.assertIsNotNone(sel_result)
        self.assertTrue(sel_result.selected)
        self.assertEqual(sel_result.tran_id, "0000000000000003")

    def test_multiple_selections_takes_first(self):
        """If multiple rows are selected, the first one is processed."""
        repo = _make_repo(10)
        selections = [
            ("S", "0000000000000001"),
            ("S", "0000000000000002"),
        ]
        sel_result, page = process_enter_key(repo, "", selections)
        self.assertIsNotNone(sel_result)
        self.assertEqual(sel_result.tran_id, "0000000000000001")


if __name__ == "__main__":
    unittest.main()
