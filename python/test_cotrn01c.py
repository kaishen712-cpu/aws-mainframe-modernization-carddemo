"""
Unit tests for cotrn01c.py — the Python translation of COTRN01C.CBL.

These tests verify the same business rules that the original COBOL program
enforces, organised by functional area.
"""

import unittest

from cotrn01c import (
    InMemoryTransactionRepository,
    TransactionRecord,
    clear_all_fields,
    format_amount,
    get_header_info,
    validate_tran_id,
    view_transaction,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_repo_with_transaction() -> InMemoryTransactionRepository:
    """Return a repo pre-loaded with one transaction."""
    repo = InMemoryTransactionRepository()
    repo.add_transaction(
        TransactionRecord(
            tran_id="0000000000000042",
            tran_type_cd="01",
            tran_cat_cd="5000",
            tran_source="ONLINE",
            tran_desc="Test purchase at ACME Store",
            tran_amt=100.50,
            tran_merchant_id="123456789",
            tran_merchant_name="ACME Store",
            tran_merchant_city="Seattle",
            tran_merchant_zip="98101",
            tran_card_num="4000123456789010",
            tran_orig_ts="2024-06-15 12:00:00.000000",
            tran_proc_ts="2024-06-16 08:30:00.000000",
        )
    )
    return repo


# ===========================================================================
# 1. Transaction ID validation
# ===========================================================================

class TestValidateTranId(unittest.TestCase):
    """Tests for the transaction ID input validation."""

    def test_empty_is_invalid(self):
        is_valid, err = validate_tran_id("")
        self.assertFalse(is_valid)
        self.assertIn("can NOT be empty", err)

    def test_spaces_is_invalid(self):
        is_valid, err = validate_tran_id("   ")
        self.assertFalse(is_valid)
        self.assertIn("can NOT be empty", err)

    def test_valid_id(self):
        is_valid, err = validate_tran_id("0000000000000042")
        self.assertTrue(is_valid)
        self.assertEqual(err, "")

    def test_any_non_blank_is_valid(self):
        is_valid, err = validate_tran_id("ABC")
        self.assertTrue(is_valid)
        self.assertEqual(err, "")


# ===========================================================================
# 2. Amount formatting
# ===========================================================================

class TestFormatAmount(unittest.TestCase):
    """Tests for amount display formatting."""

    def test_positive_amount(self):
        self.assertEqual(format_amount(100.50), "+00000100.50")

    def test_negative_amount(self):
        self.assertEqual(format_amount(-25.75), "-00000025.75")

    def test_zero_amount(self):
        self.assertEqual(format_amount(0.0), "+00000000.00")

    def test_large_amount(self):
        self.assertEqual(format_amount(99999999.99), "+99999999.99")

    def test_small_amount(self):
        self.assertEqual(format_amount(0.01), "+00000000.01")


# ===========================================================================
# 3. View transaction — happy path
# ===========================================================================

class TestViewTransaction(unittest.TestCase):
    """Tests for the view_transaction function."""

    def test_successful_view(self):
        repo = _make_repo_with_transaction()
        result = view_transaction("0000000000000042", repo)

        self.assertTrue(result.success)
        self.assertEqual(result.message, "")
        self.assertIsNotNone(result.record)
        self.assertEqual(result.record.tran_id, "0000000000000042")
        self.assertEqual(result.record.tran_type_cd, "01")
        self.assertEqual(result.record.tran_cat_cd, "5000")
        self.assertEqual(result.record.tran_source, "ONLINE")
        self.assertEqual(result.record.tran_desc, "Test purchase at ACME Store")
        self.assertAlmostEqual(result.record.tran_amt, 100.50)
        self.assertEqual(result.record.tran_merchant_id, "123456789")
        self.assertEqual(result.record.tran_merchant_name, "ACME Store")
        self.assertEqual(result.record.tran_merchant_city, "Seattle")
        self.assertEqual(result.record.tran_merchant_zip, "98101")
        self.assertEqual(result.record.tran_card_num, "4000123456789010")
        self.assertEqual(result.record.tran_orig_ts, "2024-06-15 12:00:00.000000")
        self.assertEqual(result.record.tran_proc_ts, "2024-06-16 08:30:00.000000")
        self.assertEqual(result.formatted_amt, "+00000100.50")

    def test_not_found(self):
        repo = _make_repo_with_transaction()
        result = view_transaction("9999999999999999", repo)

        self.assertFalse(result.success)
        self.assertIn("Transaction ID NOT found", result.message)
        self.assertIsNone(result.record)

    def test_empty_id(self):
        repo = _make_repo_with_transaction()
        result = view_transaction("", repo)

        self.assertFalse(result.success)
        self.assertIn("can NOT be empty", result.message)

    def test_spaces_id(self):
        repo = _make_repo_with_transaction()
        result = view_transaction("   ", repo)

        self.assertFalse(result.success)
        self.assertIn("can NOT be empty", result.message)

    def test_view_with_negative_amount(self):
        repo = InMemoryTransactionRepository()
        repo.add_transaction(
            TransactionRecord(
                tran_id="0000000000000001",
                tran_amt=-50.25,
            )
        )
        result = view_transaction("0000000000000001", repo)
        self.assertTrue(result.success)
        self.assertEqual(result.formatted_amt, "-00000050.25")


# ===========================================================================
# 4. Clear fields
# ===========================================================================

class TestClearFields(unittest.TestCase):
    """Tests for the clear fields helper."""

    def test_clear_returns_all_blank(self):
        fields = clear_all_fields()
        self.assertIsInstance(fields, dict)
        for key, value in fields.items():
            self.assertEqual(value, "", f"Field '{key}' should be blank")

    def test_clear_contains_expected_keys(self):
        fields = clear_all_fields()
        expected_keys = [
            "tran_id_input", "tran_id", "card_num", "type_cd",
            "cat_cd", "source", "amount", "description",
            "orig_date", "proc_date", "merchant_id",
            "merchant_name", "merchant_city", "merchant_zip",
        ]
        for key in expected_keys:
            self.assertIn(key, fields)


# ===========================================================================
# 5. Header info
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
        self.assertEqual(info["program_name"], "COTRN01C")
        self.assertEqual(info["transaction_id"], "CT01")


# ===========================================================================
# 6. Edge cases
# ===========================================================================

class TestEdgeCases(unittest.TestCase):
    """Edge case tests."""

    def test_view_transaction_zero_amount(self):
        repo = InMemoryTransactionRepository()
        repo.add_transaction(
            TransactionRecord(tran_id="0000000000000001", tran_amt=0.0)
        )
        result = view_transaction("0000000000000001", repo)
        self.assertTrue(result.success)
        self.assertEqual(result.formatted_amt, "+00000000.00")

    def test_view_transaction_all_empty_fields(self):
        """A record with all default/empty fields is still viewable."""
        repo = InMemoryTransactionRepository()
        repo.add_transaction(TransactionRecord(tran_id="0000000000000001"))
        result = view_transaction("0000000000000001", repo)
        self.assertTrue(result.success)
        self.assertEqual(result.record.tran_desc, "")
        self.assertEqual(result.record.tran_card_num, "")

    def test_multiple_transactions_in_repo(self):
        """Correct transaction is returned when multiple exist."""
        repo = InMemoryTransactionRepository()
        repo.add_transaction(
            TransactionRecord(tran_id="0000000000000001", tran_desc="First")
        )
        repo.add_transaction(
            TransactionRecord(tran_id="0000000000000002", tran_desc="Second")
        )
        result = view_transaction("0000000000000002", repo)
        self.assertTrue(result.success)
        self.assertEqual(result.record.tran_desc, "Second")


if __name__ == "__main__":
    unittest.main()
