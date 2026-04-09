# CardDemo Python Translation

Python translation of the AWS CardDemo COBOL mainframe application.

## Project Structure

```
python/
├── common/              # Shared constants, messages, and menu definitions
│   ├── constants.py     # Screen titles, messages, abend data, date/time formatting
│   └── menu.py          # Main menu and admin menu option definitions
├── models/              # Dataclass-based data models (VSAM record types)
│   ├── commarea.py      # Session communication area
│   ├── export_record.py # Multi-record export structures
│   ├── records.py       # Core VSAM record types (Account, Card, Customer, etc.)
│   └── report.py        # Report formatting structures
├── repositories/        # Data-access layer
│   ├── base.py          # Abstract repository interfaces
│   └── in_memory.py     # In-memory implementations for testing
├── utils/               # Utility functions
│   ├── date_validation.py  # Date validation with boundary handling
│   ├── lookup_codes.py     # US state codes, zip combos, phone area codes
│   └── string_utils.py     # COBOL-style string utilities
├── cotrn02c.py          # Add Transaction online program
└── tests/               # Unit test suite
    ├── test_cotrn02c.py
    ├── test_common_constants.py
    ├── test_common_menu.py
    ├── test_date_validation.py
    ├── test_models.py
    ├── test_repositories.py
    └── test_utils.py
```

## Running Tests

```bash
# Run all tests with verbose output
python -m pytest python/ -v

# Run tests with coverage report
python -m pytest python/ --cov=python --cov-report=term-missing --cov-branch --cov-config=python/.coveragerc -v

# Run tests with coverage enforcement (fail if below 80%)
python -m pytest python/ --cov=python --cov-fail-under=80 --cov-branch --cov-config=python/.coveragerc

# Generate HTML coverage report
python -m pytest python/ --cov=python --cov-report=html:python/htmlcov --cov-branch --cov-config=python/.coveragerc
```

## Coverage Summary

| Module | Stmts | Miss | Branch | BrPart | Cover |
|--------|-------|------|--------|--------|-------|
| common/\_\_init\_\_.py | 0 | 0 | 0 | 0 | 100% |
| common/constants.py | 20 | 0 | 0 | 0 | 100% |
| common/menu.py | 22 | 0 | 8 | 0 | 100% |
| cotrn02c.py | 214 | 4 | 54 | 2 | 98% |
| models/\_\_init\_\_.py | 5 | 0 | 0 | 0 | 100% |
| models/commarea.py | 32 | 0 | 0 | 0 | 100% |
| models/export\_record.py | 80 | 0 | 0 | 0 | 100% |
| models/records.py | 122 | 0 | 0 | 0 | 100% |
| models/report.py | 46 | 0 | 0 | 0 | 100% |
| repositories/\_\_init\_\_.py | 2 | 0 | 0 | 0 | 100% |
| repositories/base.py | 64 | 0 | 0 | 0 | 100% |
| repositories/in\_memory.py | 146 | 0 | 16 | 0 | 100% |
| utils/\_\_init\_\_.py | 0 | 0 | 0 | 0 | 100% |
| utils/date\_validation.py | 84 | 0 | 40 | 0 | 100% |
| utils/lookup\_codes.py | 11 | 0 | 0 | 0 | 100% |
| utils/string\_utils.py | 26 | 0 | 4 | 0 | 100% |
| **TOTAL** | **874** | **4** | **122** | **2** | **99%** |

All modules meet the minimum 80% branch coverage threshold.

### CI Enforcement

Coverage is enforced in CI with:

```bash
python -m pytest python/ --cov=python --cov-fail-under=80 --cov-branch --cov-config=python/.coveragerc
```

This command will fail the build if any module drops below 80% overall coverage.
