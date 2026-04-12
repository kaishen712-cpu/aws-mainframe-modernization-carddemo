"""
Unit tests for Phase 7 — Export/Import & Utilities.

Tests cover:
- Export produces valid file format (NDJSON with correct record types)
- Import reads and validates records
- Round-trip: export then import
- Invalid record handling (malformed JSON, unknown types, missing fields)
- Timer utility (wait_centiseconds, wait_seconds)

All test data is synthetic — never uses real customer data.
Never logs account numbers or card numbers in plain text.

Translated from test requirements in docs/execution_plan.md Phase 7.
"""

from __future__ import annotations

import json
import os
import tempfile
from decimal import Decimal
from unittest.mock import patch

import pytest

from python.batch.management.commands.export_data import (
    ExportStatistics,
    build_account_export,
    build_card_export,
    build_customer_export,
    build_transaction_export,
    build_xref_export,
    generate_timestamp,
    run_export,
    write_record,
    _serialize_record,
    _next_sequence,
)
from python.batch.management.commands.import_data import (
    ErrorRecord,
    ImportStatistics,
    parse_account_record,
    parse_card_record,
    parse_customer_record,
    parse_transaction_record,
    parse_xref_record,
    process_record_by_type,
    run_import,
    validate_record_format,
    _safe_int,
    _safe_decimal_str,
)
from python.models.export_record import (
    EXPORT_REC_TYPE_ACCOUNT,
    EXPORT_REC_TYPE_CARD,
    EXPORT_REC_TYPE_CARD_XREF,
    EXPORT_REC_TYPE_CUSTOMER,
    EXPORT_REC_TYPE_TRANSACTION,
    ExportAccountData,
    ExportCardData,
    ExportCardXrefData,
    ExportCustomerData,
    ExportRecord,
    ExportTransactionData,
)
from python.models.records import (
    AccountRecord,
    CardRecord,
    CardXrefRecord,
    CustomerRecord,
    TransactionRecord,
)
from python.repositories.in_memory import (
    InMemoryAccountRepository,
    InMemoryCardRepository,
    InMemoryCardXrefRepository,
    InMemoryCustomerRepository,
    InMemoryTransactionRepository,
)
from python.utils.timer import wait_centiseconds, wait_seconds


# ---------------------------------------------------------------------------
# Synthetic test data factories
# ---------------------------------------------------------------------------


def _make_customer(cust_id: str = "000000001") -> CustomerRecord:
    """Create a synthetic customer record for testing."""
    return CustomerRecord(
        cust_id=cust_id,
        cust_first_name="Test",
        cust_middle_name="M",
        cust_last_name="User",
        cust_addr_line_1="123 Test St",
        cust_addr_line_2="Apt 4",
        cust_addr_line_3="",
        cust_addr_state_cd="CA",
        cust_addr_country_cd="USA",
        cust_addr_zip="90210",
        cust_phone_num_1="5551234567",
        cust_phone_num_2="5559876543",
        cust_ssn="000000000",
        cust_govt_issued_id="TESTID00000000000001",
        cust_dob_yyyy_mm_dd="1990-01-15",
        cust_eft_account_id="EFT0000001",
        cust_pri_card_holder_ind="Y",
        cust_fico_credit_score="750",
    )


def _make_account(acct_id: str = "00000000001") -> AccountRecord:
    """Create a synthetic account record for testing."""
    return AccountRecord(
        acct_id=acct_id,
        acct_active_status="Y",
        acct_curr_bal=1500.50,
        acct_credit_limit=5000.00,
        acct_cash_credit_limit=1000.00,
        acct_open_date="2020-01-01",
        acct_expiration_date="2025-12-31",
        acct_reissue_date="2023-06-15",
        acct_curr_cyc_credit=200.00,
        acct_curr_cyc_debit=50.00,
        acct_addr_zip="90210",
        acct_group_id="GRP001",
    )


def _make_xref(
    card_num: str = "0000000000000001",
    cust_id: str = "000000001",
    acct_id: str = "00000000001",
) -> CardXrefRecord:
    """Create a synthetic cross-reference record for testing."""
    return CardXrefRecord(
        xref_card_num=card_num,
        xref_cust_id=cust_id,
        xref_acct_id=acct_id,
    )


def _make_transaction(tran_id: str = "0000000000000001") -> TransactionRecord:
    """Create a synthetic transaction record for testing."""
    return TransactionRecord(
        tran_id=tran_id,
        tran_type_cd="SA",
        tran_cat_cd="5001",
        tran_source="ONLINE",
        tran_desc="Test purchase",
        tran_amt=99.99,
        tran_merchant_id="123456789",
        tran_merchant_name="Test Merchant",
        tran_merchant_city="Test City",
        tran_merchant_zip="90210",
        tran_card_num="0000000000000001",
        tran_orig_ts="2024-01-15 10:30:00.000000",
        tran_proc_ts="2024-01-15 10:30:01.000000",
    )


