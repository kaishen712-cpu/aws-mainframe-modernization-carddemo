"""
Unit tests for cbact04c.py — the Python translation of CBACT04C.CBL.

These tests verify the batch interest calculation logic including rate
lookups, interest computation, transaction creation, and account updates.
"""

import unittest

from cbact04c import (
    AccountRecord,
    CardXrefRecord,
    DisclosureGroupRecord,
    InMemoryAccountRepository,
    InMemoryCardXrefRepository,
    InMemoryDisclosureGroupRepository,
    InMemoryTransactionRepository,
    TranCatBalRecord,
    TransactionRecord,
    compute_interest,
    create_interest_transaction,
    get_interest_rate,
    run,
    update_account_for_interest,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXED_TIMESTAMP = "2024-06-15-10.30.00.000000"
PARM_DATE = "2024-06-15"


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
        curr_bal=5000.00,
        credit_limit=10000.00,
        curr_cyc_credit=3000.00,
        curr_cyc_debit=1000.00,
        group_id="PLATINUM",
    ))
    repo.add(AccountRecord(
        acct_id="00000000002",
        active_status="Y",
        curr_bal=2000.00,
        credit_limit=5000.00,
        curr_cyc_credit=1500.00,
        curr_cyc_debit=500.00,
        group_id="STANDARD",
    ))
    return repo


def _make_discgrp_repo() -> InMemoryDisclosureGroupRepository:
    repo = InMemoryDisclosureGroupRepository()
    # PLATINUM group rates
    repo.add(DisclosureGroupRecord(
        acct_group_id="PLATINUM", tran_type_cd="01", tran_cat_cd="5000",
        int_rate=18.00,
    ))
    repo.add(DisclosureGroupRecord(
        acct_group_id="PLATINUM", tran_type_cd="02", tran_cat_cd="6000",
        int_rate=24.00,
    ))
    # STANDARD group rates
    repo.add(DisclosureGroupRecord(
        acct_group_id="STANDARD", tran_type_cd="01", tran_cat_cd="5000",
        int_rate=21.00,
    ))
    # DEFAULT fallback rates
    repo.add(DisclosureGroupRecord(
        acct_group_id="DEFAULT", tran_type_cd="01", tran_cat_cd="5000",
        int_rate=25.00,
    ))
    repo.add(DisclosureGroupRecord(
        acct_group_id="DEFAULT", tran_type_cd="02", tran_cat_cd="6000",
        int_rate=28.00,
    ))
    return repo


def _make_all_repos():
    """Return all four repos needed for a batch run."""
    return (
        _make_xref_repo(),
        _make_acct_repo(),
        _make_discgrp_repo(),
        InMemoryTransactionRepository(),
    )


# ===========================================================================
# 1. Interest computation tests
# ===========================================================================

class TestComputeInterest(unittest.TestCase):
    """Tests for the compute_interest function."""

    def test_basic_calculation(self):
        """18% annual rate on $1200 balance -> $18.00 monthly."""
        # (1200 * 18) / 1200 = 18.00
        result = compute_interest(1200.00, 18.00)
        self.assertAlmostEqual(result, 18.00)

    def test_zero_balance(self):
        """Zero balance -> zero interest."""
        result = compute_interest(0.0, 18.00)
        self.assertAlmostEqual(result, 0.0)

    def test_zero_rate(self):
        """Zero rate -> zero interest."""
        result = compute_interest(1000.00, 0.0)
        self.assertAlmostEqual(result, 0.0)

    def test_standard_calculation(self):
        """21% annual rate on $5000 balance."""
        # (5000 * 21) / 1200 = 87.50
        result = compute_interest(5000.00, 21.00)
        self.assertAlmostEqual(result, 87.50)

    def test_fractional_rate(self):
        """18.50% rate on $1000 balance."""
        # (1000 * 18.50) / 1200 = 15.4166...
        result = compute_interest(1000.00, 18.50)
        self.assertAlmostEqual(result, 15.4166, places=3)

    def test_negative_balance(self):
        """Negative balance produces negative interest (credit)."""
        result = compute_interest(-1200.00, 18.00)
        self.assertAlmostEqual(result, -18.00)

    def test_large_balance(self):
        """Large balance calculation."""
        # (100000 * 24) / 1200 = 2000.00
        result = compute_interest(100000.00, 24.00)
        self.assertAlmostEqual(result, 2000.00)


