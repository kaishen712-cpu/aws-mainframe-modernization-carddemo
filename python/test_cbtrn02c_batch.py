"""
Unit tests for cbtrn02c_batch.py — the Python translation of CBTRN02C.CBL (batch).

These tests verify the advanced batch transaction posting logic including
validation, rejection handling, balance updates, and category balance tracking.
"""

import unittest

from cbtrn02c_batch import (
    AccountRecord,
    CardXrefRecord,
    DailyTransactionRecord,
    InMemoryAccountRepository,
    InMemoryCardXrefRepository,
    InMemoryTranCatBalRepository,
    InMemoryTransactionRepository,
    REASON_ACCOUNT_NOT_FOUND,
    REASON_EXPIRED,
    REASON_INVALID_CARD,
    REASON_OVERLIMIT,
    TranCatBalRecord,
    TransactionRecord,
    post_transaction,
    run,
    validate_transaction,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXED_TIMESTAMP = "2024-06-15-10.30.00.000000"


def _fixed_ts() -> str:
    return FIXED_TIMESTAMP


def _make_xref_repo() -> InMemoryCardXrefRepository:
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
    repo = InMemoryAccountRepository()
    repo.add(AccountRecord(
        acct_id="00000000001",
        active_status="Y",
        curr_bal=1000.00,
        credit_limit=5000.00,
        expiration_date="2025-12-31",
        curr_cyc_credit=500.00,
        curr_cyc_debit=200.00,
        group_id="GROUP1",
    ))
    repo.add(AccountRecord(
        acct_id="00000000002",
        active_status="Y",
        curr_bal=2500.00,
        credit_limit=10000.00,
        expiration_date="2026-06-30",
        curr_cyc_credit=1000.00,
        curr_cyc_debit=500.00,
        group_id="GROUP2",
    ))
    return repo


def _make_daily_tran(
    tran_id: str = "0000000000000001",
    card_num: str = "4000123456789010",
    amt: float = 100.50,
    type_cd: str = "01",
    cat_cd: str = "5000",
    orig_ts: str = "2024-06-15-10.30.00.000000",
) -> DailyTransactionRecord:
    return DailyTransactionRecord(
        tran_id=tran_id,
        tran_type_cd=type_cd,
        tran_cat_cd=cat_cd,
        tran_source="ONLINE",
        tran_desc="Test purchase",
        tran_amt=amt,
        tran_merchant_id="123456789",
        tran_merchant_name="ACME Store",
        tran_merchant_city="Seattle",
        tran_merchant_zip="98101",
        tran_card_num=card_num,
        tran_orig_ts=orig_ts,
        tran_proc_ts=orig_ts,
    )


def _make_all_repos():
    """Return all four repos needed for a batch run."""
    return (
        _make_xref_repo(),
        _make_acct_repo(),
        InMemoryTransactionRepository(),
        InMemoryTranCatBalRepository(),
    )


# ===========================================================================
# 1. Validation tests
# ===========================================================================

class TestValidateTransaction(unittest.TestCase):
    """Tests for the validate_transaction function."""

    def test_valid_transaction(self):
        """Happy path: card found, account found, within limits."""
        xref_repo = _make_xref_repo()
        acct_repo = _make_acct_repo()
        tran = _make_daily_tran()

        fail_reason, fail_desc, xref, account = validate_transaction(
            tran, xref_repo, acct_repo
        )

        self.assertEqual(fail_reason, 0)
        self.assertEqual(fail_desc, "")
        self.assertIsNotNone(xref)
        self.assertIsNotNone(account)

    def test_invalid_card_number(self):
        """Card not in xref -> reason 100."""
        xref_repo = _make_xref_repo()
        acct_repo = _make_acct_repo()
        tran = _make_daily_tran(card_num="9999999999999999")

        fail_reason, fail_desc, xref, account = validate_transaction(
            tran, xref_repo, acct_repo
        )

        self.assertEqual(fail_reason, REASON_INVALID_CARD)
        self.assertIn("INVALID CARD", fail_desc)
        self.assertIsNone(xref)

    def test_account_not_found(self):
        """Card in xref but account missing -> reason 101."""
        xref_repo = InMemoryCardXrefRepository()
        xref_repo.add(CardXrefRecord(
            card_num="4000123456789010",
            cust_id="000000001",
            acct_id="99999999999",
        ))
        acct_repo = _make_acct_repo()
        tran = _make_daily_tran()

        fail_reason, fail_desc, xref, account = validate_transaction(
            tran, xref_repo, acct_repo
        )

        self.assertEqual(fail_reason, REASON_ACCOUNT_NOT_FOUND)
        self.assertIn("ACCOUNT RECORD NOT FOUND", fail_desc)
        self.assertIsNotNone(xref)
        self.assertIsNone(account)

    def test_overlimit_transaction(self):
        """Transaction exceeds credit limit -> reason 102."""
        xref_repo = _make_xref_repo()
        acct_repo = InMemoryAccountRepository()
        acct_repo.add(AccountRecord(
            acct_id="00000000001",
            credit_limit=500.00,
            expiration_date="2025-12-31",
            curr_cyc_credit=400.00,
            curr_cyc_debit=0.00,
        ))
        # temp_bal = 400 - 0 + 200 = 600 > 500
        tran = _make_daily_tran(amt=200.00)

        fail_reason, fail_desc, xref, account = validate_transaction(
            tran, xref_repo, acct_repo
        )

        self.assertEqual(fail_reason, REASON_OVERLIMIT)
        self.assertIn("OVERLIMIT", fail_desc)

    def test_within_credit_limit(self):
        """Transaction exactly at credit limit -> passes."""
        xref_repo = _make_xref_repo()
        acct_repo = InMemoryAccountRepository()
        acct_repo.add(AccountRecord(
            acct_id="00000000001",
            credit_limit=500.00,
            expiration_date="2025-12-31",
            curr_cyc_credit=400.00,
            curr_cyc_debit=0.00,
        ))
        # temp_bal = 400 - 0 + 100 = 500 == 500 (OK, >= check passes)
        tran = _make_daily_tran(amt=100.00)

        fail_reason, _, _, _ = validate_transaction(
            tran, xref_repo, acct_repo
        )

        self.assertEqual(fail_reason, 0)

    def test_expired_account(self):
        """Transaction after expiration date -> reason 103."""
        xref_repo = _make_xref_repo()
        acct_repo = InMemoryAccountRepository()
        acct_repo.add(AccountRecord(
            acct_id="00000000001",
            credit_limit=50000.00,
            expiration_date="2024-01-01",
            curr_cyc_credit=0.00,
            curr_cyc_debit=0.00,
        ))
        tran = _make_daily_tran(orig_ts="2024-06-15-10.30.00.000000")

        fail_reason, fail_desc, _, _ = validate_transaction(
            tran, xref_repo, acct_repo
        )

        self.assertEqual(fail_reason, REASON_EXPIRED)
        self.assertIn("EXPIRATION", fail_desc)

    def test_not_expired_same_date(self):
        """Transaction on expiration date -> passes."""
        xref_repo = _make_xref_repo()
        acct_repo = InMemoryAccountRepository()
        acct_repo.add(AccountRecord(
            acct_id="00000000001",
            credit_limit=50000.00,
            expiration_date="2024-06-15",
            curr_cyc_credit=0.00,
            curr_cyc_debit=0.00,
        ))
        tran = _make_daily_tran(orig_ts="2024-06-15-10.30.00.000000")

        fail_reason, _, _, _ = validate_transaction(
            tran, xref_repo, acct_repo
        )

        self.assertEqual(fail_reason, 0)

    def test_negative_amount_reduces_temp_bal(self):
        """Negative (credit/refund) reduces temp balance, stays within limit."""
        xref_repo = _make_xref_repo()
        acct_repo = InMemoryAccountRepository()
        acct_repo.add(AccountRecord(
            acct_id="00000000001",
            credit_limit=500.00,
            expiration_date="2025-12-31",
            curr_cyc_credit=500.00,
            curr_cyc_debit=0.00,
        ))
        # temp_bal = 500 - 0 + (-100) = 400 <= 500
        tran = _make_daily_tran(amt=-100.00)

        fail_reason, _, _, _ = validate_transaction(
            tran, xref_repo, acct_repo
        )

        self.assertEqual(fail_reason, 0)


# ===========================================================================
# 2. Posting tests
# ===========================================================================

class TestPostTransaction(unittest.TestCase):
    """Tests for the post_transaction function."""

    def test_post_creates_transaction_record(self):
        """Posted transaction is written to the transaction repository."""
        xref = CardXrefRecord(
            card_num="4000123456789010",
            cust_id="000000001",
            acct_id="00000000001",
        )
        account = AccountRecord(
            acct_id="00000000001",
            curr_bal=1000.00,
            curr_cyc_credit=500.00,
            curr_cyc_debit=200.00,
        )
        tran_repo = InMemoryTransactionRepository()
        acct_repo = InMemoryAccountRepository()
        acct_repo.add(AccountRecord(
            acct_id="00000000001",
            curr_bal=1000.00,
            curr_cyc_credit=500.00,
            curr_cyc_debit=200.00,
        ))
        tcatbal_repo = InMemoryTranCatBalRepository()
        daily_tran = _make_daily_tran()

        posted = post_transaction(
            daily_tran, xref, account,
            tran_repo, acct_repo, tcatbal_repo,
            timestamp_fn=_fixed_ts,
        )

        self.assertEqual(posted.tran_id, "0000000000000001")
        self.assertEqual(posted.tran_type_cd, "01")
        self.assertEqual(posted.tran_proc_ts, FIXED_TIMESTAMP)
        self.assertEqual(len(tran_repo.transactions), 1)

    def test_post_updates_account_balance_credit(self):
        """Positive amount adds to current balance and cycle credit."""
        xref = CardXrefRecord(card_num="4000123456789010", acct_id="00000000001")
        account = AccountRecord(
            acct_id="00000000001",
            curr_bal=1000.00,
            curr_cyc_credit=500.00,
            curr_cyc_debit=200.00,
        )
        acct_repo = InMemoryAccountRepository()
        acct_repo.add(account)
        tran_repo = InMemoryTransactionRepository()
        tcatbal_repo = InMemoryTranCatBalRepository()
        daily_tran = _make_daily_tran(amt=150.00)

        post_transaction(
            daily_tran, xref, account,
            tran_repo, acct_repo, tcatbal_repo,
            timestamp_fn=_fixed_ts,
        )

        updated = acct_repo.read_account("00000000001")
        self.assertAlmostEqual(updated.curr_bal, 1150.00)
        self.assertAlmostEqual(updated.curr_cyc_credit, 650.00)
        self.assertAlmostEqual(updated.curr_cyc_debit, 200.00)

    def test_post_updates_account_balance_debit(self):
        """Negative amount adds to current balance and cycle debit."""
        xref = CardXrefRecord(card_num="4000123456789010", acct_id="00000000001")
        account = AccountRecord(
            acct_id="00000000001",
            curr_bal=1000.00,
            curr_cyc_credit=500.00,
            curr_cyc_debit=200.00,
        )
        acct_repo = InMemoryAccountRepository()
        acct_repo.add(account)
        tran_repo = InMemoryTransactionRepository()
        tcatbal_repo = InMemoryTranCatBalRepository()
        daily_tran = _make_daily_tran(amt=-75.00)

        post_transaction(
            daily_tran, xref, account,
            tran_repo, acct_repo, tcatbal_repo,
            timestamp_fn=_fixed_ts,
        )

        updated = acct_repo.read_account("00000000001")
        self.assertAlmostEqual(updated.curr_bal, 925.00)
        self.assertAlmostEqual(updated.curr_cyc_credit, 500.00)
        self.assertAlmostEqual(updated.curr_cyc_debit, 125.00)

    def test_post_creates_new_tcatbal(self):
        """Category balance record created when none exists."""
        xref = CardXrefRecord(card_num="4000123456789010", acct_id="00000000001")
        account = AccountRecord(acct_id="00000000001")
        acct_repo = InMemoryAccountRepository()
        acct_repo.add(account)
        tran_repo = InMemoryTransactionRepository()
        tcatbal_repo = InMemoryTranCatBalRepository()
        daily_tran = _make_daily_tran(amt=100.00, type_cd="01", cat_cd="5000")

        post_transaction(
            daily_tran, xref, account,
            tran_repo, acct_repo, tcatbal_repo,
            timestamp_fn=_fixed_ts,
        )

        bal = tcatbal_repo.read_balance("00000000001", "01", "5000")
        self.assertIsNotNone(bal)
        self.assertAlmostEqual(bal.balance, 100.00)

    def test_post_updates_existing_tcatbal(self):
        """Category balance updated when record already exists."""
        xref = CardXrefRecord(card_num="4000123456789010", acct_id="00000000001")
        account = AccountRecord(acct_id="00000000001")
        acct_repo = InMemoryAccountRepository()
        acct_repo.add(account)
        tran_repo = InMemoryTransactionRepository()
        tcatbal_repo = InMemoryTranCatBalRepository()
        tcatbal_repo.add(TranCatBalRecord(
            acct_id="00000000001", type_cd="01", cat_cd="5000", balance=200.00
        ))
        daily_tran = _make_daily_tran(amt=100.00, type_cd="01", cat_cd="5000")

        post_transaction(
            daily_tran, xref, account,
            tran_repo, acct_repo, tcatbal_repo,
            timestamp_fn=_fixed_ts,
        )

        bal = tcatbal_repo.read_balance("00000000001", "01", "5000")
        self.assertAlmostEqual(bal.balance, 300.00)


# ===========================================================================
# 3. Full batch run tests
# ===========================================================================

class TestRun(unittest.TestCase):
    """End-to-end tests for the run() function."""

    def test_empty_input(self):
        """No transactions -> zero counts."""
        xref_repo, acct_repo, tran_repo, tcatbal_repo = _make_all_repos()

        result = run([], xref_repo, acct_repo, tran_repo, tcatbal_repo,
                     timestamp_fn=_fixed_ts)

        self.assertEqual(result.transaction_count, 0)
        self.assertEqual(result.reject_count, 0)
        self.assertEqual(result.return_code, 0)

    def test_all_valid(self):
        """All transactions pass validation and are posted."""
        xref_repo, acct_repo, tran_repo, tcatbal_repo = _make_all_repos()
        transactions = [
            _make_daily_tran(tran_id="0000000000000001", card_num="4000123456789010"),
            _make_daily_tran(tran_id="0000000000000002", card_num="4000123456789020"),
        ]

        result = run(transactions, xref_repo, acct_repo, tran_repo, tcatbal_repo,
                     timestamp_fn=_fixed_ts)

        self.assertEqual(result.transaction_count, 2)
        self.assertEqual(result.reject_count, 0)
        self.assertEqual(len(result.posted_transactions), 2)
        self.assertEqual(len(result.rejected_transactions), 0)
        self.assertEqual(result.return_code, 0)

    def test_all_rejected(self):
        """All transactions fail validation."""
        xref_repo, acct_repo, tran_repo, tcatbal_repo = _make_all_repos()
        transactions = [
            _make_daily_tran(tran_id="0000000000000001", card_num="9999999999999999"),
            _make_daily_tran(tran_id="0000000000000002", card_num="8888888888888888"),
        ]

        result = run(transactions, xref_repo, acct_repo, tran_repo, tcatbal_repo,
                     timestamp_fn=_fixed_ts)

        self.assertEqual(result.transaction_count, 2)
        self.assertEqual(result.reject_count, 2)
        self.assertEqual(len(result.posted_transactions), 0)
        self.assertEqual(len(result.rejected_transactions), 2)
        self.assertEqual(result.return_code, 4)

    def test_mixed_valid_and_rejected(self):
        """Mix of valid and rejected transactions."""
        xref_repo, acct_repo, tran_repo, tcatbal_repo = _make_all_repos()
        transactions = [
            _make_daily_tran(tran_id="0000000000000001", card_num="4000123456789010"),
            _make_daily_tran(tran_id="0000000000000002", card_num="9999999999999999"),
            _make_daily_tran(tran_id="0000000000000003", card_num="4000123456789020"),
        ]

        result = run(transactions, xref_repo, acct_repo, tran_repo, tcatbal_repo,
                     timestamp_fn=_fixed_ts)

        self.assertEqual(result.transaction_count, 3)
        self.assertEqual(result.reject_count, 1)
        self.assertEqual(len(result.posted_transactions), 2)
        self.assertEqual(len(result.rejected_transactions), 1)
        self.assertEqual(result.return_code, 4)

    def test_rejected_transaction_captures_reason(self):
        """Rejected transaction includes the fail reason and description."""
        xref_repo, acct_repo, tran_repo, tcatbal_repo = _make_all_repos()
        transactions = [
            _make_daily_tran(tran_id="0000000000000001", card_num="9999999999999999"),
        ]

        result = run(transactions, xref_repo, acct_repo, tran_repo, tcatbal_repo,
                     timestamp_fn=_fixed_ts)

        self.assertEqual(len(result.rejected_transactions), 1)
        rejected = result.rejected_transactions[0]
        self.assertEqual(rejected.fail_reason, REASON_INVALID_CARD)
        self.assertIn("INVALID CARD", rejected.fail_reason_desc)

    def test_multiple_transactions_accumulate_balances(self):
        """Multiple transactions for same account accumulate balances."""
        xref_repo, acct_repo, tran_repo, tcatbal_repo = _make_all_repos()
        transactions = [
            _make_daily_tran(tran_id="0000000000000001", amt=100.00),
            _make_daily_tran(tran_id="0000000000000002", amt=200.00),
            _make_daily_tran(tran_id="0000000000000003", amt=50.00),
        ]

        result = run(transactions, xref_repo, acct_repo, tran_repo, tcatbal_repo,
                     timestamp_fn=_fixed_ts)

        self.assertEqual(result.transaction_count, 3)
        self.assertEqual(result.reject_count, 0)

        # Check accumulated account balance
        acct = acct_repo.read_account("00000000001")
        # Original curr_bal=1000 + 100 + 200 + 50 = 1350
        self.assertAlmostEqual(acct.curr_bal, 1350.00)
        # Original curr_cyc_credit=500 + 100 + 200 + 50 = 850
        self.assertAlmostEqual(acct.curr_cyc_credit, 850.00)

        # Check accumulated category balance
        bal = tcatbal_repo.read_balance("00000000001", "01", "5000")
        self.assertAlmostEqual(bal.balance, 350.00)


# ===========================================================================
# 4. Edge cases
# ===========================================================================

class TestEdgeCases(unittest.TestCase):
    """Edge case tests."""

    def test_zero_amount_transaction(self):
        """Zero amount transaction passes validation and posts."""
        xref_repo, acct_repo, tran_repo, tcatbal_repo = _make_all_repos()
        transactions = [_make_daily_tran(amt=0.0)]

        result = run(transactions, xref_repo, acct_repo, tran_repo, tcatbal_repo,
                     timestamp_fn=_fixed_ts)

        self.assertEqual(result.reject_count, 0)
        self.assertEqual(len(result.posted_transactions), 1)

    def test_overlimit_boundary(self):
        """Transaction that exactly hits the credit limit passes."""
        xref_repo = _make_xref_repo()
        acct_repo = InMemoryAccountRepository()
        acct_repo.add(AccountRecord(
            acct_id="00000000001",
            credit_limit=1000.00,
            expiration_date="2025-12-31",
            curr_cyc_credit=900.00,
            curr_cyc_debit=0.00,
        ))
        tran_repo = InMemoryTransactionRepository()
        tcatbal_repo = InMemoryTranCatBalRepository()
        # temp_bal = 900 - 0 + 100 = 1000 == limit
        transactions = [_make_daily_tran(amt=100.00)]

        result = run(transactions, xref_repo, acct_repo, tran_repo, tcatbal_repo,
                     timestamp_fn=_fixed_ts)

        self.assertEqual(result.reject_count, 0)

    def test_overlimit_by_one_cent(self):
        """Transaction that exceeds credit limit by 0.01 is rejected."""
        xref_repo = _make_xref_repo()
        acct_repo = InMemoryAccountRepository()
        acct_repo.add(AccountRecord(
            acct_id="00000000001",
            credit_limit=1000.00,
            expiration_date="2025-12-31",
            curr_cyc_credit=900.00,
            curr_cyc_debit=0.00,
        ))
        tran_repo = InMemoryTransactionRepository()
        tcatbal_repo = InMemoryTranCatBalRepository()
        # temp_bal = 900 - 0 + 100.01 = 1000.01 > 1000
        transactions = [_make_daily_tran(amt=100.01)]

        result = run(transactions, xref_repo, acct_repo, tran_repo, tcatbal_repo,
                     timestamp_fn=_fixed_ts)

        self.assertEqual(result.reject_count, 1)
        self.assertEqual(result.rejected_transactions[0].fail_reason, REASON_OVERLIMIT)

    def test_different_category_codes_create_separate_balances(self):
        """Transactions with different category codes create separate balance records."""
        xref_repo, acct_repo, tran_repo, tcatbal_repo = _make_all_repos()
        transactions = [
            _make_daily_tran(tran_id="0000000000000001", amt=100.00, type_cd="01", cat_cd="5000"),
            _make_daily_tran(tran_id="0000000000000002", amt=200.00, type_cd="02", cat_cd="6000"),
        ]

        run(transactions, xref_repo, acct_repo, tran_repo, tcatbal_repo,
            timestamp_fn=_fixed_ts)

        bal1 = tcatbal_repo.read_balance("00000000001", "01", "5000")
        bal2 = tcatbal_repo.read_balance("00000000001", "02", "6000")
        self.assertIsNotNone(bal1)
        self.assertIsNotNone(bal2)
        self.assertAlmostEqual(bal1.balance, 100.00)
        self.assertAlmostEqual(bal2.balance, 200.00)


# ===========================================================================
# 5. Data structure and repository tests
# ===========================================================================

class TestInMemoryRepos(unittest.TestCase):
    """Tests for in-memory repository implementations."""

    def test_tcatbal_repo_create_and_read(self):
        repo = InMemoryTranCatBalRepository()
        record = TranCatBalRecord(
            acct_id="00000000001", type_cd="01", cat_cd="5000", balance=100.00
        )
        repo.write_balance(record)

        found = repo.read_balance("00000000001", "01", "5000")
        self.assertIsNotNone(found)
        self.assertAlmostEqual(found.balance, 100.00)

    def test_tcatbal_repo_update(self):
        repo = InMemoryTranCatBalRepository()
        record = TranCatBalRecord(
            acct_id="00000000001", type_cd="01", cat_cd="5000", balance=100.00
        )
        repo.write_balance(record)

        record.balance = 300.00
        result = repo.update_balance(record)
        self.assertTrue(result)

        found = repo.read_balance("00000000001", "01", "5000")
        self.assertAlmostEqual(found.balance, 300.00)

    def test_tcatbal_repo_update_nonexistent(self):
        repo = InMemoryTranCatBalRepository()
        record = TranCatBalRecord(
            acct_id="99999999999", type_cd="01", cat_cd="5000", balance=100.00
        )
        result = repo.update_balance(record)
        self.assertFalse(result)

    def test_tcatbal_repo_read_nonexistent(self):
        repo = InMemoryTranCatBalRepository()
        found = repo.read_balance("99999999999", "01", "5000")
        self.assertIsNone(found)

    def test_account_repo_update_nonexistent(self):
        repo = InMemoryAccountRepository()
        result = repo.update_account(AccountRecord(acct_id="99999999999"))
        self.assertFalse(result)

    def test_transaction_repo_write(self):
        repo = InMemoryTransactionRepository()
        record = TransactionRecord(tran_id="0000000000000001")
        result = repo.write_transaction(record)
        self.assertTrue(result)
        self.assertEqual(len(repo.transactions), 1)


if __name__ == "__main__":
    unittest.main()
