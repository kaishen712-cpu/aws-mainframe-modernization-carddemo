"""
Unit tests for CBSTM03B — Statement Report Subroutine.

Tests cover:
- StatementFileHandler open/close lifecycle
- Sequential transaction reading (including EOF)
- Sequential xref reading (including EOF)
- Keyed customer lookup (found and not found)
- Keyed account lookup (found and not found)
- Reading before open returns error
- Multiple sequential reads
"""

from __future__ import annotations

import unittest

from cbstm03b import (
    AccountRecord,
    CustomerRecord,
    InMemoryAccountFileRepository,
    InMemoryCustomerFileRepository,
    InMemoryTrnxFileRepository,
    InMemoryXrefFileRepository,
    StatementFileHandler,
    TrnxRecord,
    XrefRecord,
    RC_EOF,
    RC_ERROR,
    RC_OK,
)


def _make_handler(
    trnx_records: list[TrnxRecord] | None = None,
    xref_records: list[XrefRecord] | None = None,
    cust_records: list[CustomerRecord] | None = None,
    acct_records: list[AccountRecord] | None = None,
) -> StatementFileHandler:
    """Create a StatementFileHandler with optional test data."""
    trnx_repo = InMemoryTrnxFileRepository()
    xref_repo = InMemoryXrefFileRepository()
    cust_repo = InMemoryCustomerFileRepository()
    acct_repo = InMemoryAccountFileRepository()

    for r in (trnx_records or []):
        trnx_repo.add_record(r)
    for r in (xref_records or []):
        xref_repo.add_record(r)
    for r in (cust_records or []):
        cust_repo.add_record(r)
    for r in (acct_records or []):
        acct_repo.add_record(r)

    return StatementFileHandler(trnx_repo, xref_repo, cust_repo, acct_repo)


def _make_trnx(**overrides: object) -> TrnxRecord:
    defaults = dict(
        trnx_card_num="4111111111111111",
        trnx_id="TRN0000000000001",
        trnx_type_cd="SA",
        trnx_cat_cd="0001",
        trnx_source="ONLINE",
        trnx_desc="Purchase",
        trnx_amt=100.00,
        trnx_merchant_id="000000001",
        trnx_merchant_name="Test",
        trnx_merchant_city="NYC",
        trnx_merchant_zip="10001",
        trnx_orig_ts="2024-01-15-10.30.00.000000",
        trnx_proc_ts="2024-01-15-12.00.00.000000",
    )
    defaults.update(overrides)
    return TrnxRecord(**defaults)  # type: ignore[arg-type]


def _make_xref(**overrides: object) -> XrefRecord:
    defaults = dict(
        xref_card_num="4111111111111111",
        xref_cust_id="000000001",
        xref_acct_id="00000000001",
    )
    defaults.update(overrides)
    return XrefRecord(**defaults)  # type: ignore[arg-type]


def _make_customer(**overrides: object) -> CustomerRecord:
    defaults = dict(
        cust_id="000000001",
        cust_first_name="JOHN",
        cust_middle_name="Q",
        cust_last_name="PUBLIC",
        cust_addr_line_1="123 MAIN ST",
        cust_addr_line_2="",
        cust_addr_line_3="",
        cust_addr_state_cd="NY",
        cust_addr_country_cd="US",
        cust_addr_zip="10001",
        cust_phone_num_1="2125551234",
        cust_phone_num_2="",
        cust_ssn="123456789",
        cust_govt_issued_id="DL12345",
        cust_dob_yyyymmdd="1985-06-15",
        cust_eft_account_id="EFT001",
        cust_pri_card_holder_ind="Y",
        cust_fico_credit_score="750",
    )
    defaults.update(overrides)
    return CustomerRecord(**defaults)  # type: ignore[arg-type]


def _make_account(**overrides: object) -> AccountRecord:
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