# ===========================================================================
# 2. Interest rate lookup tests
# ===========================================================================

class TestGetInterestRate(unittest.TestCase):
    """Tests for the get_interest_rate function."""

    def test_exact_group_match(self):
        """Rate found for exact group/type/category."""
        repo = _make_discgrp_repo()
        record, used_default = get_interest_rate("PLATINUM", "01", "5000", repo)

        self.assertIsNotNone(record)
        self.assertAlmostEqual(record.int_rate, 18.00)
        self.assertFalse(used_default)

    def test_fallback_to_default(self):
        """Rate not found for group, falls back to DEFAULT."""
        repo = _make_discgrp_repo()
        record, used_default = get_interest_rate("UNKNOWN_GRP", "01", "5000", repo)

        self.assertIsNotNone(record)
        self.assertAlmostEqual(record.int_rate, 25.00)
        self.assertTrue(used_default)

    def test_not_found_at_all(self):
        """Rate not found for group or default -> None."""
        repo = _make_discgrp_repo()
        record, used_default = get_interest_rate("UNKNOWN_GRP", "99", "9999", repo)

        self.assertIsNone(record)
        self.assertFalse(used_default)


# ===========================================================================
# 3. Interest transaction creation tests
# ===========================================================================

class TestCreateInterestTransaction(unittest.TestCase):
    """Tests for the create_interest_transaction function."""

    def test_basic_creation(self):
        """Create an interest transaction record."""
        tran = create_interest_transaction(
            acct_id="00000000001",
            card_num="4000123456789010",
            monthly_interest=18.00,
            parm_date="2024-06-15",
            tran_suffix=1,
            timestamp_fn=_fixed_ts,
        )

        self.assertEqual(tran.tran_id, "2024-06-15000001")
        self.assertEqual(tran.tran_type_cd, "01")
        self.assertEqual(tran.tran_cat_cd, "0005")
        self.assertEqual(tran.tran_source, "System")
        self.assertIn("Int. for a/c", tran.tran_desc)
        self.assertIn("00000000001", tran.tran_desc)
        self.assertAlmostEqual(tran.tran_amt, 18.00)
        self.assertEqual(tran.tran_card_num, "4000123456789010")
        self.assertEqual(tran.tran_orig_ts, FIXED_TIMESTAMP)
        self.assertEqual(tran.tran_proc_ts, FIXED_TIMESTAMP)

    def test_suffix_increments(self):
        """Different suffixes produce different transaction IDs."""
        tran1 = create_interest_transaction(
            "00000000001", "4000123456789010", 10.0,
            "2024-06-15", 1, _fixed_ts,
        )
        tran2 = create_interest_transaction(
            "00000000001", "4000123456789010", 20.0,
            "2024-06-15", 2, _fixed_ts,
        )

        self.assertEqual(tran1.tran_id, "2024-06-15000001")
        self.assertEqual(tran2.tran_id, "2024-06-15000002")

    def test_merchant_fields_empty(self):
        """Interest transactions have empty/zero merchant fields."""
        tran = create_interest_transaction(
            "00000000001", "4000123456789010", 18.00,
            "2024-06-15", 1, _fixed_ts,
        )

        self.assertEqual(tran.tran_merchant_id, "0")
        self.assertEqual(tran.tran_merchant_name, "")
        self.assertEqual(tran.tran_merchant_city, "")
        self.assertEqual(tran.tran_merchant_zip, "")


# ===========================================================================
# 4. Account update tests
# ===========================================================================

