"""
Unit tests for cbimport.py — the Python translation of CBIMPORT.CBL.

These tests verify the import logic that reads export records and
dispatches them to individual repositories. Includes round-trip
tests with cbexport to verify data integrity.
"""

import unittest

from cbexport import (
    AccountRecord,
    CardRecord,
    CardXrefRecord,
    CustomerRecord,
    ExportRecord,
    InMemoryExportDataRepository,
    TransactionRecord,
    export_customer_data,
)
from cbimport import (
    InMemoryImportDataRepository,
    import_customer_data,
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


# ===========================================================================
# 1. Empty import
# ===========================================================================

class TestEmptyImport(unittest.TestCase):
    """Import with no records."""

    def test_empty_list_returns_empty_result(self) -> None:
        repo = InMemoryImportDataRepository()
        result = import_customer_data([], repo)
        self.assertEqual(result.statistics.total_records_read, 0)
        self.assertEqual(len(result.customers), 0)
        self.assertEqual(len(result.errors), 0)


# ===========================================================================
# 2. Single record import by type
# ===========================================================================

class TestSingleRecordImport(unittest.TestCase):
    """Import a single record of each type."""

    def test_import_customer(self) -> None:
        repo = InMemoryImportDataRepository()
        rec = ExportRecord(
            rec_type="C",
            timestamp=FIXED_TIMESTAMP,
            sequence_num=1,
            customer_data=_make_customer(),
        )
        result = import_customer_data([rec], repo)
        self.assertEqual(result.statistics.customer_records, 1)
        self.assertEqual(len(repo.customers), 1)
        self.assertEqual(repo.customers[0].first_name, "John")

    def test_import_account(self) -> None:
        repo = InMemoryImportDataRepository()
        rec = ExportRecord(
            rec_type="A",
            timestamp=FIXED_TIMESTAMP,
            sequence_num=1,
            account_data=_make_account(),
        )
        result = import_customer_data([rec], repo)
        self.assertEqual(result.statistics.account_records, 1)
        self.assertEqual(len(repo.accounts), 1)
        self.assertAlmostEqual(repo.accounts[0].curr_bal, 1500.75)

    def test_import_xref(self) -> None:
        repo = InMemoryImportDataRepository()
        rec = ExportRecord(
            rec_type="X",
            timestamp=FIXED_TIMESTAMP,
            sequence_num=1,
            xref_data=_make_xref(),
        )
        result = import_customer_data([rec], repo)
        self.assertEqual(result.statistics.xref_records, 1)
        self.assertEqual(len(repo.xrefs), 1)
        self.assertEqual(repo.xrefs[0].card_num, "4000123456789010")

    def test_import_transaction(self) -> None:
        repo = InMemoryImportDataRepository()
        rec = ExportRecord(
            rec_type="T",
            timestamp=FIXED_TIMESTAMP,
            sequence_num=1,
            transaction_data=_make_transaction(),
        )
        result = import_customer_data([rec], repo)
        self.assertEqual(result.statistics.transaction_records, 1)
        self.assertEqual(len(repo.transactions), 1)
        self.assertAlmostEqual(repo.transactions[0].tran_amt, 100.50)

    def test_import_card(self) -> None:
        repo = InMemoryImportDataRepository()
        rec = ExportRecord(
            rec_type="D",
            timestamp=FIXED_TIMESTAMP,
            sequence_num=1,
            card_data=_make_card(),
        )
        result = import_customer_data([rec], repo)
        self.assertEqual(result.statistics.card_records, 1)
        self.assertEqual(len(repo.cards), 1)
        self.assertEqual(repo.cards[0].card_embossed_name, "JOHN M DOE")


# ===========================================================================
# 3. Unknown record types
# ===========================================================================

class TestUnknownRecordTypes(unittest.TestCase):
    """Import with unrecognized record types."""

    def test_unknown_type_creates_error(self) -> None:
        repo = InMemoryImportDataRepository()
        rec = ExportRecord(
            rec_type="Z",
            timestamp=FIXED_TIMESTAMP,
            sequence_num=42,
        )
        result = import_customer_data([rec], repo)
        self.assertEqual(result.statistics.unknown_record_types, 1)
        self.assertEqual(result.statistics.error_records, 1)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0].record_type, "Z")
        self.assertEqual(result.errors[0].sequence_num, 42)
        self.assertIn("Unknown record type", result.errors[0].message)

    def test_empty_type_creates_error(self) -> None:
        repo = InMemoryImportDataRepository()
        rec = ExportRecord(
            rec_type="",
            timestamp=FIXED_TIMESTAMP,
            sequence_num=1,
        )
        result = import_customer_data([rec], repo)
        self.assertEqual(result.statistics.unknown_record_types, 1)

    def test_missing_data_for_type_creates_error(self) -> None:
        """Record type 'C' but no customer_data attached."""
        repo = InMemoryImportDataRepository()
        rec = ExportRecord(
            rec_type="C",
            timestamp=FIXED_TIMESTAMP,
            sequence_num=1,
            customer_data=None,
        )
        result = import_customer_data([rec], repo)
        self.assertEqual(result.statistics.unknown_record_types, 1)
        self.assertEqual(result.statistics.customer_records, 0)


