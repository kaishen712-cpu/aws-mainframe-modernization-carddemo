"""
Unit tests for CBCUS01C — Print Customer Data.

Tests cover:
- Empty repository (no customers)
- Single customer record formatting
- Multiple customer records
- Name trimming
- Start/end banners
"""

from __future__ import annotations

import unittest

from cbcus01c import (
    CustomerRecord,
    InMemoryCustomerRepository,
    format_customer_record,
    print_customer_data,
    PROGRAM_NAME,
)


def _make_customer(**overrides: object) -> CustomerRecord:
    """Create a CustomerRecord with sensible defaults."""
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
        cust_dob_yyyy_mm_dd="1985-06-15",
        cust_eft_account_id="EFT001",
        cust_pri_card_holder_ind="Y",
        cust_fico_credit_score="750",
    )
    defaults.update(overrides)
    return CustomerRecord(**defaults)  # type: ignore[arg-type]


class TestFormatCustomerRecord(unittest.TestCase):
    """Tests for the format_customer_record function."""

    def test_basic_formatting(self) -> None:
        cust = _make_customer()
        line = format_customer_record(cust)
        self.assertIn("000000001", line)
        self.assertIn("JOHN", line)
        self.assertIn("PUBLIC", line)
        self.assertIn("123456789", line)
        self.assertIn("1985-06-15", line)
        self.assertIn("750", line)
        self.assertIn("123 MAIN ST", line)
        self.assertIn("NY", line)

    def test_name_trimmed(self) -> None:
        cust = _make_customer(
            cust_first_name="ALICE                    ",
            cust_last_name="WONDERLAND               ",
        )
        line = format_customer_record(cust)
        self.assertIn("ALICE", line)
        self.assertIn("WONDERLAND", line)

    def test_middle_name_empty(self) -> None:
        cust = _make_customer(cust_middle_name="")
        line = format_customer_record(cust)
        self.assertIn("JOHN", line)
        self.assertIn("PUBLIC", line)


class TestPrintCustomerData(unittest.TestCase):
    """Tests for the print_customer_data main function."""

    def test_empty_repo(self) -> None:
        repo = InMemoryCustomerRepository()
        lines = print_customer_data(repo)
        self.assertEqual(len(lines), 2)
        self.assertIn("START", lines[0])
        self.assertIn("END", lines[1])

    def test_single_customer(self) -> None:
        repo = InMemoryCustomerRepository()
        repo.add_customer(_make_customer())
        lines = print_customer_data(repo)
        self.assertEqual(len(lines), 3)
        self.assertIn("000000001", lines[1])

    def test_multiple_customers(self) -> None:
        repo = InMemoryCustomerRepository()
        repo.add_customer(_make_customer(cust_id="000000001"))
        repo.add_customer(_make_customer(cust_id="000000002"))
        repo.add_customer(_make_customer(cust_id="000000003"))
        lines = print_customer_data(repo)
        self.assertEqual(len(lines), 5)  # start + 3 + end

    def test_banners_contain_program_name(self) -> None:
        repo = InMemoryCustomerRepository()
        lines = print_customer_data(repo)
        self.assertIn(PROGRAM_NAME, lines[0])
        self.assertIn(PROGRAM_NAME, lines[-1])


if __name__ == "__main__":
    unittest.main()