def _make_card(card_num: str = "0000000000000001") -> CardRecord:
    """Create a synthetic card record for testing."""
    return CardRecord(
        card_num=card_num,
        card_acct_id="00000000001",
        card_cvv_cd="123",
        card_embossed_name="TEST USER",
        card_expiration_date="2025-12-31",
        card_active_status="Y",
    )


# ---------------------------------------------------------------------------
# Timer utility tests
# ---------------------------------------------------------------------------


class TestTimerUtility:
    """Tests for utils/timer.py — translated from COBSWAIT.cbl."""

    @patch("python.utils.timer.time.sleep")
    def test_wait_centiseconds_converts_correctly(self, mock_sleep: patch) -> None:
        """100 centiseconds = 1.0 second."""
        wait_centiseconds(100)
        mock_sleep.assert_called_once_with(1.0)

    @patch("python.utils.timer.time.sleep")
    def test_wait_centiseconds_zero(self, mock_sleep: patch) -> None:
        """0 centiseconds = 0.0 seconds (no wait)."""
        wait_centiseconds(0)
        mock_sleep.assert_called_once_with(0.0)

    @patch("python.utils.timer.time.sleep")
    def test_wait_centiseconds_small_value(self, mock_sleep: patch) -> None:
        """1 centisecond = 0.01 seconds."""
        wait_centiseconds(1)
        mock_sleep.assert_called_once_with(0.01)

    def test_wait_centiseconds_negative_raises(self) -> None:
        """Negative centiseconds raises ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            wait_centiseconds(-1)

    @patch("python.utils.timer.time.sleep")
    def test_wait_seconds_converts_correctly(self, mock_sleep: patch) -> None:
        """wait_seconds(2.5) converts to 250 centiseconds."""
        wait_seconds(2.5)
        mock_sleep.assert_called_once_with(2.5)

    def test_wait_seconds_negative_raises(self) -> None:
        """Negative seconds raises ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            wait_seconds(-0.5)

    @patch("python.utils.timer.time.sleep")
    def test_wait_seconds_zero(self, mock_sleep: patch) -> None:
        """wait_seconds(0) = no-op sleep."""
        wait_seconds(0)
        mock_sleep.assert_called_once_with(0.0)


# ---------------------------------------------------------------------------
# Export tests
# ---------------------------------------------------------------------------


class TestGenerateTimestamp:
    """Tests for the timestamp generation function."""

    def test_timestamp_length(self) -> None:
        """Timestamp must be exactly 26 characters (COBOL format)."""
        ts = generate_timestamp()
        assert len(ts) == 26

    def test_timestamp_format(self) -> None:
        """Timestamp matches YYYY-MM-DD HH:MM:SS.ffffff pattern."""
        ts = generate_timestamp()
        assert ts[4] == "-"
        assert ts[7] == "-"
        assert ts[10] == " "
        assert ts[13] == ":"
        assert ts[16] == ":"
        assert ts[19] == "."


class TestSequenceCounter:
    """Tests for the sequence counter helper."""

    def test_increments_from_zero(self) -> None:
        counter = [0]
        assert _next_sequence(counter) == 1
        assert _next_sequence(counter) == 2
        assert _next_sequence(counter) == 3

    def test_monotonically_increasing(self) -> None:
        counter = [100]
        values = [_next_sequence(counter) for _ in range(5)]
        assert values == [101, 102, 103, 104, 105]


class TestExportStatistics:
    """Tests for the ExportStatistics helper."""

    def test_initial_values(self) -> None:
        stats = ExportStatistics()
        assert stats.customer_count == 0
        assert stats.total_count == 0

    def test_log_summary_no_error(self) -> None:
        """log_summary runs without exception."""
        stats = ExportStatistics()
        stats.customer_count = 5
        stats.total_count = 5
        stats.log_summary()


class TestBuildExportRecords:
    """Tests for building export records from source records."""

    def test_build_customer_export(self) -> None:
        customer = _make_customer()
        record = build_customer_export(customer, "2024-01-15 10:30:00.00", 1)
        assert record.export_rec_type == EXPORT_REC_TYPE_CUSTOMER
        assert record.export_sequence_num == 1
        assert isinstance(record.record_data, ExportCustomerData)
        assert record.record_data.exp_cust_first_name == "Test"
        assert record.record_data.exp_cust_last_name == "User"
        assert record.record_data.exp_cust_fico_credit_score == 750

    def test_build_account_export(self) -> None:
        account = _make_account()
        record = build_account_export(account, "2024-01-15 10:30:00.00", 2)
        assert record.export_rec_type == EXPORT_REC_TYPE_ACCOUNT
        assert isinstance(record.record_data, ExportAccountData)
        assert record.record_data.exp_acct_id == "00000000001"
        assert record.record_data.exp_acct_curr_bal == 1500.50

    def test_build_xref_export(self) -> None:
        xref = _make_xref()
        record = build_xref_export(xref, "2024-01-15 10:30:00.00", 3)
        assert record.export_rec_type == EXPORT_REC_TYPE_CARD_XREF
        assert isinstance(record.record_data, ExportCardXrefData)
        assert record.record_data.exp_xref_cust_id == "000000001"

    def test_build_transaction_export(self) -> None:
        tran = _make_transaction()
        record = build_transaction_export(tran, "2024-01-15 10:30:00.00", 4)
        assert record.export_rec_type == EXPORT_REC_TYPE_TRANSACTION
        assert isinstance(record.record_data, ExportTransactionData)
        assert record.record_data.exp_tran_amt == 99.99

    def test_build_card_export(self) -> None:
        card = _make_card()
        record = build_card_export(card, "2024-01-15 10:30:00.00", 5)
        assert record.export_rec_type == EXPORT_REC_TYPE_CARD
        assert isinstance(record.record_data, ExportCardData)
        assert record.record_data.exp_card_embossed_name == "TEST USER"

    def test_build_customer_export_empty_id(self) -> None:
        """Empty cust_id should default to 0."""
        customer = _make_customer()
        customer.cust_id = ""
        record = build_customer_export(customer, "2024-01-15 10:30:00.00", 1)
        assert record.record_data.exp_cust_id == 0

    def test_build_customer_export_empty_fico(self) -> None:
        """Empty FICO score should default to 0."""
        customer = _make_customer()
        customer.cust_fico_credit_score = ""
        record = build_customer_export(customer, "2024-01-15 10:30:00.00", 1)
        assert record.record_data.exp_cust_fico_credit_score == 0