class TestUpdateAccountForInterest(unittest.TestCase):
    """Tests for the update_account_for_interest function."""

    def test_adds_interest_to_balance(self):
        """Interest is added to current balance."""
        acct_repo = InMemoryAccountRepository()
        account = AccountRecord(
            acct_id="00000000001",
            curr_bal=5000.00,
            curr_cyc_credit=3000.00,
            curr_cyc_debit=1000.00,
        )
        acct_repo.add(account)

        update_account_for_interest(account, 50.00, acct_repo)

        updated = acct_repo.read_account("00000000001")
        self.assertAlmostEqual(updated.curr_bal, 5050.00)

    def test_resets_cycle_credits_and_debits(self):
        """Cycle credit and debit are reset to zero."""
        acct_repo = InMemoryAccountRepository()
        account = AccountRecord(
            acct_id="00000000001",
            curr_bal=5000.00,
            curr_cyc_credit=3000.00,
            curr_cyc_debit=1000.00,
        )
        acct_repo.add(account)

        update_account_for_interest(account, 50.00, acct_repo)

        updated = acct_repo.read_account("00000000001")
        self.assertAlmostEqual(updated.curr_cyc_credit, 0.0)
        self.assertAlmostEqual(updated.curr_cyc_debit, 0.0)

    def test_zero_interest(self):
        """Zero interest still resets cycle fields."""
        acct_repo = InMemoryAccountRepository()
        account = AccountRecord(
            acct_id="00000000001",
            curr_bal=5000.00,
            curr_cyc_credit=3000.00,
            curr_cyc_debit=1000.00,
        )
        acct_repo.add(account)

        update_account_for_interest(account, 0.0, acct_repo)

        updated = acct_repo.read_account("00000000001")
        self.assertAlmostEqual(updated.curr_bal, 5000.00)
        self.assertAlmostEqual(updated.curr_cyc_credit, 0.0)


# ===========================================================================
# 5. Full batch run tests
# ===========================================================================

