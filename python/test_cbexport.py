"""
Unit tests for cbexport.py — the Python translation of CBEXPORT.CBL.

These tests verify the export logic that reads from multiple data sources
and produces a unified export record list.
"""

import unittest

from cbexport import (
    AccountRecord,
    CardRecord,
    CardXrefRecord,
    CustomerRecord,
    InMemoryExportDataRepository,
    TransactionRecord,
    export_customer_data,
    generate_timestamp,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXED_TIMESTAMP = "2024-06-15 10:30:00.00"


def _make_customer(cust_id: str = "000000001") -> CustomerRecord:
    return CustomerRecord(
        cust_id=cust_id,
        first_name="John",
        middle_name="M",
        last_name="Doe",
        addr_line_1="123 Main St",
        addr_line_2="Apt 4B",
        addr_line_3="",
        addr_state_cd="WA",
        addr_country_cd="USA",
        addr_zip="98101",
        phone_num_1="206-555-0100",
        phone_num_2="206-555-0101",
        ssn="123456789",
        govt_issued_id="DL123456",
        dob_yyyy_mm_dd="1985-03-15",
        eft_account_id="EFT0000001",
        pri_card_holder_ind="Y",
        fico_credit_score=750,
    )


def _make_account(acct_id: str = "00000000001") -> AccountRecord:
    return AccountRecord(
        acct_id=acct_id,
        active_status="Y",
        curr_bal=1500.75,
        credit_limit=10000.00,
        cash_credit_limit=2000.00,
        open_date="2020-01-15",
        expiration_date="2025-01-15",
        reissue_date="2024-01-15",
        curr_cyc_credit=500.00,
        curr_cyc_debit=200.50,
        addr_zip="98101",
        group_id="GRP001",
    )


def _make_xref(card_num: str = "4000123456789010") -> CardXrefRecord:
    return CardXrefRecord(
        card_num=card_num,
        cust_id="000000001",
        acct_id="00000000001",
    )


def _make_transaction(tran_id: str = "0000000000000001") -> TransactionRecord:
    return TransactionRecord(
        tran_id=tran_id,
        tran_type_cd="01",
        tran_cat_cd="5000",
        tran_source="ONLINE",
        tran_desc="Test purchase at store",
        tran_amt=100.50,
        tran_merchant_id="123456789",
        tran_merchant_name="ACME Store",
        tran_merchant_city="Seattle",
        tran_merchant_zip="98101",
        tran_card_num="4000123456789010",
        tran_orig_ts="2024-06-15 10:00:00.00",
        tran_proc_ts="2024-06-15 10:00:01.00",
    )


def _make_card(card_num: str = "4000123456789010") -> CardRecord:
    return CardRecord(
        card_num=card_num,
        card_acct_id="00000000001",
        card_cvv_cd="123",
        card_embossed_name="JOHN M DOE",
        card_expiration_date="2025-12-31",
        card_active_status="Y",
    )


def _make_loaded_repo() -> InMemoryExportDataRepository:
    """Return a repo pre-loaded with one record of each type."""
    repo = InMemoryExportDataRepository()
    repo.customers.append(_make_customer())
    repo.accounts.append(_make_account())
    repo.xrefs.append(_make_xref())
    repo.transactions.append(_make_transaction())
    repo.cards.append(_make_card())
    return repo


# ===========================================================================
# 1. Empty repository
# ===========================================================================

class TestEmptyExport(unittest.TestCase):
    """Export from an empty repository should produce no records."""

    def test_empty_repo_returns_no_records(self) -> None:
        repo = InMemoryExportDataRepository()
        records, stats = export_customer_data(repo, timestamp=FIXED_TIMESTAMP)
        self.assertEqual(len(records), 0)
        self.assertEqual(stats.total_records, 0)

    def test_empty_repo_all_counters_zero(self) -> None:
        repo = InMemoryExportDataRepository()
        _, stats = export_customer_data(repo, timestamp=FIXED_TIMESTAMP)
        self.assertEqual(stats.customer_records, 0)
        self.assertEqual(stats.account_records, 0)
        self.assertEqual(stats.xref_records, 0)
        self.assertEqual(stats.transaction_records, 0)
        self.assertEqual(stats.card_records, 0)


# ===========================================================================
# 2. Single record of each type
# ===========================================================================

class TestSingleRecordExport(unittest.TestCase):
    """Export with one record of each type."""

    def setUp(self) -> None:
        self.repo = _make_loaded_repo()
        self.records, self.stats = export_customer_data(
            self.repo, timestamp=FIXED_TIMESTAMP
        )

    def test_total_records(self) -> None:
        self.assertEqual(len(self.records), 5)
        self.assertEqual(self.stats.total_records, 5)

    def test_record_type_order(self) -> None:
        """Records are exported in order: C, A, X, T, D."""
        types = [r.rec_type for r in self.records]
        self.assertEqual(types, ["C", "A", "X", "T", "D"])

    def test_sequence_numbers_are_sequential(self) -> None:
        seq_nums = [r.sequence_num for r in self.records]
        self.assertEqual(seq_nums, [1, 2, 3, 4, 5])

    def test_timestamp_is_set(self) -> None:
        for rec in self.records:
            self.assertEqual(rec.timestamp, FIXED_TIMESTAMP)

    def test_branch_id_default(self) -> None:
        for rec in self.records:
            self.assertEqual(rec.branch_id, "0001")

    def test_region_code_default(self) -> None:
        for rec in self.records:
            self.assertEqual(rec.region_code, "NORTH")

    def test_customer_data_attached(self) -> None:
        cust_rec = self.records[0]
        self.assertEqual(cust_rec.rec_type, "C")
        self.assertIsNotNone(cust_rec.customer_data)
        self.assertEqual(cust_rec.customer_data.first_name, "John")

    def test_account_data_attached(self) -> None:
        acct_rec = self.records[1]
        self.assertEqual(acct_rec.rec_type, "A")
        self.assertIsNotNone(acct_rec.account_data)
        self.assertEqual(acct_rec.account_data.acct_id, "00000000001")

    def test_xref_data_attached(self) -> None:
        xref_rec = self.records[2]
        self.assertEqual(xref_rec.rec_type, "X")
        self.assertIsNotNone(xref_rec.xref_data)
        self.assertEqual(xref_rec.xref_data.card_num, "4000123456789010")

    def test_transaction_data_attached(self) -> None:
        tran_rec = self.records[3]
        self.assertEqual(tran_rec.rec_type, "T")
        self.assertIsNotNone(tran_rec.transaction_data)
        self.assertAlmostEqual(tran_rec.transaction_data.tran_amt, 100.50)

    def test_card_data_attached(self) -> None:
        card_rec = self.records[4]
        self.assertEqual(card_rec.rec_type, "D")
        self.assertIsNotNone(card_rec.card_data)
        self.assertEqual(card_rec.card_data.card_embossed_name, "JOHN M DOE")

    def test_statistics_per_type(self) -> None:
        self.assertEqual(self.stats.customer_records, 1)
        self.assertEqual(self.stats.account_records, 1)
        self.assertEqual(self.stats.xref_records, 1)
        self.assertEqual(self.stats.transaction_records, 1)
        self.assertEqual(self.stats.card_records, 1)


# ===========================================================================
# 3. Multiple records
# ===========================================================================

class TestMultipleRecordExport(unittest.TestCase):
    """Export with multiple records of some types."""

    def test_multiple_customers(self) -> None:
        repo = InMemoryExportDataRepository()
        repo.customers.append(_make_customer("000000001"))
        repo.customers.append(_make_customer("000000002"))
        repo.customers.append(_make_customer("000000003"))

        records, stats = export_customer_data(repo, timestamp=FIXED_TIMESTAMP)
        self.assertEqual(stats.customer_records, 3)
        self.assertEqual(stats.total_records, 3)
        self.assertEqual(len(records), 3)
        self.assertTrue(all(r.rec_type == "C" for r in records))

    def test_mixed_multiple(self) -> None:
        repo = InMemoryExportDataRepository()
        repo.customers.append(_make_customer("000000001"))
        repo.customers.append(_make_customer("000000002"))
        repo.accounts.append(_make_account("00000000001"))
        repo.transactions.append(_make_transaction("0000000000000001"))
        repo.transactions.append(_make_transaction("0000000000000002"))
        repo.transactions.append(_make_transaction("0000000000000003"))

        records, stats = export_customer_data(repo, timestamp=FIXED_TIMESTAMP)
        self.assertEqual(stats.total_records, 6)
        self.assertEqual(stats.customer_records, 2)
        self.assertEqual(stats.account_records, 1)
        self.assertEqual(stats.transaction_records, 3)

        # Sequence numbers still sequential across types
        seq_nums = [r.sequence_num for r in records]
        self.assertEqual(seq_nums, [1, 2, 3, 4, 5, 6])


# ===========================================================================
# 4. Custom branch/region
# ===========================================================================

class TestCustomBranchRegion(unittest.TestCase):
    """Export with custom branch and region codes."""

    def test_custom_branch_and_region(self) -> None:
        repo = InMemoryExportDataRepository()
        repo.customers.append(_make_customer())

        records, _ = export_customer_data(
            repo,
            branch_id="0042",
            region_code="SOUTH",
            timestamp=FIXED_TIMESTAMP,
        )
        self.assertEqual(records[0].branch_id, "0042")
        self.assertEqual(records[0].region_code, "SOUTH")


# ===========================================================================
# 5. Timestamp generation
# ===========================================================================

class TestTimestampGeneration(unittest.TestCase):
    """Tests for the generate_timestamp helper."""

    def test_timestamp_format(self) -> None:
        ts = generate_timestamp()
        # Should be 26 characters: YYYY-MM-DD HH:MM:SS.00
        self.assertEqual(len(ts), 22)  # "YYYY-MM-DD HH:MM:SS.00"
        self.assertTrue(ts.endswith(".00"))

    def test_timestamp_has_date_and_time(self) -> None:
        ts = generate_timestamp()
        self.assertIn("-", ts)
        self.assertIn(":", ts)
        self.assertIn(" ", ts)


# ===========================================================================
# 6. Data integrity — field values preserved
# ===========================================================================

class TestDataIntegrity(unittest.TestCase):
    """Verify all field values are preserved through export."""

    def test_customer_fields_preserved(self) -> None:
        repo = InMemoryExportDataRepository()
        original = _make_customer()
        repo.customers.append(original)

        records, _ = export_customer_data(repo, timestamp=FIXED_TIMESTAMP)
        exported = records[0].customer_data

        self.assertEqual(exported.cust_id, original.cust_id)
        self.assertEqual(exported.first_name, original.first_name)
        self.assertEqual(exported.middle_name, original.middle_name)
        self.assertEqual(exported.last_name, original.last_name)
        self.assertEqual(exported.addr_line_1, original.addr_line_1)
        self.assertEqual(exported.addr_zip, original.addr_zip)
        self.assertEqual(exported.ssn, original.ssn)
        self.assertEqual(exported.fico_credit_score, original.fico_credit_score)

    def test_account_fields_preserved(self) -> None:
        repo = InMemoryExportDataRepository()
        original = _make_account()
        repo.accounts.append(original)

        records, _ = export_customer_data(repo, timestamp=FIXED_TIMESTAMP)
        exported = records[0].account_data

        self.assertEqual(exported.acct_id, original.acct_id)
        self.assertAlmostEqual(exported.curr_bal, original.curr_bal)
        self.assertAlmostEqual(exported.credit_limit, original.credit_limit)
        self.assertEqual(exported.open_date, original.open_date)

    def test_transaction_fields_preserved(self) -> None:
        repo = InMemoryExportDataRepository()
        original = _make_transaction()
        repo.transactions.append(original)

        records, _ = export_customer_data(repo, timestamp=FIXED_TIMESTAMP)
        exported = records[0].transaction_data

        self.assertEqual(exported.tran_id, original.tran_id)
        self.assertAlmostEqual(exported.tran_amt, original.tran_amt)
        self.assertEqual(exported.tran_desc, original.tran_desc)
        self.assertEqual(exported.tran_card_num, original.tran_card_num)


if __name__ == "__main__":
    unittest.main()