class TestSerializeRecord:
    """Tests for record serialization to NDJSON format."""

    def test_serialize_customer_produces_valid_json(self) -> None:
        record = build_customer_export(_make_customer(), "2024-01-15 10:30:00.00", 1)
        line = _serialize_record(record)
        data = json.loads(line)
        assert data["record_type"] == "C"
        assert "customer" in data
        assert data["customer"]["first_name"] == "Test"

    def test_serialize_account_contains_decimal_strings(self) -> None:
        """Monetary fields are serialized as Decimal strings."""
        record = build_account_export(_make_account(), "2024-01-15 10:30:00.00", 1)
        line = _serialize_record(record)
        data = json.loads(line)
        assert "account" in data
        # Verify monetary values are string representations
        bal = Decimal(data["account"]["curr_bal"])
        assert bal == Decimal("1500.5")

    def test_serialize_xref_produces_valid_json(self) -> None:
        record = build_xref_export(_make_xref(), "2024-01-15 10:30:00.00", 1)
        line = _serialize_record(record)
        data = json.loads(line)
        assert data["record_type"] == "X"
        assert "xref" in data

    def test_serialize_transaction_produces_valid_json(self) -> None:
        record = build_transaction_export(_make_transaction(), "2024-01-15 10:30:00.00", 1)
        line = _serialize_record(record)
        data = json.loads(line)
        assert data["record_type"] == "T"
        assert "transaction" in data

    def test_serialize_card_produces_valid_json(self) -> None:
        record = build_card_export(_make_card(), "2024-01-15 10:30:00.00", 1)
        line = _serialize_record(record)
        data = json.loads(line)
        assert data["record_type"] == "D"
        assert "card" in data

    def test_serialize_record_none_data(self) -> None:
        """Record with None data serializes header only."""
        record = ExportRecord(
            export_rec_type="?",
            export_timestamp="2024-01-15 10:30:00.00",
            export_sequence_num=1,
        )
        line = _serialize_record(record)
        data = json.loads(line)
        assert data["record_type"] == "?"
        assert "customer" not in data


class TestWriteRecord:
    """Tests for writing export records to file."""

    def test_write_record_to_file(self) -> None:
        record = build_customer_export(_make_customer(), "2024-01-15 10:30:00.00", 1)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".dat", delete=False) as fh:
            write_record(fh, record)
            path = fh.name

        try:
            with open(path, encoding="utf-8") as fh:
                line = fh.readline().strip()
            data = json.loads(line)
            assert data["record_type"] == "C"
        finally:
            os.unlink(path)


