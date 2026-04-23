# CardDemo — Python Migration

Python translation of the [AWS CardDemo](https://github.com/aws-samples/aws-mainframe-modernization-carddemo) COBOL mainframe application. The original system is a credit-card management application that runs under CICS on z/OS with VSAM files and DB2. This project re-implements the business logic, data models, and data-access layer in idiomatic Python.

## Directory Structure

```
python/
├── models/                 # Dataclass representations of VSAM record types
│   ├── records.py          # Core record types (Account, Card, Customer, Transaction, …)
│   ├── commarea.py         # CICS communication area (session state)
│   ├── export_record.py    # Multi-record export file layout (CVEXPORT)
│   └── report.py           # Report formatting structures (daily transaction report)
│
├── repositories/           # Data-access layer (repository pattern)
│   ├── base.py             # Abstract interfaces for each VSAM file
│   └── in_memory.py        # In-memory dict-backed implementations for testing
│
├── utils/                  # Shared utility functions
│   ├── date_validation.py  # COBOL-style CCYYMMDD date validation
│   ├── string_utils.py     # String padding, trimming, numeric parsing
│   └── lookup_codes.py     # US state codes, ZIP combos, phone area codes
│
├── common/                 # Application-wide definitions
│   ├── constants.py        # Screen titles, messages, date formatting
│   └── menu.py             # Main menu and admin menu option definitions
│
├── cotrn02c.py             # COTRN02C — Add Transaction program (business logic)
├── test_cotrn02c.py        # Unit tests for COTRN02C (68 tests)
│
└── tests/                  # Shared test infrastructure
    ├── conftest.py         # Pytest fixtures: pre-populated repos, record factories
    ├── test_integration.py # Cross-program integration tests
    ├── test_models.py      # Unit tests for data models
    ├── test_repositories.py# Unit tests for in-memory repositories
    ├── test_date_validation.py # Unit tests for date validation
    └── test_utils.py       # Unit tests for string/lookup utilities
```

## Quick Start

### Prerequisites

- Python 3.10+
- `pytest`, `pytest-cov`, `pyflakes`

```bash
pip install pytest pytest-cov pyflakes
```

### Run All Tests

```bash
python -m pytest python/ -v
```

### Run Only the COTRN02C Unit Tests

```bash
python -m pytest python/test_cotrn02c.py -v
```

### Run Only the Integration Tests

```bash
python -m pytest python/tests/test_integration.py -v
```

### Check Test Coverage

```bash
python -m pytest python/ --cov=python --cov-report=term-missing
```

### Lint with pyflakes

```bash
pyflakes python/
```

## Architecture

### Repository Pattern

All data access is abstracted behind repository interfaces defined in `python/repositories/base.py`. Each VSAM file has a corresponding abstract base class:

| Repository | VSAM File | Key |
|---|---|---|
| `AccountRepository` | ACCTDAT | ACCT-ID (11 digits) |
| `CardRepository` | CARDDAT | CARD-NUM (16 chars) |
| `CardXrefRepository` | CARDXREF | CARD-NUM + alternate index on ACCT-ID |
| `CustomerRepository` | CUSTDAT | CUST-ID (9 digits) |
| `TransactionRepository` | TRANSACT | TRAN-ID (16 chars) |
| `DailyTransactionRepository` | DALYTRAN | Sequential |
| `UserSecurityRepository` | USRSEC | SEC-USR-ID (8 chars) |
| `TranCatBalRepository` | TCATBALF | ACCT-ID + TYPE-CD + CAT-CD |
| `DisclosureGroupRepository` | DISCGRP | GROUP-ID + TYPE-CD + CAT-CD |
| `TransactionTypeRepository` | TRANTYPE | TRAN-TYPE (2 chars) |
| `TransactionCategoryRepository` | TRANCATG | TYPE-CD + CAT-CD |

In-memory implementations in `python/repositories/in_memory.py` are used for testing.

### Dataclass Models

All COBOL copybook record layouts are represented as Python dataclasses in `python/models/records.py`. Field names follow Python conventions but map directly to the original COBOL field names (documented in comments).

### Adapter Pattern (COTRN02C)

The COTRN02C module was the first program translated (before the shared foundation existed). It defines its own `TransactionRepository` interface with slightly different method names. The `FoundationTransactionRepository` adapter bridges the shared foundation repositories into COTRN02C's expected interface:

```
Shared Foundation                    COTRN02C Interface
─────────────────                    ──────────────────
CardXrefRepository.lookup_by_acct_id → lookup_card_by_account
CardXrefRepository.lookup_by_card_num → lookup_account_by_card
TransactionRepository.get_max_id     → get_max_transaction_id
TransactionRepository.write          → write_transaction
TransactionRepository.get_last_transaction → get_last_transaction
```

## COBOL-to-Python Mapping

| COBOL Program | Python Module | Description |
|---|---|---|
| COTRN02C.CBL | `cotrn02c.py` | Add Transaction — validation, ID generation, record building |
| COCOM01Y.cpy | `models/commarea.py` | Communication area (session state) |
| CVACT01Y.cpy | `models/records.py` → `AccountRecord` | Account master record |
| CVACT02Y.cpy | `models/records.py` → `CardRecord` | Card master record |
| CVACT03Y.cpy | `models/records.py` → `CardXrefRecord` | Card cross-reference |
| CVCUS01Y.cpy | `models/records.py` → `CustomerRecord` | Customer master record |
| CVTRA05Y.cpy | `models/records.py` → `TransactionRecord` | Transaction record |
| CVTRA06Y.cpy | `models/records.py` → `DailyTransactionRecord` | Daily transaction record |
| CVTRA07Y.cpy | `models/report.py` | Report formatting structures |
| CVEXPORT.cpy | `models/export_record.py` | Export file layout |
| COTTL01Y.cpy | `common/constants.py` | Screen titles |
| CSMSG01Y.cpy | `common/constants.py` | Common messages |
| COMEN02Y.cpy | `common/menu.py` | Main menu options |
| COADM02Y.cpy | `common/menu.py` | Admin menu options |
| CSDAT01Y.cpy | `common/constants.py` | Date/time formatting |
| CSUTLDTC | `utils/date_validation.py` | Date validation subroutine |
| CSSTRPFY.cpy | `utils/string_utils.py` | String utility functions |
| CSLKPCDY.cpy | `utils/lookup_codes.py` | State/ZIP/phone code lookups |
| CSUSR01Y.cpy | `models/records.py` → `UserSecurityRecord` | User security record |

## Test Data

The `python/tests/conftest.py` module provides a `populated_system` fixture with:

- **2 customers**: John Doe (NY) and Jane Smith (CA)
- **2 accounts**: balances of $1,500 and $3,200
- **2 cards**: Visa-style numbers linked to respective accounts
- **2 cross-references**: linking cards ↔ accounts ↔ customers
- **3 transactions**: purchases on both cards
- **1 daily transaction**: pending batch posting
- **2 users**: one admin, one regular
- **2 transaction types**: Sale (SA) and Credit (CR)
- **3 transaction categories**: Retail Sale, Grocery, Credit Return

Record factory functions (`make_account`, `make_card`, `make_customer`, etc.) allow creating custom test data with sensible defaults.