# ===========================================================================
# 4. Mixed record import
# ===========================================================================

class TestMixedImport(unittest.TestCase):
    """Import with multiple record types."""

    def test_all_types_dispatched(self) -> None:
        repo = InMemoryImportDataRepository()
        records = [
            ExportRecord(rec_type="C", timestamp=FIXED_TIMESTAMP,
                         sequence_num=1, customer_data=_make_customer()),
            ExportRecord(rec_type="A", timestamp=FIXED_TIMESTAMP,
                         sequence_num=2, account_data=_make_account()),
            ExportRecord(rec_type="X", timestamp=FIXED_TIMESTAMP,
                         sequence_num=3, xref_data=_make_xref()),
            ExportRecord(rec_type="T", timestamp=FIXED_TIMESTAMP,
                         sequence_num=4, transaction_data=_make_transaction()),
            ExportRecord(rec_type="D", timestamp=FIXED_TIMESTAMP,
                         sequence_num=5, card_data=_make_card()),
        ]
        result = import_customer_data(records, repo)
        self.assertEqual(result.statistics.total_records_read, 5)
        self.assertEqual(result.statistics.customer_records, 1)
        self.assertEqual(result.statistics.account_records, 1)
        self.assertEqual(result.statistics.xref_records, 1)
        self.assertEqual(result.statistics.transaction_records, 1)
        self.assertEqual(result.statistics.card_records, 1)
        self.assertEqual(result.statistics.error_records, 0)

    def test_mixed_with_errors(self) -> None:
        repo = InMemoryImportDataRepository()
        records = [
            ExportRecord(rec_type="C", timestamp=FIXED_TIMESTAMP,
                         sequence_num=1, customer_data=_make_customer()),
            ExportRecord(rec_type="Z", timestamp=FIXED_TIMESTAMP,
                         sequence_num=2),
            ExportRecord(rec_type="A", timestamp=FIXED_TIMESTAMP,
                         sequence_num=3, account_data=_make_account()),
        ]
        result = import_customer_data(records, repo)
        self.assertEqual(result.statistics.total_records_read, 3)
        self.assertEqual(result.statistics.customer_records, 1)
        self.assertEqual(result.statistics.account_records, 1)
        self.assertEqual(result.statistics.error_records, 1)


# ===========================================================================
# 5. Statistics
# ===========================================================================

class TestImportStatistics(unittest.TestCase):
    """Verify statistics counters are accurate."""

    def test_multiple_of_same_type(self) -> None:
        repo = InMemoryImportDataRepository()
        records = [
            ExportRecord(rec_type="C", timestamp=FIXED_TIMESTAMP,
                         sequence_num=i, customer_data=_make_customer(f"{i:09d}"))
            for i in range(1, 6)
        ]
        result = import_customer_data(records, repo)
        self.assertEqual(result.statistics.total_records_read, 5)
        self.assertEqual(result.statistics.customer_records, 5)
        self.assertEqual(len(repo.customers), 5)

    def test_total_matches_sum(self) -> None:
        """total_records_read should equal sum of all type counts + errors."""
        repo = InMemoryImportDataRepository()
        records = [
            ExportRecord(rec_type="C", timestamp=FIXED_TIMESTAMP,
                         sequence_num=1, customer_data=_make_customer()),
            ExportRecord(rec_type="A", timestamp=FIXED_TIMESTAMP,
                         sequence_num=2, account_data=_make_account()),
            ExportRecord(rec_type="Z", timestamp=FIXED_TIMESTAMP,
                         sequence_num=3),
        ]
        result = import_customer_data(records, repo)
        s = result.statistics
        type_sum = (s.customer_records + s.account_records + s.xref_records +
                    s.transaction_records + s.card_records + s.error_records)
        self.assertEqual(s.total_records_read, type_sum)


