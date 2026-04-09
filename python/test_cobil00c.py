"""
Unit tests for cobil00c.py — the Python translation of COBIL00C.CBL.

These tests verify the same business rules that the original COBOL program
enforces, organised by functional area.
"""

import unittest

from cobil00c import (
    AccountRecord,
    CardXrefRecord,
    InMemoryAccountRepository,
    InMemoryCardXrefRepository,
    InMemoryTransactionRepository,
    TransactionRecord,
    clear_all_fields,
    format_balance,
    generate_transaction_id,
    get_header_info,
    process_bill_payment,
    validate_account_id,
    validate_confirmation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_repos(
    balance: float = 500.00,
) -> tuple[
    InMemoryAccountRepository,
    InMemoryCardXrefRepository,
    InMemoryTransactionRepository,
]:
    """Return repos pre-loaded with one account, xref, and no transactions."""
    acct_repo = InMemoryAccountRepository()
    acct_repo.add_account(
        AccountRecord(
            acct_id="00000000001",
            acct_active_status="Y",
            acct_curr_bal=balance,
            acct_credit_limit=5000.00,
        )
    )

    xref_repo = InMemoryCardXrefRepository()
    xref_repo.add_xref(
        CardXrefRecord(
            card_num="4000123456789010",
            cust_id="000000001",
            acct_id="00000000001",
        )
    )

    tran_repo = InMemoryTransactionRepository()

    return acct_repo, xref_repo, tran_repo


# ===========================================================================
# 1. Account ID validation
# ===========================================================================

class TestValidateAccountId(unittest.TestCase):
    """Tests for account ID input validation."""

    def test_empty_is_invalid(self):
        is_valid, err = validate_account_id("")
        self.assertFalse(is_valid)
        self.assertIn("can NOT be empty", err)

    def test_spaces_is_invalid(self):
        is_valid, err = validate_account_id("   ")
        self.assertFalse(is_valid)
        self.assertIn("can NOT be empty", err)

    def test_valid_id(self):
        is_valid, err = validate_account_id("00000000001")
        self.assertTrue(is_valid)
        self.assertEqual(err, "")


# ===========================================================================
# 2. Confirmation validation
# ===========================================================================

class TestValidateConfirmation(unittest.TestCase):
    """Tests for confirmation flag validation."""

    def test_Y_is_confirmed(self):
        status, err = validate_confirmation("Y")
        self.assertEqual(status, "confirmed")
        self.assertEqual(err, "")

    def test_y_is_confirmed(self):
        status, err = validate_confirmation("y")
        self.assertEqual(status, "confirmed")

    def test_N_is_cancelled(self):
        status, err = validate_confirmation("N")
        self.assertEqual(status, "cancelled")

    def test_n_is_cancelled(self):
        status, err = validate_confirmation("n")
        self.assertEqual(status, "cancelled")

    def test_blank_is_pending(self):
        status, err = validate_confirmation("")
        self.assertEqual(status, "pending")

    def test_spaces_is_pending(self):
        status, err = validate_confirmation("   ")
        self.assertEqual(status, "pending")

    def test_invalid_value(self):
        status, err = validate_confirmation("X")
        self.assertEqual(status, "invalid")
        self.assertIn("Invalid value", err)

    def test_digit_is_invalid(self):
        status, err = validate_confirmation("1")
        self.assertEqual(status, "invalid")


# ===========================================================================
# 3. Balance formatting
# ===========================================================================

class TestFormatBalance(unittest.TestCase):
    """Tests for balance display formatting."""

    def test_positive_balance(self):
        self.assertEqual(format_balance(500.00), "+0000000500.00")

    def test_zero_balance(self):
        self.assertEqual(format_balance(0.0), "+0000000000.00")

    def test_negative_balance(self):
        self.assertEqual(format_balance(-100.50), "-0000000100.50")

    def test_large_balance(self):
        self.assertEqual(format_balance(9999999999.99), "+9999999999.99")


# ===========================================================================
# 4. Transaction ID generation
# ===========================================================================

class TestGenerateTransactionId(unittest.TestCase):
    """Tests for payment transaction ID generation."""

    def test_empty_repo_starts_at_one(self):
        tran_repo = InMemoryTransactionRepository()
        tid = generate_transaction_id(tran_repo)
        self.assertEqual(tid, "0000000000000001")

    def test_increments_from_last(self):
        tran_repo = InMemoryTransactionRepository()
        tran_repo.add_transaction(TransactionRecord(tran_id="0000000000000042"))
        tid = generate_transaction_id(tran_repo)
        self.assertEqual(tid, "0000000000000043")


# ===========================================================================
# 5. Bill payment — happy path
# ===========================================================================

class TestBillPaymentHappyPath(unittest.TestCase):
    """Tests for successful bill payment."""

    def test_successful_payment(self):
        acct_repo, xref_repo, tran_repo = _make_repos(500.00)

        result = process_bill_payment(
            "00000000001", "Y", acct_repo, xref_repo, tran_repo
        )

        self.assertTrue(result.success)
        self.assertIn("Payment successful", result.message)
        self.assertIn("1", result.message)  # Tran ID
        self.assertEqual(result.tran_id, "0000000000000001")
        self.assertAlmostEqual(result.new_balance, 0.0)

        # Verify transaction was written
        self.assertEqual(len(tran_repo.transactions), 1)
        tran = list(tran_repo.transactions.values())[0]
        self.assertEqual(tran.tran_type_cd, "02")
        self.assertEqual(tran.tran_cat_cd, "0002")
        self.assertEqual(tran.tran_source, "POS TERM")
        self.assertEqual(tran.tran_desc, "BILL PAYMENT - ONLINE")
        self.assertAlmostEqual(tran.tran_amt, 500.00)
        self.assertEqual(tran.tran_card_num, "4000123456789010")
        self.assertEqual(tran.tran_merchant_id, "999999999")
        self.assertEqual(tran.tran_merchant_name, "BILL PAYMENT")

        # Verify account was updated
        account = acct_repo.read_account("00000000001")
        self.assertAlmostEqual(account.acct_curr_bal, 0.0)

    def test_payment_with_lowercase_y(self):
        acct_repo, xref_repo, tran_repo = _make_repos(100.00)
        result = process_bill_payment(
            "00000000001", "y", acct_repo, xref_repo, tran_repo
        )
        self.assertTrue(result.success)

    def test_sequential_payments_increment_id(self):
        acct_repo, xref_repo, tran_repo = _make_repos(500.00)

        result1 = process_bill_payment(
            "00000000001", "Y", acct_repo, xref_repo, tran_repo
        )
        self.assertTrue(result1.success)
        self.assertEqual(result1.tran_id, "0000000000000001")

        # Reset balance for second payment
        account = acct_repo.read_account("00000000001")
        account.acct_curr_bal = 200.00
        acct_repo.update_account(account)

        result2 = process_bill_payment(
            "00000000001", "Y", acct_repo, xref_repo, tran_repo
        )
        self.assertTrue(result2.success)
        self.assertEqual(result2.tran_id, "0000000000000002")


# ===========================================================================
# 6. Bill payment — validation errors
# ===========================================================================

class TestBillPaymentValidation(unittest.TestCase):
    """Tests for bill payment validation errors."""

    def test_empty_account_id(self):
        acct_repo, xref_repo, tran_repo = _make_repos()
        result = process_bill_payment(
            "", "Y", acct_repo, xref_repo, tran_repo
        )
        self.assertFalse(result.success)
        self.assertIn("can NOT be empty", result.message)

    def test_account_not_found(self):
        acct_repo, xref_repo, tran_repo = _make_repos()
        result = process_bill_payment(
            "99999999999", "Y", acct_repo, xref_repo, tran_repo
        )
        self.assertFalse(result.success)
        self.assertIn("Account ID NOT found", result.message)

    def test_zero_balance(self):
        acct_repo, xref_repo, tran_repo = _make_repos(0.0)
        result = process_bill_payment(
            "00000000001", "Y", acct_repo, xref_repo, tran_repo
        )
        self.assertFalse(result.success)
        self.assertIn("nothing to pay", result.message)

    def test_negative_balance(self):
        acct_repo, xref_repo, tran_repo = _make_repos(-50.00)
        result = process_bill_payment(
            "00000000001", "Y", acct_repo, xref_repo, tran_repo
        )
        self.assertFalse(result.success)
        self.assertIn("nothing to pay", result.message)

    def test_invalid_confirmation(self):
        acct_repo, xref_repo, tran_repo = _make_repos()
        result = process_bill_payment(
            "00000000001", "X", acct_repo, xref_repo, tran_repo
        )
        self.assertFalse(result.success)
        self.assertIn("Invalid value", result.message)

    def test_cancel_confirmation(self):
        acct_repo, xref_repo, tran_repo = _make_repos()
        result = process_bill_payment(
            "00000000001", "N", acct_repo, xref_repo, tran_repo
        )
        self.assertFalse(result.success)
        self.assertEqual(len(tran_repo.transactions), 0)

    def test_pending_confirmation_shows_balance(self):
        acct_repo, xref_repo, tran_repo = _make_repos(500.00)
        result = process_bill_payment(
            "00000000001", "", acct_repo, xref_repo, tran_repo
        )
        self.assertFalse(result.success)
        self.assertIn("Confirm to make a bill payment", result.message)
        self.assertIn("500", result.display_balance)

    def test_xref_not_found(self):
        """Account exists but no card cross-reference."""
        acct_repo = InMemoryAccountRepository()
        acct_repo.add_account(
            AccountRecord(acct_id="00000000001", acct_curr_bal=500.00)
        )
        xref_repo = InMemoryCardXrefRepository()
        tran_repo = InMemoryTransactionRepository()

        result = process_bill_payment(
            "00000000001", "Y", acct_repo, xref_repo, tran_repo
        )
        self.assertFalse(result.success)
        self.assertIn("Account ID NOT found", result.message)


# ===========================================================================
# 7. Clear fields and header
# ===========================================================================

class TestClearAndHeader(unittest.TestCase):
    """Tests for clear fields and header helpers."""

    def test_clear_returns_blank(self):
        fields = clear_all_fields()
        self.assertEqual(fields["acct_id"], "")
        self.assertEqual(fields["cur_bal"], "")
        self.assertEqual(fields["confirm"], "")

    def test_header_contains_required_fields(self):
        info = get_header_info()
        self.assertEqual(info["program_name"], "COBIL00C")
        self.assertEqual(info["transaction_id"], "CB00")
        self.assertIn("title01", info)
        self.assertIn("current_date", info)
        self.assertIn("current_time", info)


# ===========================================================================
# 8. Edge cases
# ===========================================================================

class TestEdgeCases(unittest.TestCase):
    """Edge case tests."""

    def test_very_small_balance(self):
        acct_repo, xref_repo, tran_repo = _make_repos(0.01)
        result = process_bill_payment(
            "00000000001", "Y", acct_repo, xref_repo, tran_repo
        )
        self.assertTrue(result.success)
        self.assertAlmostEqual(result.new_balance, 0.0)

    def test_large_balance(self):
        acct_repo, xref_repo, tran_repo = _make_repos(9999999.99)
        result = process_bill_payment(
            "00000000001", "Y", acct_repo, xref_repo, tran_repo
        )
        self.assertTrue(result.success)

    def test_payment_transaction_has_timestamps(self):
        acct_repo, xref_repo, tran_repo = _make_repos(100.00)
        result = process_bill_payment(
            "00000000001", "Y", acct_repo, xref_repo, tran_repo
        )
        self.assertTrue(result.success)
        tran = list(tran_repo.transactions.values())[0]
        self.assertNotEqual(tran.tran_orig_ts, "")
        self.assertNotEqual(tran.tran_proc_ts, "")
        self.assertEqual(tran.tran_orig_ts, tran.tran_proc_ts)

    def test_duplicate_tran_id_error(self):
        """Force a duplicate by subclassing write_transaction to always fail."""
        acct_repo, xref_repo, tran_repo = _make_repos(100.00)
        # Override write_transaction to simulate a DUPKEY error
        tran_repo.write_transaction = lambda record: False
        result = process_bill_payment(
            "00000000001", "Y", acct_repo, xref_repo, tran_repo
        )
        self.assertFalse(result.success)
        self.assertIn("Tran ID already exist", result.message)


if __name__ == "__main__":
    unittest.main()