class TestRun(unittest.TestCase):
    """End-to-end tests for the run() function."""

    def test_empty_input(self):
        """No category balances -> zero counts."""
        xref_repo, acct_repo, discgrp_repo, tran_repo = _make_all_repos()

        result = run(
            [], xref_repo, acct_repo, discgrp_repo, tran_repo,
            parm_date=PARM_DATE, timestamp_fn=_fixed_ts,
        )

        self.assertEqual(result.records_read, 0)
        self.assertEqual(result.accounts_processed, 0)
        self.assertEqual(result.interest_transactions_created, 0)

    def test_single_account_single_category(self):
        """One account with one category balance."""
        xref_repo, acct_repo, discgrp_repo, tran_repo = _make_all_repos()
        cat_balances = [
            TranCatBalRecord(acct_id="00000000001", type_cd="01", cat_cd="5000",
                             balance=1200.00),
        ]

        result = run(
            cat_balances, xref_repo, acct_repo, discgrp_repo, tran_repo,
            parm_date=PARM_DATE, timestamp_fn=_fixed_ts,
        )

        self.assertEqual(result.records_read, 1)
        self.assertEqual(result.accounts_processed, 1)
        self.assertEqual(result.interest_transactions_created, 1)
        # Interest: (1200 * 18) / 1200 = 18.00
        self.assertAlmostEqual(result.total_interest_charged, 18.00)

        # Verify account was updated
        acct = acct_repo.read_account("00000000001")
        # Original 5000 + 18 = 5018
        self.assertAlmostEqual(acct.curr_bal, 5018.00)
        self.assertAlmostEqual(acct.curr_cyc_credit, 0.0)
        self.assertAlmostEqual(acct.curr_cyc_debit, 0.0)

        # Verify transaction was written
        self.assertEqual(len(tran_repo.transactions), 1)
        tran = tran_repo.transactions[0]
        self.assertAlmostEqual(tran.tran_amt, 18.00)
        self.assertEqual(tran.tran_card_num, "4000123456789010")

    def test_single_account_multiple_categories(self):
        """One account with multiple category balances."""
        xref_repo, acct_repo, discgrp_repo, tran_repo = _make_all_repos()
        cat_balances = [
            TranCatBalRecord(acct_id="00000000001", type_cd="01", cat_cd="5000",
                             balance=1200.00),
            TranCatBalRecord(acct_id="00000000001", type_cd="02", cat_cd="6000",
                             balance=2400.00),
        ]

        result = run(
            cat_balances, xref_repo, acct_repo, discgrp_repo, tran_repo,
            parm_date=PARM_DATE, timestamp_fn=_fixed_ts,
        )

        self.assertEqual(result.records_read, 2)
        self.assertEqual(result.accounts_processed, 1)
        self.assertEqual(result.interest_transactions_created, 2)
        # Interest: (1200 * 18) / 1200 + (2400 * 24) / 1200 = 18 + 48 = 66
        self.assertAlmostEqual(result.total_interest_charged, 66.00)

    def test_multiple_accounts(self):
        """Multiple accounts with category balances (sorted by acct_id)."""
        xref_repo, acct_repo, discgrp_repo, tran_repo = _make_all_repos()
        cat_balances = [
            TranCatBalRecord(acct_id="00000000001", type_cd="01", cat_cd="5000",
                             balance=1200.00),
            TranCatBalRecord(acct_id="00000000002", type_cd="01", cat_cd="5000",
                             balance=2400.00),
        ]

        result = run(
            cat_balances, xref_repo, acct_repo, discgrp_repo, tran_repo,
            parm_date=PARM_DATE, timestamp_fn=_fixed_ts,
        )

        self.assertEqual(result.records_read, 2)
        self.assertEqual(result.accounts_processed, 2)
        self.assertEqual(result.interest_transactions_created, 2)

        # Account 1: (1200 * 18) / 1200 = 18.00
        # Account 2: (2400 * 21) / 1200 = 42.00
        self.assertAlmostEqual(result.total_interest_charged, 60.00)

        # Verify both accounts updated
        acct1 = acct_repo.read_account("00000000001")
        self.assertAlmostEqual(acct1.curr_bal, 5018.00)

        acct2 = acct_repo.read_account("00000000002")
        self.assertAlmostEqual(acct2.curr_bal, 2042.00)

    def test_default_rate_fallback(self):
        """Rate not found for group, uses DEFAULT rate."""
        xref_repo, acct_repo, discgrp_repo, tran_repo = _make_all_repos()
        # Account 2 has group "STANDARD", which has no rate for type=02/cat=6000
        # Should fall back to DEFAULT rate (28%)
        cat_balances = [
            TranCatBalRecord(acct_id="00000000002", type_cd="02", cat_cd="6000",
                             balance=1200.00),
        ]

        result = run(
            cat_balances, xref_repo, acct_repo, discgrp_repo, tran_repo,
            parm_date=PARM_DATE, timestamp_fn=_fixed_ts,
        )

        # Interest: (1200 * 28) / 1200 = 28.00
        self.assertAlmostEqual(result.total_interest_charged, 28.00)
        self.assertEqual(result.interest_transactions_created, 1)

        # Verify the summary shows default rate was used
        summary = result.account_summaries[0]
        self.assertTrue(summary.category_results[0].used_default_rate)

    def test_zero_rate_skips_interest(self):
        """Zero interest rate -> no interest computed for that category."""
        xref_repo, acct_repo, discgrp_repo, tran_repo = _make_all_repos()
        # Add a zero-rate record
        discgrp_repo.add(DisclosureGroupRecord(
            acct_group_id="PLATINUM", tran_type_cd="03", tran_cat_cd="7000",
            int_rate=0.0,
        ))
        cat_balances = [
            TranCatBalRecord(acct_id="00000000001", type_cd="03", cat_cd="7000",
                             balance=5000.00),
        ]

        result = run(
            cat_balances, xref_repo, acct_repo, discgrp_repo, tran_repo,
            parm_date=PARM_DATE, timestamp_fn=_fixed_ts,
        )

        self.assertEqual(result.interest_transactions_created, 0)
        self.assertAlmostEqual(result.total_interest_charged, 0.0)

    def test_no_rate_found_skips_interest(self):
        """No rate found (even DEFAULT) -> no interest for that category."""
        xref_repo, acct_repo, discgrp_repo, tran_repo = _make_all_repos()
        cat_balances = [
            TranCatBalRecord(acct_id="00000000001", type_cd="99", cat_cd="9999",
                             balance=5000.00),
        ]

        result = run(
            cat_balances, xref_repo, acct_repo, discgrp_repo, tran_repo,
            parm_date=PARM_DATE, timestamp_fn=_fixed_ts,
        )

        self.assertEqual(result.interest_transactions_created, 0)
        self.assertAlmostEqual(result.total_interest_charged, 0.0)

    def test_transaction_ids_are_sequential(self):
        """Transaction IDs use incrementing suffixes."""
        xref_repo, acct_repo, discgrp_repo, tran_repo = _make_all_repos()
        cat_balances = [
            TranCatBalRecord(acct_id="00000000001", type_cd="01", cat_cd="5000",
                             balance=1200.00),
            TranCatBalRecord(acct_id="00000000001", type_cd="02", cat_cd="6000",
                             balance=2400.00),
        ]

        run(
            cat_balances, xref_repo, acct_repo, discgrp_repo, tran_repo,
            parm_date=PARM_DATE, timestamp_fn=_fixed_ts,
        )

        self.assertEqual(len(tran_repo.transactions), 2)
        self.assertEqual(tran_repo.transactions[0].tran_id, "2024-06-15000001")
        self.assertEqual(tran_repo.transactions[1].tran_id, "2024-06-15000002")

    def test_account_summaries_populated(self):
        """Batch result includes summaries for each account."""
        xref_repo, acct_repo, discgrp_repo, tran_repo = _make_all_repos()
        cat_balances = [
            TranCatBalRecord(acct_id="00000000001", type_cd="01", cat_cd="5000",
                             balance=1200.00),
            TranCatBalRecord(acct_id="00000000002", type_cd="01", cat_cd="5000",
                             balance=2400.00),
        ]

        result = run(
            cat_balances, xref_repo, acct_repo, discgrp_repo, tran_repo,
            parm_date=PARM_DATE, timestamp_fn=_fixed_ts,
        )

        self.assertEqual(len(result.account_summaries), 2)

        summary1 = result.account_summaries[0]
        self.assertEqual(summary1.acct_id, "00000000001")
        self.assertAlmostEqual(summary1.total_interest, 18.00)
        self.assertEqual(len(summary1.category_results), 1)
        self.assertEqual(len(summary1.transactions_created), 1)

        summary2 = result.account_summaries[1]
        self.assertEqual(summary2.acct_id, "00000000002")
        self.assertAlmostEqual(summary2.total_interest, 42.00)


