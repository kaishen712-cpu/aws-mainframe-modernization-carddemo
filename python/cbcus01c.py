"""
CBCUS01C - Print Customer Data (Python Translation)

Translated from the COBOL program CBCUS01C.CBL in the AWS CardDemo
mainframe modernization project. This module reads customer records and
produces formatted output lines for each customer.

Original: Batch COBOL program reading a VSAM KSDS customer file
sequentially and printing each record via DISPLAY.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROGRAM_NAME = "CBCUS01C"


# ---------------------------------------------------------------------------
# Data structures (from copybook CVCUS01Y — customer entity, RECLN 500)
# ---------------------------------------------------------------------------

@dataclass
class CustomerRecord:
    """Customer record layout (CVCUS01Y - 500 bytes)."""
    cust_id: str = ""                   # PIC 9(09)
    cust_first_name: str = ""           # PIC X(25)
    cust_middle_name: str = ""          # PIC X(25)
    cust_last_name: str = ""            # PIC X(25)
    cust_addr_line_1: str = ""          # PIC X(50)
    cust_addr_line_2: str = ""          # PIC X(50)
    cust_addr_line_3: str = ""          # PIC X(50)
    cust_addr_state_cd: str = ""        # PIC X(02)
    cust_addr_country_cd: str = ""      # PIC X(03)
    cust_addr_zip: str = ""             # PIC X(10)
    cust_phone_num_1: str = ""          # PIC X(15)
    cust_phone_num_2: str = ""          # PIC X(15)
    cust_ssn: str = ""                  # PIC 9(09)
    cust_govt_issued_id: str = ""       # PIC X(20)
    cust_dob_yyyy_mm_dd: str = ""       # PIC X(10)
    cust_eft_account_id: str = ""       # PIC X(10)
    cust_pri_card_holder_ind: str = ""  # PIC X(01)
    cust_fico_credit_score: str = ""    # PIC 9(03)


# ---------------------------------------------------------------------------
# Repository interface
# ---------------------------------------------------------------------------

class CustomerRepository:
    """
    Abstract interface for customer data access.

    In the original COBOL program this is a sequential read of a VSAM
    KSDS file. Concrete implementations can use any data source.
    """

    def get_all_customers(self) -> List[CustomerRecord]:
        """Return all customer records in sequential order."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# In-memory repository for testing
# ---------------------------------------------------------------------------

class InMemoryCustomerRepository(CustomerRepository):
    """Simple in-memory implementation backed by a list."""

    def __init__(self) -> None:
        self.customers: List[CustomerRecord] = []

    def add_customer(self, record: CustomerRecord) -> None:
        """Add a customer record."""
        self.customers.append(record)

    def get_all_customers(self) -> List[CustomerRecord]:
        return list(self.customers)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def format_customer_record(record: CustomerRecord) -> str:
    """
    Format a single customer record as a display line.

    Mirrors the COBOL DISPLAY CUSTOMER-RECORD statement which prints
    the entire record structure.
    """
    return (
        f"Cust ID: {record.cust_id}  "
        f"Name: {record.cust_first_name.strip()} "
        f"{record.cust_middle_name.strip()} "
        f"{record.cust_last_name.strip()}  "
        f"SSN: {record.cust_ssn}  "
        f"DOB: {record.cust_dob_yyyy_mm_dd}  "
        f"FICO: {record.cust_fico_credit_score}  "
        f"Addr: {record.cust_addr_line_1.strip()}, "
        f"{record.cust_addr_state_cd} {record.cust_addr_zip.strip()}"
    )


def print_customer_data(repo: CustomerRepository) -> List[str]:
    """
    Read all customer records and produce formatted output lines.

    This is the main entry point corresponding to the COBOL program's
    PROCEDURE DIVISION. Returns a list of formatted strings (one per line)
    rather than writing to stdout.

    Args:
        repo: A CustomerRepository providing customer records.

    Returns:
        A list of formatted output lines including start/end banners.
    """
    lines: List[str] = []
    lines.append(f"START OF EXECUTION OF PROGRAM {PROGRAM_NAME}")

    customers = repo.get_all_customers()
    for customer in customers:
        lines.append(format_customer_record(customer))

    lines.append(f"END OF EXECUTION OF PROGRAM {PROGRAM_NAME}")
    return lines