# ===========================================================================
# 6. Round-trip test: Export → Import
# ===========================================================================

class TestRoundTrip(unittest.TestCase):
    """
    Verify that export → import reproduces the original data.

    This is the key integration test ensuring CBEXPORT and CBIMPORT
    are true complements of each other.
    """

    def _load_export_repo(self) -> InMemoryExportDataRepository:
        """Create a repo with diverse test data."""
        repo = InMemoryExportDataRepository()

        # Multiple customers
        repo.customers.append(_make_customer("000000001"))
        cust2 = _make_customer("000000002")
        cust2.first_name = "Jane"
        cust2.last_name = "Smith"
        cust2.fico_credit_score = 800
        repo.customers.append(cust2)

        # Multiple accounts
        repo.accounts.append(_make_account("00000000001"))
        acct2 = _make_account("00000000002")
        acct2.curr_bal = -250.00
        acct2.active_status = "N"
        repo.accounts.append(acct2)

        # Cross-references
        repo.xrefs.append(_make_xref("4000123456789010"))
        repo.xrefs.append(_make_xref("4000123456789020"))

        # Transactions
        repo.transactions.append(_make_transaction("0000000000000001"))
        tran2 = _make_transaction("0000000000000002")
        tran2.tran_amt = -50.25
        tran2.tran_desc = "Refund"
        repo.transactions.append(tran2)

        # Cards
        repo.cards.append(_make_card("4000123456789010"))
        card2 = _make_card("4000123456789020")
        card2.card_embossed_name = "JANE SMITH"
        card2.card_active_status = "N"
        repo.cards.append(card2)

        return repo

    def test_round_trip_customer_count(self) -> None:
        """Number of customers after round-trip matches original."""
        export_repo = self._load_export_repo()
        original_count = len(export_repo.customers)

        export_records, _ = export_customer_data(
            export_repo, timestamp=FIXED_TIMESTAMP
        )

        import_repo = InMemoryImportDataRepository()
        result = import_customer_data(export_records, import_repo)

        self.assertEqual(len(import_repo.customers), original_count)
        self.assertEqual(result.statistics.customer_records, original_count)

    def test_round_trip_account_count(self) -> None:
        export_repo = self._load_export_repo()
        original_count = len(export_repo.accounts)

        export_records, _ = export_customer_data(
            export_repo, timestamp=FIXED_TIMESTAMP
        )

        import_repo = InMemoryImportDataRepository()
        import_customer_data(export_records, import_repo)

        self.assertEqual(len(import_repo.accounts), original_count)

    def test_round_trip_all_counts(self) -> None:
        """All record type counts match between export and import."""
        export_repo = self._load_export_repo()

        export_records, export_stats = export_customer_data(
            export_repo, timestamp=FIXED_TIMESTAMP
        )

        import_repo = InMemoryImportDataRepository()
        result = import_customer_data(export_records, import_repo)

        self.assertEqual(
            result.statistics.customer_records, export_stats.customer_records
        )
        self.assertEqual(
            result.statistics.account_records, export_stats.account_records
        )
        self.assertEqual(
            result.statistics.xref_records, export_stats.xref_records
        )
        self.assertEqual(
            result.statistics.transaction_records,
            export_stats.transaction_records,
        )
        self.assertEqual(
            result.statistics.card_records, export_stats.card_records
        )
        self.assertEqual(result.statistics.error_records, 0)

    def test_round_trip_customer_data_preserved(self) -> None:
        """Customer field values are identical after round-trip."""
        export_repo = self._load_export_repo()
        originals = export_repo.customers

        export_records, _ = export_customer_data(
            export_repo, timestamp=FIXED_TIMESTAMP
        )

        import_repo = InMemoryImportDataRepository()
        import_customer_data(export_records, import_repo)

        for orig, imported in zip(originals, import_repo.customers):
            self.assertEqual(imported.cust_id, orig.cust_id)
            self.assertEqual(imported.first_name, orig.first_name)
            self.assertEqual(imported.last_name, orig.last_name)
            self.assertEqual(imported.ssn, orig.ssn)
            self.assertEqual(imported.addr_zip, orig.addr_zip)
            self.assertEqual(
                imported.fico_credit_score, orig.fico_credit_score
            )

    def test_round_trip_account_data_preserved(self) -> None:
        """Account field values are identical after round-trip."""
        export_repo = self._load_export_repo()
        originals = export_repo.accounts

        export_records, _ = export_customer_data(
            export_repo, timestamp=FIXED_TIMESTAMP
        )

        import_repo = InMemoryImportDataRepository()
        import_customer_data(export_records, import_repo)

        for orig, imported in zip(originals, import_repo.accounts):
            self.assertEqual(imported.acct_id, orig.acct_id)
            self.assertEqual(imported.active_status, orig.active_status)
            self.assertAlmostEqual(imported.curr_bal, orig.curr_bal)
            self.assertAlmostEqual(
                imported.credit_limit, orig.credit_limit
            )

    def test_round_trip_transaction_data_preserved(self) -> None:
        """Transaction field values are identical after round-trip."""
        export_repo = self._load_export_repo()
        originals = export_repo.transactions

        export_records, _ = export_customer_data(
            export_repo, timestamp=FIXED_TIMESTAMP
        )

        import_repo = InMemoryImportDataRepository()
        import_customer_data(export_records, import_repo)

        for orig, imported in zip(originals, import_repo.transactions):
            self.assertEqual(imported.tran_id, orig.tran_id)
            self.assertAlmostEqual(imported.tran_amt, orig.tran_amt)
            self.assertEqual(imported.tran_desc, orig.tran_desc)
            self.assertEqual(imported.tran_card_num, orig.tran_card_num)

    def test_round_trip_card_data_preserved(self) -> None:
        """Card field values are identical after round-trip."""
        export_repo = self._load_export_repo()
        originals = export_repo.cards

        export_records, _ = export_customer_data(
            export_repo, timestamp=FIXED_TIMESTAMP
        )

        import_repo = InMemoryImportDataRepository()
        import_customer_data(export_records, import_repo)

        for orig, imported in zip(originals, import_repo.cards):
            self.assertEqual(imported.card_num, orig.card_num)
            self.assertEqual(imported.card_acct_id, orig.card_acct_id)
            self.assertEqual(imported.card_cvv_cd, orig.card_cvv_cd)
            self.assertEqual(
                imported.card_embossed_name, orig.card_embossed_name
            )
            self.assertEqual(
                imported.card_active_status, orig.card_active_status
            )

    def test_round_trip_xref_data_preserved(self) -> None:
        """Cross-reference field values are identical after round-trip."""
        export_repo = self._load_export_repo()
        originals = export_repo.xrefs

        export_records, _ = export_customer_data(
            export_repo, timestamp=FIXED_TIMESTAMP
        )

        import_repo = InMemoryImportDataRepository()
        import_customer_data(export_records, import_repo)

        for orig, imported in zip(originals, import_repo.xrefs):
            self.assertEqual(imported.card_num, orig.card_num)
            self.assertEqual(imported.cust_id, orig.cust_id)
            self.assertEqual(imported.acct_id, orig.acct_id)

    def test_round_trip_no_errors(self) -> None:
        """Round-trip should produce zero errors."""
        export_repo = self._load_export_repo()

        export_records, _ = export_customer_data(
            export_repo, timestamp=FIXED_TIMESTAMP
        )

        import_repo = InMemoryImportDataRepository()
        result = import_customer_data(export_records, import_repo)

        self.assertEqual(result.statistics.error_records, 0)
        self.assertEqual(len(result.errors), 0)


if __name__ == "__main__":
    unittest.main()
