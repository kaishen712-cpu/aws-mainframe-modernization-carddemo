"""
Unit tests for cbtrn01c.py — the Python translation of CBTRN01C.CBL.

These tests verify the batch processing logic that reads daily transactions,
looks up card cross-references, and reads account records.
"""

import unittest

from cbtrn01c import (
    AccountRecord,
    BatchResult,
    CardXrefRecord,
    DailyTransactionRecord,
    InMemoryAccountRepository,
    InMemoryCardXrefRepository,
    process_single_transaction,
    run,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_xref_repo() -> InMemoryCardXrefRepository:
    """Return a repo pre-loaded with cross-reference records."""
    repo = InMemoryCardXrefRepository()
    repo.add(CardXrefRecord(
        card_num="4000123456789010",
        cust_id="000000001",
        acct_id="00000000001",
    ))
    repo.add(CardXrefRecord(
        card_num="4000123456789020",
        cust_id="000000002",
        acct_id="00000000002",
    ))
    return repo


def _make_acct_repo() -> InMemoryAccountRepository:
    """Return a repo pre-loaded with account records."""
    repo = InMemoryAccountRepository()
    repo.add(AccountRecord(
        acct_id="00000000001",
        active_status="Y",
        curr_bal=1000.00,
        credit_limit=5000.00,
    ))
    repo.add(AccountRecord(
        acct_id="00000000002",
        active_status="Y",
        curr_bal=2500.00,
        credit_limit=10000.00,
    ))
    return repo


def _make_daily_tran(
    tran_id: str = "0000000000000001",
    card_num: str = "4000123456789010",
    amt: float = 100.50,
) -> DailyTransactionRecord:
    """Return a sample daily transaction record."""
    return DailyTransactionRecord(
        tran_id=tran_id,
        tran_type_cd="01",
        tran_cat_cd="5000",
        tran_source="ONLINE",
        tran_desc="Test purchase",
        tran_amt=amt,
        tran_merchant_id="123456789",
        tran_merchant_name="ACME Store",
        tran_merchant_city="Seattle",
        tran_merchant_zip="98101",
        tran_card_num=card_num,
        tran_orig_ts="2024-06-15-10.30.00.000000",
        tran_proc_ts="2024-06-15-10.30.00.000000",
    )


# ===========================================================================
# 1. Single transaction processing
# ===========================================================================

class TestProcessSingleTransaction(unittest.TestCase):
    """Tests for the process_single_transaction function."""

    def test_happy_path_xref_and_account_found(self):
        """Card in xref, account exists -> both found."""
        xref_repo = _make_xref_repo()
        acct_repo = _make_acct_repo()
        tran = _make_daily_tran()

        result = process_single_transaction(tran, xref_repo, acct_repo)

        self.assertTrue(result.xref_found)
        self.assertTrue(result.acct_found)
        self.assertEqual(result.acct_id, "00000000001")
        self.assertEqual(result.error_message, "")

    def test_card_not_in_xref(self):
        """Unknown card number -> xref not found, skip transaction."""
        xref_repo = _make_xref_repo()
        acct_repo = _make_acct_repo()
        tran = _make_daily_tran(card_num="9999999999999999")

        result = process_single_transaction(tran, xref_repo, acct_repo)

        self.assertFalse(result.xref_found)
        self.assertFalse(result.acct_found)
        self.assertIn("COULD NOT BE VERIFIED", result.error_message)
        self.assertIn("9999999999999999", result.error_message)

    def test_xref_found_but_account_missing(self):
        """Card in xref but account doesn't exist -> account not found."""
        xref_repo = InMemoryCardXrefRepository()
        xref_repo.add(CardXrefRecord(
            card_num="4000123456789010",
            cust_id="000000001",
            acct_id="99999999999",  # account that doesn't exist
        ))
        acct_repo = _make_acct_repo()
        tran = _make_daily_tran()

        result = process_single_transaction(tran, xref_repo, acct_repo)

        self.assertTrue(result.xref_found)
        self.assertFalse(result.acct_found)
        self.assertIn("NOT FOUND", result.error_message)
        self.assertIn("99999999999", result.error_message)

    def test_tran_id_and_card_num_preserved(self):
        """Result captures the transaction ID and card number."""
        xref_repo = _make_xref_repo()
        acct_repo = _make_acct_repo()
        tran = _make_daily_tran(
            tran_id="0000000000000042",
            card_num="4000123456789020",
        )

        result = process_single_transaction(tran, xref_repo, acct_repo)

        self.assertEqual(result.tran_id, "0000000000000042")
        self.assertEqual(result.card_num, "4000123456789020")
        self.assertTrue(result.xref_found)
        self.assertTrue(result.acct_found)


# ===========================================================================
# 2. Full batch run
# ===========================================================================

class TestRun(unittest.TestCase):
    """End-to-end tests for the run() function."""

    def test_empty_input(self):
        """No daily transactions -> zero counts."""
        xref_repo = _make_xref_repo()
        acct_repo = _make_acct_repo()

        result = run([], xref_repo, acct_repo)

        self.assertEqual(result.transactions_read, 0)
        self.assertEqual(result.xref_found, 0)
        self.assertEqual(result.xref_not_found, 0)
        self.assertEqual(result.accounts_found, 0)
        self.assertEqual(result.accounts_not_found, 0)
        self.assertEqual(len(result.results), 0)

    def test_all_transactions_successful(self):
        """All transactions have valid cards and accounts."""
        xref_repo = _make_xref_repo()
        acct_repo = _make_acct_repo()
        transactions = [
            _make_daily_tran(tran_id="0000000000000001", card_num="4000123456789010"),
            _make_daily_tran(tran_id="0000000000000002", card_num="4000123456789020"),
        ]

        result = run(transactions, xref_repo, acct_repo)

        self.assertEqual(result.transactions_read, 2)
        self.assertEqual(result.xref_found, 2)
        self.assertEqual(result.xref_not_found, 0)
        self.assertEqual(result.accounts_found, 2)
        self.assertEqual(result.accounts_not_found, 0)
        self.assertEqual(len(result.results), 2)

    def test_mixed_results(self):
        """Mix of valid cards, invalid cards, and missing accounts."""
        xref_repo = _make_xref_repo()
        # Add an xref that points to a non-existent account
        xref_repo.add(CardXrefRecord(
            card_num="4000123456789030",
            cust_id="000000003",
            acct_id="99999999999",
        ))
        acct_repo = _make_acct_repo()

        transactions = [
            _make_daily_tran(tran_id="0000000000000001", card_num="4000123456789010"),  # OK
            _make_daily_tran(tran_id="0000000000000002", card_num="9999999999999999"),  # bad card
            _make_daily_tran(tran_id="0000000000000003", card_num="4000123456789030"),  # bad acct
        ]

        result = run(transactions, xref_repo, acct_repo)

        self.assertEqual(result.transactions_read, 3)
        self.assertEqual(result.xref_found, 2)
        self.assertEqual(result.xref_not_found, 1)
        self.assertEqual(result.accounts_found, 1)
        self.assertEqual(result.accounts_not_found, 1)

        # Verify individual results
        self.assertTrue(result.results[0].xref_found)
        self.assertTrue(result.results[0].acct_found)
        self.assertFalse(result.results[1].xref_found)
        self.assertTrue(result.results[2].xref_found)
        self.assertFalse(result.results[2].acct_found)

    def test_all_cards_invalid(self):
        """No cards match the cross-reference."""
        xref_repo = _make_xref_repo()
        acct_repo = _make_acct_repo()
        transactions = [
            _make_daily_tran(tran_id="0000000000000001", card_num="0000000000000001"),
            _make_daily_tran(tran_id="0000000000000002", card_num="0000000000000002"),
        ]

        result = run(transactions, xref_repo, acct_repo)

        self.assertEqual(result.transactions_read, 2)
        self.assertEqual(result.xref_found, 0)
        self.assertEqual(result.xref_not_found, 2)
        self.assertEqual(result.accounts_found, 0)


# ===========================================================================
# 3. Data structure tests
# ===========================================================================

class TestDataStructures(unittest.TestCase):
    """Tests for data structures and repository implementations."""

    def test_daily_transaction_defaults(self):
        """DailyTransactionRecord has sensible defaults."""
        tran = DailyTransactionRecord()
        self.assertEqual(tran.tran_id, "")
        self.assertEqual(tran.tran_amt, 0.0)
        self.assertEqual(tran.tran_card_num, "")

    def test_card_xref_defaults(self):
        """CardXrefRecord has sensible defaults."""
        xref = CardXrefRecord()
        self.assertEqual(xref.card_num, "")
        self.assertEqual(xref.cust_id, "")
        self.assertEqual(xref.acct_id, "")

    def test_account_defaults(self):
        """AccountRecord has sensible defaults."""
        acct = AccountRecord()
        self.assertEqual(acct.acct_id, "")
        self.assertEqual(acct.curr_bal, 0.0)
        self.assertEqual(acct.credit_limit, 0.0)

    def test_batch_result_defaults(self):
        """BatchResult initializes with zero counts and empty list."""
        result = BatchResult()
        self.assertEqual(result.transactions_read, 0)
        self.assertEqual(len(result.results), 0)

    def test_inmemory_xref_repo_add_and_lookup(self):
        """InMemoryCardXrefRepository stores and retrieves records."""
        repo = InMemoryCardXrefRepository()
        record = CardXrefRecord(card_num="1234567890123456", cust_id="1", acct_id="1")
        repo.add(record)

        found = repo.lookup_by_card_num("1234567890123456")
        self.assertIsNotNone(found)
        self.assertEqual(found.card_num, "1234567890123456")

        not_found = repo.lookup_by_card_num("0000000000000000")
        self.assertIsNone(not_found)

    def test_inmemory_acct_repo_add_and_lookup(self):
        """InMemoryAccountRepository stores and retrieves records."""
        repo = InMemoryAccountRepository()
        record = AccountRecord(acct_id="00000000001", curr_bal=500.00)
        repo.add(record)

        found = repo.read_account("00000000001")
        self.assertIsNotNone(found)
        self.assertAlmostEqual(found.curr_bal, 500.00)

        not_found = repo.read_account("99999999999")
        self.assertIsNone(not_found)


# ===========================================================================
# 4. Edge cases
# ===========================================================================

class TestEdgeCases(unittest.TestCase):
    """Edge case tests."""

    def test_single_transaction(self):
        """Batch with exactly one transaction."""
        xref_repo = _make_xref_repo()
        acct_repo = _make_acct_repo()
        transactions = [_make_daily_tran()]

        result = run(transactions, xref_repo, acct_repo)

        self.assertEqual(result.transactions_read, 1)
        self.assertEqual(result.xref_found, 1)
        self.assertEqual(result.accounts_found, 1)

    def test_duplicate_transactions(self):
        """Multiple transactions for the same card are each processed."""
        xref_repo = _make_xref_repo()
        acct_repo = _make_acct_repo()
        transactions = [
            _make_daily_tran(tran_id="0000000000000001"),
            _make_daily_tran(tran_id="0000000000000002"),
            _make_daily_tran(tran_id="0000000000000003"),
        ]

        result = run(transactions, xref_repo, acct_repo)

        self.assertEqual(result.transactions_read, 3)
        self.assertEqual(result.xref_found, 3)
        self.assertEqual(result.accounts_found, 3)

    def test_empty_card_number(self):
        """Transaction with empty card number -> xref not found."""
        xref_repo = _make_xref_repo()
        acct_repo = _make_acct_repo()
        tran = _make_daily_tran(card_num="")

        result = process_single_transaction(tran, xref_repo, acct_repo)

        self.assertFalse(result.xref_found)

    def test_negative_amount_transaction(self):
        """Transaction with negative amount (credit/refund)."""
        xref_repo = _make_xref_repo()
        acct_repo = _make_acct_repo()
        tran = _make_daily_tran(amt=-50.00)

        result = process_single_transaction(tran, xref_repo, acct_repo)

        self.assertTrue(result.xref_found)
        self.assertTrue(result.acct_found)

    def test_zero_amount_transaction(self):
        """Transaction with zero amount."""
        xref_repo = _make_xref_repo()
        acct_repo = _make_acct_repo()
        tran = _make_daily_tran(amt=0.0)

        result = process_single_transaction(tran, xref_repo, acct_repo)

        self.assertTrue(result.xref_found)
        self.assertTrue(result.acct_found)


if __name__ == "__main__":
    unittest.main()