class TestRunExport:
    """Tests for the full export pipeline."""

    def _setup_repos(self):
        """Set up in-memory repositories with synthetic data."""
        customer_repo = InMemoryCustomerRepository()
        account_repo = InMemoryAccountRepository()
        xref_repo = InMemoryCardXrefRepository()
        transaction_repo = InMemoryTransactionRepository()
        card_repo = InMemoryCardRepository()

        customer_repo.seed(_make_customer("000000001"))
        customer_repo.seed(_make_customer("000000002"))
        account_repo.seed(_make_account("00000000001"))
        xref_repo.seed(_make_xref())
        transaction_repo.seed(_make_transaction("0000000000000001"))
        card_repo.seed(_make_card("0000000000000001"))

        return (
            customer_repo,
            account_repo,
            xref_repo,
            transaction_repo,
            card_repo,
        )

    def test_export_all_record_types(self) -> None:
        """Full export writes all 5 record types."""
        repos = self._setup_repos()
        with tempfile.NamedTemporaryFile(suffix=".dat", delete=False) as tmp:
            path = tmp.name

        try:
            stats = run_export(path, None, *repos)
            assert stats.customer_count == 2
            assert stats.account_count == 1
            assert stats.xref_count == 1
            assert stats.transaction_count == 1
            assert stats.card_count == 1
            assert stats.total_count == 6

            with open(path, encoding="utf-8") as fh:
                lines = fh.readlines()
            assert len(lines) == 6

            types_found = set()
            for line in lines:
                data = json.loads(line)
                types_found.add(data["record_type"])
            assert types_found == {"C", "A", "X", "T", "D"}
        finally:
            os.unlink(path)

    def test_export_selective_types(self) -> None:
        """Export only customer and account records."""
        repos = self._setup_repos()
        with tempfile.NamedTemporaryFile(suffix=".dat", delete=False) as tmp:
            path = tmp.name

        try:
            stats = run_export(path, {"customer", "account"}, *repos)
            assert stats.customer_count == 2
            assert stats.account_count == 1
            assert stats.xref_count == 0
            assert stats.transaction_count == 0
            assert stats.card_count == 0
            assert stats.total_count == 3
        finally:
            os.unlink(path)

    def test_export_empty_repos(self) -> None:
        """Export with empty repositories produces empty file."""
        repos = (
            InMemoryCustomerRepository(),
            InMemoryAccountRepository(),
            InMemoryCardXrefRepository(),
            InMemoryTransactionRepository(),
            InMemoryCardRepository(),
        )
        with tempfile.NamedTemporaryFile(suffix=".dat", delete=False) as tmp:
            path = tmp.name

        try:
            stats = run_export(path, None, *repos)
            assert stats.total_count == 0

            with open(path, encoding="utf-8") as fh:
                content = fh.read()
            assert content == ""
        finally:
            os.unlink(path)

    def test_export_sequence_numbers_are_monotonic(self) -> None:
        """Sequence numbers increase monotonically across record types."""
        repos = self._setup_repos()
        with tempfile.NamedTemporaryFile(suffix=".dat", delete=False) as tmp:
            path = tmp.name

        try:
            run_export(path, None, *repos)

            with open(path, encoding="utf-8") as fh:
                lines = fh.readlines()

            seq_nums = []
            for line in lines:
                data = json.loads(line)
                seq_nums.append(data["sequence_num"])

            assert seq_nums == sorted(seq_nums)
            assert len(set(seq_nums)) == len(seq_nums)
        finally:
            os.unlink(path)

    def test_export_branch_and_region_defaults(self) -> None:
        """All records have default branch_id and region_code."""
        repos = self._setup_repos()
        with tempfile.NamedTemporaryFile(suffix=".dat", delete=False) as tmp:
            path = tmp.name

        try:
            run_export(path, None, *repos)

            with open(path, encoding="utf-8") as fh:
                lines = fh.readlines()

            for line in lines:
                data = json.loads(line)
                assert data["branch_id"] == "0001"
                assert data["region_code"] == "NORTH"
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Import tests
# ---------------------------------------------------------------------------


class TestValidateRecordFormat:
    """Tests for record format validation."""

    def test_valid_customer_record(self) -> None:
        data = {
            "record_type": "C",
            "timestamp": "2024-01-15 10:30:00.00",
            "sequence_num": 1,
        }
        assert validate_record_format(data) is None

    def test_missing_record_type(self) -> None:
        data = {
            "timestamp": "2024-01-15 10:30:00.00",
            "sequence_num": 1,
        }
        error = validate_record_format(data)
        assert error is not None
        assert "record_type" in error

    def test_missing_timestamp(self) -> None:
        data = {"record_type": "C", "sequence_num": 1}
        error = validate_record_format(data)
        assert error is not None
        assert "timestamp" in error

    def test_missing_sequence_num(self) -> None:
        data = {
            "record_type": "C",
            "timestamp": "2024-01-15 10:30:00.00",
        }
        error = validate_record_format(data)
        assert error is not None
        assert "sequence_num" in error

    def test_unknown_record_type_passes_header_validation(self) -> None:
        """Unknown types pass header validation; dispatcher handles them."""
        data = {
            "record_type": "Z",
            "timestamp": "2024-01-15 10:30:00.00",
            "sequence_num": 1,
        }
        error = validate_record_format(data)
        assert error is None

    def test_all_valid_types(self) -> None:
        for rec_type in ["C", "A", "X", "T", "D"]:
            data = {
                "record_type": rec_type,
                "timestamp": "2024-01-15 10:30:00.00",
                "sequence_num": 1,
            }
            assert validate_record_format(data) is None


class TestSafeConversions:
    """Tests for _safe_int and _safe_decimal_str helpers."""

    def test_safe_int_valid(self) -> None:
        assert _safe_int(42) == 42
        assert _safe_int("123") == 123

    def test_safe_int_invalid(self) -> None:
        assert _safe_int("abc") == 0
        assert _safe_int(None) == 0
        assert _safe_int("abc", default=99) == 99

    def test_safe_decimal_str_valid(self) -> None:
        result = _safe_decimal_str("1500.50")
        assert result == 1500.50

    def test_safe_decimal_str_invalid(self) -> None:
        result = _safe_decimal_str("not_a_number")
        assert result == 0.0