# ===========================================================================
# 6. Edge cases
# ===========================================================================

class TestEdgeCases(unittest.TestCase):
    """Edge case tests."""

    def test_single_record(self):
        """Single category balance record."""
        xref_repo, acct_repo, discgrp_repo, tran_repo = _make_all_repos()
        cat_balances = [
            TranCatBalRecord(acct_id="00000000001", type_cd="01", cat_cd="5000",
                             balance=600.00),
        ]

        result = run(
            cat_balances, xref_repo, acct_repo, discgrp_repo, tran_repo,
            parm_date=PARM_DATE, timestamp_fn=_fixed_ts,
        )

        # (600 * 18) / 1200 = 9.00
        self.assertAlmostEqual(result.total_interest_charged, 9.00)
        self.assertEqual(result.accounts_processed, 1)

    def test_account_not_found(self):
        """Category balance for non-existent account."""
        xref_repo, acct_repo, discgrp_repo, tran_repo = _make_all_repos()
        cat_balances = [
            TranCatBalRecord(acct_id="99999999999", type_cd="01", cat_cd="5000",
                             balance=1000.00),
        ]

        result = run(
            cat_balances, xref_repo, acct_repo, discgrp_repo, tran_repo,
            parm_date=PARM_DATE, timestamp_fn=_fixed_ts,
        )

        self.assertEqual(result.records_read, 1)
        self.assertEqual(result.interest_transactions_created, 0)

    def test_xref_not_found(self):
        """Account exists but no xref -> still calculates interest with empty card."""
        xref_repo = InMemoryCardXrefRepository()  # empty, no xrefs
        acct_repo = _make_acct_repo()
        discgrp_repo = _make_discgrp_repo()
        tran_repo = InMemoryTransactionRepository()
        cat_balances = [
            TranCatBalRecord(acct_id="00000000001", type_cd="01", cat_cd="5000",
                             balance=1200.00),
        ]

        result = run(
            cat_balances, xref_repo, acct_repo, discgrp_repo, tran_repo,
            parm_date=PARM_DATE, timestamp_fn=_fixed_ts,
        )

        self.assertEqual(result.interest_transactions_created, 1)
        # Transaction created with empty card number
        tran = tran_repo.transactions[0]
        self.assertEqual(tran.tran_card_num, "")

    def test_negative_balance_produces_negative_interest(self):
        """Negative category balance -> negative interest (credit)."""
        xref_repo, acct_repo, discgrp_repo, tran_repo = _make_all_repos()
        cat_balances = [
            TranCatBalRecord(acct_id="00000000001", type_cd="01", cat_cd="5000",
                             balance=-1200.00),
        ]

        result = run(
            cat_balances, xref_repo, acct_repo, discgrp_repo, tran_repo,
            parm_date=PARM_DATE, timestamp_fn=_fixed_ts,
        )

        # (−1200 × 18) / 1200 = −18.00
        self.assertAlmostEqual(result.total_interest_charged, -18.00)

    def test_default_parm_date(self):
        """When no parm_date provided, uses current date."""
        xref_repo, acct_repo, discgrp_repo, tran_repo = _make_all_repos()
        cat_balances = [
            TranCatBalRecord(acct_id="00000000001", type_cd="01", cat_cd="5000",
                             balance=1200.00),
        ]

        result = run(
            cat_balances, xref_repo, acct_repo, discgrp_repo, tran_repo,
            timestamp_fn=_fixed_ts,
        )

        self.assertEqual(result.interest_transactions_created, 1)
        # Transaction ID should start with current date
        tran = tran_repo.transactions[0]
        self.assertTrue(len(tran.tran_id) > 0)