class TestStatementFileHandlerOpenClose(unittest.TestCase):
    """Tests for open/close lifecycle."""

    def test_open_and_close(self) -> None:
        handler = _make_handler()
        handler.open_all()
        handler.close_all()
        # Should not raise

    def test_read_trnx_before_open_returns_error(self) -> None:
        handler = _make_handler()
        result = handler.read_next_trnx()
        self.assertEqual(result.return_code, RC_ERROR)

    def test_read_xref_before_open_returns_error(self) -> None:
        handler = _make_handler()
        result = handler.read_next_xref()
        self.assertEqual(result.return_code, RC_ERROR)

    def test_read_after_close_returns_error(self) -> None:
        handler = _make_handler(trnx_records=[_make_trnx()])
        handler.open_all()
        handler.close_all()
        result = handler.read_next_trnx()
        self.assertEqual(result.return_code, RC_ERROR)


class TestReadNextTrnx(unittest.TestCase):
    """Tests for sequential transaction reading."""

    def test_read_single_record(self) -> None:
        handler = _make_handler(trnx_records=[_make_trnx()])
        handler.open_all()
        result = handler.read_next_trnx()
        self.assertEqual(result.return_code, RC_OK)
        trnx: TrnxRecord = result.data  # type: ignore[assignment]
        self.assertEqual(trnx.trnx_card_num, "4111111111111111")

    def test_read_eof_on_empty(self) -> None:
        handler = _make_handler()
        handler.open_all()
        result = handler.read_next_trnx()
        self.assertEqual(result.return_code, RC_EOF)

    def test_read_multiple_then_eof(self) -> None:
        records = [_make_trnx(trnx_id=f"TRN{i:016d}") for i in range(3)]
        handler = _make_handler(trnx_records=records)
        handler.open_all()
        for i in range(3):
            result = handler.read_next_trnx()
            self.assertEqual(result.return_code, RC_OK)
        result = handler.read_next_trnx()
        self.assertEqual(result.return_code, RC_EOF)


class TestReadNextXref(unittest.TestCase):
    """Tests for sequential xref reading."""

    def test_read_single_xref(self) -> None:
        handler = _make_handler(xref_records=[_make_xref()])
        handler.open_all()
        result = handler.read_next_xref()
        self.assertEqual(result.return_code, RC_OK)
        xref: XrefRecord = result.data  # type: ignore[assignment]
        self.assertEqual(xref.xref_card_num, "4111111111111111")

    def test_read_eof_on_empty(self) -> None:
        handler = _make_handler()
        handler.open_all()
        result = handler.read_next_xref()
        self.assertEqual(result.return_code, RC_EOF)

    def test_read_multiple_then_eof(self) -> None:
        records = [_make_xref(xref_card_num=f"{i:016d}") for i in range(5)]
        handler = _make_handler(xref_records=records)
        handler.open_all()
        for _ in range(5):
            result = handler.read_next_xref()
            self.assertEqual(result.return_code, RC_OK)
        result = handler.read_next_xref()
        self.assertEqual(result.return_code, RC_EOF)


class TestReadCustomerByKey(unittest.TestCase):
    """Tests for keyed customer lookup."""

    def test_found(self) -> None:
        handler = _make_handler(cust_records=[_make_customer()])
        handler.open_all()
        result = handler.read_customer_by_key("000000001")
        self.assertEqual(result.return_code, RC_OK)
        cust: CustomerRecord = result.data  # type: ignore[assignment]
        self.assertEqual(cust.cust_first_name, "JOHN")

    def test_not_found(self) -> None:
        handler = _make_handler()
        handler.open_all()
        result = handler.read_customer_by_key("999999999")
        self.assertEqual(result.return_code, RC_ERROR)

    def test_customer_lookup_no_open_needed(self) -> None:
        """Customer lookup works via keyed access even without open."""
        handler = _make_handler(cust_records=[_make_customer()])
        result = handler.read_customer_by_key("000000001")
        self.assertEqual(result.return_code, RC_OK)


class TestReadAccountByKey(unittest.TestCase):
    """Tests for keyed account lookup."""

    def test_found(self) -> None:
        handler = _make_handler(acct_records=[_make_account()])
        handler.open_all()
        result = handler.read_account_by_key("00000000001")
        self.assertEqual(result.return_code, RC_OK)
        acct: AccountRecord = result.data  # type: ignore[assignment]
        self.assertEqual(acct.acct_curr_bal, 5000.00)

    def test_not_found(self) -> None:
        handler = _make_handler()
        handler.open_all()
        result = handler.read_account_by_key("99999999999")
        self.assertEqual(result.return_code, RC_ERROR)


if __name__ == "__main__":
    unittest.main()