class TestParseRecords:
    """Tests for individual record parsers in import_data."""

    def test_parse_customer_record(self) -> None:
        data = {
            "cust_id": 1,
            "first_name": "Test",
            "middle_name": "M",
            "last_name": "User",
            "addr_lines": ["123 Test St", "Apt 4", ""],
            "addr_state_cd": "CA",
            "addr_country_cd": "USA",
            "addr_zip": "90210",
            "phone_nums": ["5551234567", "5559876543"],
            "ssn": "000000000",
            "govt_issued_id": "TESTID00000000000001",
            "dob": "1990-01-15",
            "eft_account_id": "EFT0000001",
            "pri_card_holder_ind": "Y",
            "fico_credit_score": 750,
        }
        record = parse_customer_record(data)
        assert record.cust_id == "000000001"
        assert record.cust_first_name == "Test"
        assert record.cust_addr_line_1 == "123 Test St"

    def test_parse_account_record(self) -> None:
        data = {
            "acct_id": "00000000001",
            "active_status": "Y",
            "curr_bal": "1500.50",
            "credit_limit": "5000.00",
            "cash_credit_limit": "1000.00",
            "open_date": "2020-01-01",
            "expiration_date": "2025-12-31",
            "reissue_date": "2023-06-15",
            "curr_cyc_credit": "200.00",
            "curr_cyc_debit": "50.00",
            "addr_zip": "90210",
            "group_id": "GRP001",
        }
        record = parse_account_record(data)
        assert record.acct_id == "00000000001"
        assert record.acct_curr_bal == 1500.50

    def test_parse_xref_record(self) -> None:
        data = {
            "card_num": "0000000000000001",
            "cust_id": "000000001",
            "acct_id": "00000000001",
        }
        record = parse_xref_record(data)
        assert record.xref_card_num == "0000000000000001"

    def test_parse_transaction_record(self) -> None:
        data = {
            "tran_id": "0000000000000001",
            "type_cd": "SA",
            "cat_cd": "5001",
            "source": "ONLINE",
            "desc": "Test purchase",
            "amt": "99.99",
            "merchant_id": 123456789,
            "merchant_name": "Test Merchant",
            "merchant_city": "Test City",
            "merchant_zip": "90210",
            "card_num": "0000000000000001",
            "orig_ts": "2024-01-15 10:30:00.000000",
            "proc_ts": "2024-01-15 10:30:01.000000",
        }
        record = parse_transaction_record(data)
        assert record.tran_id == "0000000000000001"
        assert record.tran_amt == 99.99

    def test_parse_card_record(self) -> None:
        data = {
            "card_num": "0000000000000001",
            "acct_id": "00000000001",
            "cvv_cd": 123,
            "embossed_name": "TEST USER",
            "expiration_date": "2025-12-31",
            "active_status": "Y",
        }
        record = parse_card_record(data)
        assert record.card_num == "0000000000000001"
        assert record.card_embossed_name == "TEST USER"

    def test_parse_customer_missing_fields_defaults(self) -> None:
        """Missing fields default to empty strings or defaults."""
        record = parse_customer_record({})
        assert record.cust_id == "000000000"
        assert record.cust_first_name == ""
        assert record.cust_addr_line_1 == ""

    def test_parse_customer_short_addr_lines(self) -> None:
        """Addr lines shorter than 3 elements handled gracefully."""
        data = {"addr_lines": ["Only one"]}
        record = parse_customer_record(data)
        assert record.cust_addr_line_1 == "Only one"
        assert record.cust_addr_line_2 == ""

    def test_parse_customer_short_phone_nums(self) -> None:
        """Phone nums shorter than 2 elements handled gracefully."""
        data = {"phone_nums": ["5551234567"]}
        record = parse_customer_record(data)
        assert record.cust_phone_num_1 == "5551234567"
        assert record.cust_phone_num_2 == ""