# ===========================================================================
# 7. Data structure and repository tests
# ===========================================================================

class TestInMemoryRepos(unittest.TestCase):
    """Tests for in-memory repository implementations."""

    def test_xref_repo_by_acct(self):
        repo = InMemoryCardXrefRepository()
        repo.add(CardXrefRecord(
            card_num="4000123456789010", cust_id="1", acct_id="00000000001"
        ))
        found = repo.lookup_by_acct_id("00000000001")
        self.assertIsNotNone(found)
        self.assertEqual(found.card_num, "4000123456789010")

    def test_xref_repo_not_found(self):
        repo = InMemoryCardXrefRepository()
        found = repo.lookup_by_acct_id("99999999999")
        self.assertIsNone(found)

    def test_discgrp_repo_add_and_read(self):
        repo = InMemoryDisclosureGroupRepository()
        repo.add(DisclosureGroupRecord(
            acct_group_id="GROUP1", tran_type_cd="01", tran_cat_cd="5000",
            int_rate=18.00,
        ))
        found = repo.read_rate("GROUP1", "01", "5000")
        self.assertIsNotNone(found)
        self.assertAlmostEqual(found.int_rate, 18.00)

    def test_discgrp_repo_not_found(self):
        repo = InMemoryDisclosureGroupRepository()
        found = repo.read_rate("NONEXISTENT", "01", "5000")
        self.assertIsNone(found)

    def test_account_repo_update(self):
        repo = InMemoryAccountRepository()
        acct = AccountRecord(acct_id="00000000001", curr_bal=1000.00)
        repo.add(acct)

        acct.curr_bal = 2000.00
        result = repo.update_account(acct)
        self.assertTrue(result)

        updated = repo.read_account("00000000001")
        self.assertAlmostEqual(updated.curr_bal, 2000.00)

    def test_account_repo_update_nonexistent(self):
        repo = InMemoryAccountRepository()
        result = repo.update_account(AccountRecord(acct_id="99999999999"))
        self.assertFalse(result)

    def test_transaction_repo_write(self):
        repo = InMemoryTransactionRepository()
        tran = TransactionRecord(tran_id="0000000000000001")
        result = repo.write_transaction(tran)
        self.assertTrue(result)
        self.assertEqual(len(repo.transactions), 1)


if __name__ == "__main__":
    unittest.main()