class TestProcessRecordByType:
    """Tests for the record type dispatcher."""

    def test_process_customer(self) -> None:
        data = {
            "record_type": "C",
            "timestamp": "2024-01-15 10:30:00.00",
            "sequence_num": 1,
            "customer": {"cust_id": 1, "first_name": "Test"},
        }
        errors: list[ErrorRecord] = []
        stats = ImportStatistics()
        record = process_record_by_type(data, errors, stats)
        assert isinstance(record, CustomerRecord)
        assert stats.customer_count == 1
        assert len(errors) == 0

    def test_process_account(self) -> None:
        data = {
            "record_type": "A",
            "timestamp": "2024-01-15 10:30:00.00",
            "sequence_num": 2,
            "account": {"acct_id": "00000000001", "curr_bal": "100.00"},
        }
        errors: list[ErrorRecord] = []
        stats = ImportStatistics()
        record = process_record_by_type(data, errors, stats)
        assert isinstance(record, AccountRecord)
        assert stats.account_count == 1

    def test_process_xref(self) -> None:
        data = {
            "record_type": "X",
            "timestamp": "2024-01-15 10:30:00.00",
            "sequence_num": 3,
            "xref": {"card_num": "0000000000000001"},
        }
        errors: list[ErrorRecord] = []
        stats = ImportStatistics()
        record = process_record_by_type(data, errors, stats)
        assert isinstance(record, CardXrefRecord)

    def test_process_transaction(self) -> None:
        data = {
            "record_type": "T",
            "timestamp": "2024-01-15 10:30:00.00",
            "sequence_num": 4,
            "transaction": {"tran_id": "0000000000000001"},
        }
        errors: list[ErrorRecord] = []
        stats = ImportStatistics()
        record = process_record_by_type(data, errors, stats)
        assert isinstance(record, TransactionRecord)

    def test_process_card(self) -> None:
        data = {
            "record_type": "D",
            "timestamp": "2024-01-15 10:30:00.00",
            "sequence_num": 5,
            "card": {"card_num": "0000000000000001"},
        }
        errors: list[ErrorRecord] = []
        stats = ImportStatistics()
        record = process_record_by_type(data, errors, stats)
        assert isinstance(record, CardRecord)

    def test_process_missing_customer_data_section(self) -> None:
        """Customer record without 'customer' key logs error."""
        data = {
            "record_type": "C",
            "timestamp": "2024-01-15 10:30:00.00",
            "sequence_num": 1,
        }
        errors: list[ErrorRecord] = []
        stats = ImportStatistics()
        record = process_record_by_type(data, errors, stats)
        assert record is None
        assert len(errors) == 1
        assert "missing data section" in errors[0].message

    def test_process_missing_account_data_section(self) -> None:
        data = {
            "record_type": "A",
            "timestamp": "2024-01-15 10:30:00.00",
            "sequence_num": 2,
        }
        errors: list[ErrorRecord] = []
        stats = ImportStatistics()
        record = process_record_by_type(data, errors, stats)
        assert record is None
        assert stats.error_count == 1

    def test_process_missing_xref_data_section(self) -> None:
        data = {
            "record_type": "X",
            "timestamp": "2024-01-15 10:30:00.00",
            "sequence_num": 3,
        }
        errors: list[ErrorRecord] = []
        stats = ImportStatistics()
        record = process_record_by_type(data, errors, stats)
        assert record is None
        assert stats.error_count == 1

    def test_process_missing_transaction_data_section(self) -> None:
        data = {
            "record_type": "T",
            "timestamp": "2024-01-15 10:30:00.00",
            "sequence_num": 4,
        }
        errors: list[ErrorRecord] = []
        stats = ImportStatistics()
        record = process_record_by_type(data, errors, stats)
        assert record is None
        assert stats.error_count == 1

    def test_process_missing_card_data_section(self) -> None:
        data = {
            "record_type": "D",
            "timestamp": "2024-01-15 10:30:00.00",
            "sequence_num": 5,
        }
        errors: list[ErrorRecord] = []
        stats = ImportStatistics()
        record = process_record_by_type(data, errors, stats)
        assert record is None
        assert stats.error_count == 1

    def test_process_invalid_format(self) -> None:
        """Record missing required header fields."""
        data = {"some_field": "value"}
        errors: list[ErrorRecord] = []
        stats = ImportStatistics()
        record = process_record_by_type(data, errors, stats)
        assert record is None
        assert len(errors) == 1


class TestImportStatistics:
    """Tests for ImportStatistics."""

    def test_initial_values(self) -> None:
        stats = ImportStatistics()
        assert stats.total_records_read == 0
        assert stats.error_count == 0

    def test_log_summary_no_error(self) -> None:
        stats = ImportStatistics()
        stats.customer_count = 10
        stats.log_summary()


class TestErrorRecord:
    """Tests for error record formatting."""

    def test_format(self) -> None:
        err = ErrorRecord(
            timestamp="2024-01-15 10:30:00.000000",
            record_type="Z",
            sequence=42,
            message="Unknown record type encountered",
        )
        formatted = err.format()
        assert "2024-01-15 10:30:00.000000" in formatted
        assert "|Z|" in formatted
        assert "0000042" in formatted
        assert "Unknown record type encountered" in formatted


class TestRunImport:
    """Tests for the full import pipeline."""

    def test_import_valid_file(self) -> None:
        """Import a file with one record of each type."""
        records = [
            {
                "record_type": "C",
                "timestamp": "2024-01-15 10:30:00.00",
                "sequence_num": 1,
                "branch_id": "0001",
                "region_code": "NORTH",
                "customer": {
                    "cust_id": 1,
                    "first_name": "Test",
                    "last_name": "User",
                },
            },
            {
                "record_type": "A",
                "timestamp": "2024-01-15 10:30:00.00",
                "sequence_num": 2,
                "branch_id": "0001",
                "region_code": "NORTH",
                "account": {
                    "acct_id": "00000000001",
                    "curr_bal": "1500.50",
                },
            },
            {
                "record_type": "X",
                "timestamp": "2024-01-15 10:30:00.00",
                "sequence_num": 3,
                "branch_id": "0001",
                "region_code": "NORTH",
                "xref": {
                    "card_num": "0000000000000001",
                    "cust_id": "000000001",
                    "acct_id": "00000000001",
                },
            },
            {
                "record_type": "T",
                "timestamp": "2024-01-15 10:30:00.00",
                "sequence_num": 4,
                "branch_id": "0001",
                "region_code": "NORTH",
                "transaction": {
                    "tran_id": "0000000000000001",
                    "amt": "99.99",
                },
            },
            {
                "record_type": "D",
                "timestamp": "2024-01-15 10:30:00.00",
                "sequence_num": 5,
                "branch_id": "0001",
                "region_code": "NORTH",
                "card": {
                    "card_num": "0000000000000001",
                    "embossed_name": "TEST USER",
                },
            },
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".dat", delete=False, encoding="utf-8"
        ) as fh:
            for rec in records:
                fh.write(json.dumps(rec) + "\n")
            path = fh.name

        try:
            result = run_import(path)
            assert result.stats.total_records_read == 5
            assert result.stats.customer_count == 1
            assert result.stats.account_count == 1
            assert result.stats.xref_count == 1
            assert result.stats.transaction_count == 1
            assert result.stats.card_count == 1
            assert result.stats.error_count == 0
            assert len(result.customers) == 1
            assert len(result.accounts) == 1
        finally:
            os.unlink(path)

    def test_import_invalid_json_lines(self) -> None:
        """Invalid JSON lines are logged as errors, valid ones processed."""
        lines = [
            '{"record_type": "C", "timestamp": "2024-01-15 10:30:00.00", '
            '"sequence_num": 1, "customer": {"cust_id": 1}}',
            "this is not json",
            '{"record_type": "A", "timestamp": "2024-01-15 10:30:00.00", '
            '"sequence_num": 2, "account": {"acct_id": "001"}}',
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".dat", delete=False, encoding="utf-8"
        ) as fh:
            for line in lines:
                fh.write(line + "\n")
            path = fh.name

        try:
            result = run_import(path)
            assert result.stats.total_records_read == 3
            assert result.stats.customer_count == 1
            assert result.stats.account_count == 1
            assert result.stats.error_count == 1
            assert len(result.errors) == 1
        finally:
            os.unlink(path)

    def test_import_unknown_record_type(self) -> None:
        """Unknown record types are logged and counted."""
        line = json.dumps(
            {
                "record_type": "Z",
                "timestamp": "2024-01-15 10:30:00.00",
                "sequence_num": 1,
            }
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".dat", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(line + "\n")
            path = fh.name

        try:
            result = run_import(path)
            assert result.stats.error_count == 1
            assert result.stats.unknown_type_count == 1
            assert len(result.errors) == 1
        finally:
            os.unlink(path)

    def test_import_empty_file(self) -> None:
        """Empty file produces zero records and zero errors."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".dat", delete=False, encoding="utf-8"
        ) as fh:
            path = fh.name

        try:
            result = run_import(path)
            assert result.stats.total_records_read == 0
            assert result.stats.error_count == 0
        finally:
            os.unlink(path)

    def test_import_blank_lines_skipped(self) -> None:
        """Blank lines in the input file are skipped."""
        lines = [
            "",
            '{"record_type": "C", "timestamp": "2024-01-15 10:30:00.00", '
            '"sequence_num": 1, "customer": {"cust_id": 1}}',
            "",
            "",
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".dat", delete=False, encoding="utf-8"
        ) as fh:
            for line in lines:
                fh.write(line + "\n")
            path = fh.name

        try:
            result = run_import(path)
            assert result.stats.total_records_read == 1
            assert result.stats.customer_count == 1
        finally:
            os.unlink(path)

    def test_import_file_not_found(self) -> None:
        """FileNotFoundError raised for missing input file."""
        with pytest.raises(FileNotFoundError):
            run_import("/nonexistent/path/to/file.dat")

    def test_import_with_error_report(self) -> None:
        """Error report file is written when errors occur."""
        line = "not valid json"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".dat", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(line + "\n")
            input_path = fh.name

        error_path = input_path + ".errors"

        try:
            result = run_import(input_path, error_path=error_path)
            assert result.stats.error_count == 1
            assert os.path.exists(error_path)

            with open(error_path, encoding="utf-8") as efh:
                error_content = efh.read()
            assert "Invalid JSON" in error_content
        finally:
            os.unlink(input_path)
            if os.path.exists(error_path):
                os.unlink(error_path)


# ---------------------------------------------------------------------------
# Round-trip tests (export → import)
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Test that data exported and then imported produces equivalent records."""

    def test_customer_round_trip(self) -> None:
        """Export a customer, import it, verify fields match."""
        customer_repo = InMemoryCustomerRepository()
        customer_repo.seed(_make_customer("000000001"))

        with tempfile.NamedTemporaryFile(suffix=".dat", delete=False) as tmp:
            path = tmp.name

        try:
            run_export(
                path,
                {"customer"},
                customer_repo,
                InMemoryAccountRepository(),
                InMemoryCardXrefRepository(),
                InMemoryTransactionRepository(),
                InMemoryCardRepository(),
            )

            result = run_import(path)
            assert len(result.customers) == 1
            imported = result.customers[0]
            assert imported.cust_first_name == "Test"
            assert imported.cust_last_name == "User"
            assert imported.cust_addr_state_cd == "CA"
        finally:
            os.unlink(path)

    def test_account_round_trip(self) -> None:
        """Export an account, import it, verify monetary fields."""
        account_repo = InMemoryAccountRepository()
        account_repo.seed(_make_account("00000000001"))

        with tempfile.NamedTemporaryFile(suffix=".dat", delete=False) as tmp:
            path = tmp.name

        try:
            run_export(
                path,
                {"account"},
                InMemoryCustomerRepository(),
                account_repo,
                InMemoryCardXrefRepository(),
                InMemoryTransactionRepository(),
                InMemoryCardRepository(),
            )

            result = run_import(path)
            assert len(result.accounts) == 1
            imported = result.accounts[0]
            assert imported.acct_id == "00000000001"
            assert imported.acct_curr_bal == 1500.50
        finally:
            os.unlink(path)

    def test_full_round_trip(self) -> None:
        """Export all record types, import, verify counts match."""
        customer_repo = InMemoryCustomerRepository()
        account_repo = InMemoryAccountRepository()
        xref_repo = InMemoryCardXrefRepository()
        transaction_repo = InMemoryTransactionRepository()
        card_repo = InMemoryCardRepository()

        customer_repo.seed(_make_customer("000000001"))
        account_repo.seed(_make_account("00000000001"))
        xref_repo.seed(_make_xref())
        transaction_repo.seed(_make_transaction("0000000000000001"))
        card_repo.seed(_make_card("0000000000000001"))

        with tempfile.NamedTemporaryFile(suffix=".dat", delete=False) as tmp:
            path = tmp.name

        try:
            export_stats = run_export(
                path,
                None,
                customer_repo,
                account_repo,
                xref_repo,
                transaction_repo,
                card_repo,
            )

            result = run_import(path)

            assert result.stats.customer_count == export_stats.customer_count
            assert result.stats.account_count == export_stats.account_count
            assert result.stats.xref_count == export_stats.xref_count
            assert result.stats.transaction_count == export_stats.transaction_count
            assert result.stats.card_count == export_stats.card_count
            assert result.stats.error_count == 0
        finally:
            os.unlink(path)

    def test_transaction_amount_preserved(self) -> None:
        """Transaction amounts survive round-trip without precision loss."""
        transaction_repo = InMemoryTransactionRepository()
        tran = _make_transaction()
        tran.tran_amt = 12345.67
        transaction_repo.seed(tran)

        with tempfile.NamedTemporaryFile(suffix=".dat", delete=False) as tmp:
            path = tmp.name

        try:
            run_export(
                path,
                {"transaction"},
                InMemoryCustomerRepository(),
                InMemoryAccountRepository(),
                InMemoryCardXrefRepository(),
                transaction_repo,
                InMemoryCardRepository(),
            )

            result = run_import(path)
            assert len(result.transactions) == 1
            assert result.transactions[0].tran_amt == 12345.67
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# CLI entry point tests
# ---------------------------------------------------------------------------


class TestExportCLI:
    """Tests for the export CLI main() function."""

    def test_export_cli_success(self) -> None:
        from python.batch.management.commands.export_data import main

        with tempfile.NamedTemporaryFile(suffix=".dat", delete=False) as tmp:
            path = tmp.name

        try:
            exit_code = main(["--output", path])
            assert exit_code == 0
        finally:
            os.unlink(path)

    def test_export_cli_with_types(self) -> None:
        from python.batch.management.commands.export_data import main

        with tempfile.NamedTemporaryFile(suffix=".dat", delete=False) as tmp:
            path = tmp.name

        try:
            exit_code = main(["--output", path, "--types", "customer"])
            assert exit_code == 0
        finally:
            os.unlink(path)


class TestImportCLI:
    """Tests for the import CLI main() function."""

    def test_import_cli_success(self) -> None:
        from python.batch.management.commands.import_data import main

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".dat", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(
                json.dumps(
                    {
                        "record_type": "C",
                        "timestamp": "2024-01-15 10:30:00.00",
                        "sequence_num": 1,
                        "customer": {"cust_id": 1},
                    }
                )
                + "\n"
            )
            path = fh.name

        try:
            exit_code = main(["--input", path])
            assert exit_code == 0
        finally:
            os.unlink(path)

    def test_import_cli_file_not_found(self) -> None:
        from python.batch.management.commands.import_data import main

        exit_code = main(["--input", "/nonexistent/file.dat"])
        assert exit_code == 1

    def test_import_cli_with_errors(self) -> None:
        from python.batch.management.commands.import_data import main

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".dat", delete=False, encoding="utf-8"
        ) as fh:
            fh.write("invalid json\n")
            path = fh.name

        error_path = path + ".errors"

        try:
            exit_code = main(["--input", path, "--errors", error_path])
            assert exit_code == 0  # Completes with warnings, not failure
        finally:
            os.unlink(path)
            if os.path.exists(error_path):
                os.unlink(error_path)
