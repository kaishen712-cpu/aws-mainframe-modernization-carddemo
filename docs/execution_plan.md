# CardDemo COBOL-to-Python Translation: Execution Plan

## Scope Summary

The CardDemo application contains **31 COBOL programs**, **30 copybooks**, **17 BMS mapsets**, and **38 JCL files**. A Phase 0 foundation already exists in `python/` with:

- **Models**: `records.py` (12 dataclasses), `commarea.py`, `export_record.py`, `report.py`
- **Repositories**: Abstract interfaces (`base.py`) and in-memory implementations (`in_memory.py`) for all 11 VSAM file types
- **Utils**: `date_validation.py`, `string_utils.py`, `lookup_codes.py`
- **Common**: `constants.py`, `menu.py`
- **One translated program**: `cotrn02c.py` (Add Transaction) with full test suite (`test_cotrn02c.py`, 694 lines)

The plan below translates the remaining 30 COBOL programs into Python, integrates the two requested performance improvements, and produces a production-ready Django application backed by PostgreSQL.

---

## Architecture Mapping: COBOL to Python

| COBOL Technology | Python Equivalent | Rationale |
|---|---|---|
| **VSAM KSDS/AIX files** | **PostgreSQL** (via Django ORM) | Enterprise-grade RDBMS with ACID transactions, concurrent access, row-level locking, and built-in replication. Replaces VSAM's indexed sequential access with proper relational indexes. PostgreSQL is the standard for banking/financial applications requiring data integrity, audit trails, and horizontal scalability. |
| **CICS (online transaction monitor)** | **Django** (web framework) | Django provides URL routing (replaces CICS transaction IDs), middleware (replaces CICS task management), ORM (replaces VSAM file I/O), and built-in auth/session/CSRF/admin. Its "batteries included" philosophy matches the enterprise requirement for a single, cohesive framework with proven security. |
| **BMS maps (3270 screens)** | **Django Templates** | Django's built-in template engine provides server-side HTML rendering consistent with the Django ecosystem. Template inheritance, form rendering, and CSRF integration come out of the box. No need for a separate Jinja2 dependency. |
| **JCL (batch job control)** | **Django management commands** + **cron** / **Celery** | Django management commands (`manage.py <command>`) replace individual JCL steps. Orchestration via cron for simple scheduling or Celery for distributed task queues with retry/monitoring. Management commands integrate with Django's ORM and settings infrastructure. |
| **Copybooks (shared data layouts)** | **Django models** + **Python `dataclasses`** | Django models define the database schema and provide ORM access. Dataclasses remain for DTOs, validation inputs, and batch record structures that don't map directly to database tables. |
| **COBOL file I/O (READ/WRITE/REWRITE/DELETE)** | **Repository pattern** (abstract interfaces + Django ORM implementations) | The repository abstraction (`repositories/base.py`) decouples business logic from storage. Production implementations use Django ORM querysets. In-memory implementations remain for unit testing. |
| **COBOL batch programs** | **Django management commands** in `management/commands/` | Each COBOL batch program becomes a Django management command. Invoked via `python manage.py post_transactions --input daily.dat`. Inherits Django's argument parsing, logging, and database connection management. |
| **CICS COMMAREA (session state)** | **Django sessions** (database-backed) | Django's session framework stores user state server-side with secure cookie-based session IDs. Database-backed sessions provide persistence across restarts and support for concurrent users. |
| **COBOL paragraph PERFORM** | **Python functions/methods** | COBOL paragraphs with PERFORM/THRU become regular Python functions. GO TO and ALTER patterns are replaced with structured control flow (loops, if/else, early return). |
| **No formal testing in COBOL** | **pytest** + **pytest-django** + **pytest-cov** | Full automated test coverage from day one. pytest-django provides Django test client, database fixtures, and transactional test cases. pytest-cov enforces minimum coverage thresholds. |
| **EBCDIC fixed-length records** | **UTF-8 + Django ORM** | Django ORM handles all serialization/deserialization. Business logic never deals with byte offsets or encoding. Import/export utilities handle legacy format conversion. |
| **COBOL CURRENT-DATE intrinsic** | **`django.utils.timezone.now()`** | Timezone-aware datetime handling via Django's timezone utilities. Already have formatting helpers in `python/common/constants.py`. |
| **No security framework** | **Django auth** + **`django.contrib.auth`** | Built-in user model, password hashing (PBKDF2/Argon2), login/logout views, permission framework, CSRF protection, and session security. Replaces the flat-file USRSEC security model with industry-standard auth. |

---

## Code Quality Standards

### CLEAN Code Principles

All translated Python code must adhere to the following CLEAN code standards:

1. **Meaningful Names** — Variables, functions, classes, and modules use intention-revealing names. No single-letter variables outside of list comprehensions. No COBOL-style abbreviated names in business logic (e.g., `calculate_interest()` not `CALC-INT`).
2. **Small Functions** — Each function does one thing. Target max 20 lines per function body. Extract helper functions rather than writing long procedural blocks.
3. **No Side Effects** — Functions that compute values should not modify external state. Functions that modify state should clearly signal it (e.g., `update_account_balance()` not `process()`).
4. **DRY (Don't Repeat Yourself)** — Common patterns (validation, formatting, error handling) are extracted into shared utilities. No copy-paste between modules.
5. **Minimal Comments** — Code should be self-documenting through clear naming. Comments explain *why*, not *what*. Docstrings on all public functions/classes following Google-style format.
6. **Consistent Formatting** — Enforced by `ruff` (linter + formatter). Line length max 99 characters. Imports sorted by `isort` rules built into `ruff`.
7. **Error Handling** — Use specific exception types (never bare `except:`). Define domain-specific exceptions (`AccountNotFoundError`, `TransactionValidationError`, etc.). Log errors with structured context.

### SOLID Principles

1. **Single Responsibility (SRP)** — Each module/class has one reason to change.
   - Example: `AccountRepository` handles data access; `AccountValidator` handles validation; `AccountService` orchestrates workflows.
2. **Open/Closed (OCP)** — Classes are open for extension, closed for modification.
   - Example: New transaction types are handled by adding a new `TransactionProcessor` subclass, not modifying existing ones.
3. **Liskov Substitution (LSP)** — Repository implementations are interchangeable.
   - Example: `InMemoryAccountRepository` and `DjangoAccountRepository` both satisfy `AccountRepository` interface. Tests use in-memory; production uses Django ORM.
4. **Interface Segregation (ISP)** — Clients depend only on the interfaces they use.
   - Example: A report generator depends on `TransactionReadRepository` (read-only), not the full `TransactionRepository` (read + write).
5. **Dependency Inversion (DIP)** — High-level modules depend on abstractions, not concrete implementations.
   - Example: Business logic imports `AccountRepository` (abstract), not `DjangoAccountRepository` (concrete). Concrete implementations are injected via Django settings or constructor injection.

### Enforcement

| Tool | Purpose | Configuration |
|---|---|---|
| `ruff` | Linting + formatting (replaces flake8, isort, black) | `pyproject.toml` — enable rules: E, F, W, I, N, UP, S, B, A, C4, SIM, TCH |
| `mypy` | Static type checking | `pyproject.toml` — `strict = true` |
| `pytest-cov` | Coverage enforcement | See Testing Strategy section |
| `pre-commit` | Git hook enforcement | Runs ruff, mypy, and tests on every commit |

---

## Testing Strategy

### Coverage Requirements

The original COBOL codebase has **zero automated tests**. The Python version establishes automated testing from day one with enforced minimums:

| Category | Modules | Minimum Coverage | Rationale |
|---|---|---|---|
| **Security-sensitive** | Authentication (`cosgn00c`), password handling, session management, CSRF, permission checks | **90%** | Authentication and authorization are the primary attack surface. Untested auth code is a liability in a banking application. |
| **Transaction processing** | `cbtrn02c` (batch posting), `cotrn02c` (online add), `cobil00c` (bill pay), `cbact04c` (interest calc), `BatchAccountUpdater`, `RecordCache` | **90%** | Financial calculations must be provably correct. Rounding errors, double-posting, and missed validations have direct monetary impact. |
| **All other modules** | Account/card/user CRUD, reports, export/import, utilities | **70%** | Adequate coverage for business logic correctness while allowing pragmatic trade-offs on presentation-layer code. |
| **Overall project** | All Python code | **70%** | Enforced by CI pipeline via `pytest --cov --cov-fail-under=70`. |

### Test Types

| Type | Framework | Scope | When |
|---|---|---|---|
| **Unit tests** | `pytest` + `pytest-django` | Individual functions, validators, services | Every module, every phase |
| **Integration tests** | `pytest` + Django `TestCase` | Full request/response cycles, database operations | Phase 8 |
| **Repository tests** | `pytest` | Verify both in-memory and Django ORM implementations satisfy interfaces | Phase 1 onwards |
| **Batch pipeline tests** | `pytest` | End-to-end: load data → post transactions → calculate interest → generate statements | Phase 8 |

### Test Organization

```
tests/
  conftest.py                      # Shared fixtures (test database, sample data)
  factories.py                     # Factory Boy factories for test data generation
  unit/
    test_models.py                 # (exists)
    test_repositories.py           # (exists)
    test_date_validation.py        # (exists)
    test_utils.py                  # (exists)
    test_batch_cbtrn02c.py         # incl. cache & batching tests (90% coverage)
    test_batch_cbact04c.py         # Interest calculation (90% coverage)
    test_batch_statements.py
    test_online_auth.py            # Authentication tests (90% coverage)
    test_online_accounts.py
    test_online_cards.py
    test_online_transactions.py    # Transaction add/view (90% coverage)
    test_online_billpay.py         # Bill payment (90% coverage)
    test_online_users.py
    test_record_cache.py           # Cache correctness (90% coverage)
    test_batch_account_updater.py  # Batched updates (90% coverage)
  integration/
    test_batch_pipeline.py         # End-to-end batch processing
    test_online_workflows.py       # End-to-end online user flows
```

### CI Pipeline

```yaml
# Enforced on every PR
pytest --cov=carddemo --cov-report=term-missing --cov-fail-under=70
ruff check .
mypy .
```

---

## Performance Improvements (Woven Into Plan)

### Improvement 1: Cache Customer/Account Records During Transaction Processing

**What changes**: In `CBTRN02C` (daily transaction posting), the COBOL code performs a VSAM `READ` of the cross-reference file and account file for *every single transaction*, even when consecutive transactions belong to the same card/account. The Python translation will introduce a `RecordCache` that stores the last-read cross-reference and account records in memory. A new database read only happens when the card number or account ID changes.

**Where it lands**: Phase 1 (`post_transactions` management command — batch transaction posting)

**Design**:
```python
from decimal import Decimal

class RecordCache:
    """LRU-style cache for cross-ref and account lookups during batch processing."""
    def __init__(self, xref_repo, account_repo):
        self._xref_repo = xref_repo
        self._account_repo = account_repo
        self._xref_cache: dict[str, CardXrefRecord | None] = {}
        self._account_cache: dict[str, AccountRecord | None] = {}

    def get_xref(self, card_num: str) -> CardXrefRecord | None:
        if card_num not in self._xref_cache:
            self._xref_cache[card_num] = self._xref_repo.lookup_by_card_num(card_num)
        return self._xref_cache[card_num]

    def get_account(self, acct_id: str) -> AccountRecord | None:
        if acct_id not in self._account_cache:
            self._account_cache[acct_id] = self._account_repo.lookup_by_id(acct_id)
        return self._account_cache[acct_id]

    def invalidate_account(self, acct_id: str) -> None:
        """Call after mutating an account record to keep cache consistent."""
        self._account_cache.pop(acct_id, None)
```

### Improvement 2: Batch Account Record Updates

**What changes**: The COBOL `CBTRN02C` rewrites the account master record after *every single posted transaction* (updating `ACCT-CURR-BAL`, `ACCT-CURR-CYC-CREDIT`, `ACCT-CURR-CYC-DEBIT`). The Python translation will accumulate balance deltas in a `dict[acct_id, BalanceDelta]` and flush a single `update()` per account at the end of the batch run, wrapped in a database transaction for atomicity.

**Where it lands**: Phase 1 (`post_transactions` management command — batch transaction posting)

**Design**:
```python
from decimal import Decimal
from django.db import transaction as db_transaction

@dataclass
class BalanceDelta:
    """Accumulated balance changes for one account."""
    curr_bal_delta: Decimal = Decimal("0.00")
    cyc_credit_delta: Decimal = Decimal("0.00")
    cyc_debit_delta: Decimal = Decimal("0.00")

class BatchAccountUpdater:
    """Accumulates balance changes and writes once per account."""
    def __init__(self, account_repo):
        self._repo = account_repo
        self._deltas: dict[str, BalanceDelta] = {}

    def accumulate(self, acct_id: str, amount: Decimal) -> None:
        delta = self._deltas.setdefault(acct_id, BalanceDelta())
        delta.curr_bal_delta += amount
        if amount >= 0:
            delta.cyc_credit_delta += amount
        else:
            delta.cyc_debit_delta += amount

    @db_transaction.atomic
    def flush(self) -> list[str]:
        """Write all accumulated changes atomically.

        Only clears deltas for successfully written accounts.
        Failed account deltas are preserved for retry.
        Returns list of failed acct_ids.
        """
        failures: list[str] = []
        succeeded: list[str] = []
        for acct_id, delta in self._deltas.items():
            record = self._repo.lookup_by_id(acct_id)
            if record is None:
                failures.append(acct_id)
                continue
            record.acct_curr_bal += delta.curr_bal_delta
            record.acct_curr_cyc_credit += delta.cyc_credit_delta
            record.acct_curr_cyc_debit += delta.cyc_debit_delta
            self._repo.update(record)
            succeeded.append(acct_id)
        # Only clear successfully written deltas; failed deltas remain for retry
        for acct_id in succeeded:
            del self._deltas[acct_id]
        return failures
```

**Note**: All monetary fields use `Decimal` (not `float`) to prevent floating-point rounding errors — critical for a banking application.

---

## Phased Execution Plan

### Phase 1 — Batch Processing Core (7 programs)

These are the non-interactive batch COBOL programs. They have no CICS/BMS dependency, making them the simplest to translate. The two performance improvements land here.

| # | COBOL Source | Python Target | Description | Lines | Priority |
|---|---|---|---|---|---|
| 1 | `CBTRN02C.cbl` | `batch/management/commands/post_transactions.py` | Daily transaction posting (+ **both perf improvements**) | 732 | **Critical** |
| 2 | `CBACT04C.cbl` | `batch/management/commands/calc_interest.py` | Interest calculation | 653 | High |
| 3 | `CBTRN01C.cbl` | `batch/management/commands/gen_transaction_report.py` | Transaction report generation | ~600 | High |
| 4 | `CBTRN03C.cbl` | `batch/management/commands/gen_category_report.py` | Transaction category balance report | ~500 | Medium |
| 5 | `CBSTM03A.CBL` | `batch/management/commands/gen_statements.py` | Statement generation (text + HTML) | 924 | High |
| 6 | `CBSTM03B.CBL` | `batch/management/commands/gen_statements_v2.py` | Statement generation variant | ~800 | Medium |
| 7 | `CBACT01C.cbl` — `CBACT03C.cbl` | `batch/management/commands/seed_accounts.py`, `list_accounts.py`, `validate_accounts.py` | Account file utilities | ~400 ea | Medium |

**Tasks**:
1. Initialize Django project (`carddemo/`) with `batch` app
2. Define Django models mapping to existing dataclasses (PostgreSQL schema)
3. Create `batch/services/record_cache.py` — the `RecordCache` class (Perf Improvement 1)
4. Create `batch/services/batch_account_updater.py` — the `BatchAccountUpdater` class (Perf Improvement 2)
5. Translate `CBTRN02C.cbl` → `post_transactions` management command
   - Replace per-transaction VSAM READs with `RecordCache` lookups
   - Replace per-transaction account REWRITEs with `BatchAccountUpdater.accumulate()`
   - Call `BatchAccountUpdater.flush()` after all transactions processed (atomic DB transaction)
   - Preserve all validation logic (card lookup, credit limit, expiration check)
   - Preserve reject-file writing for failed transactions
6. Write unit tests: `tests/unit/test_batch_post_transactions.py` (**90% coverage**)
   - Test that cache prevents redundant reads (mock/spy on repository)
   - Test that account updates are batched (single write per account)
   - Test validation rules: invalid card, overlimit, expired account
   - Test reject-file output for failed transactions
7. Translate remaining batch programs
8. Write unit tests for each (interest calc at **90% coverage**)

**Deliverable**: All batch programs runnable via `python manage.py <command>` with CLI argument support.

---

### Phase 2 — Authentication & Navigation (3 programs)

The CICS sign-on and menu programs. These form the session management layer.

| # | COBOL Source | Python Target | Description | Lines |
|---|---|---|---|---|
| 1 | `COSGN00C.cbl` | `accounts/views.py` (login/logout) | Sign-on / authentication | 261 |
| 2 | `COMEN01C.cbl` | `core/views.py` (main menu) | Main menu (regular users) | 309 |
| 3 | `COADM01C.cbl` | `core/views.py` (admin menu) | Admin menu | ~300 |

**Tasks**:
1. Create `accounts` Django app for authentication
2. Extend `django.contrib.auth.User` or create custom user model with `user_type` (admin/regular), mapping from COBOL `USRSEC` record
3. Implement login/logout views using Django's auth framework with:
   - Password hashing (Argon2 via `django.contrib.auth.hashers`)
   - Session-based authentication (database-backed sessions)
   - Login attempt throttling (prevent brute force)
   - CSRF protection (built-in)
4. Translate menu routing using Django URL patterns and `@login_required` / `@user_passes_test` decorators
5. Django Templates for login screen and menu pages
6. Unit tests for auth validation, login throttling, menu option routing, admin vs. user access (**90% coverage**)

---

### Phase 3 — Account Management (2 programs)

| # | COBOL Source | Python Target | Description | Lines |
|---|---|---|---|---|
| 1 | `COACTVWC.cbl` | `accounts_mgmt/views.py` (AccountDetailView) | Account View | 942 |
| 2 | `COACTUPC.cbl` | `accounts_mgmt/views.py` (AccountUpdateView) | Account Update | 4,237 |

**Tasks**:
1. Create `accounts_mgmt` Django app
2. Translate `COACTVWC` — read-only account display using Django `DetailView`
3. Translate `COACTUPC` — account update using Django `UpdateView` with form validation
   - This is the **largest single program** (4,237 lines). Decompose into:
     - `accounts_mgmt/forms.py` — Django forms with field-level validation (date, numeric, SSN, phone, state/zip)
     - `accounts_mgmt/services.py` — Account update service (change detection, business rules)
     - Reuse: `date_validation.py`, `lookup_codes.py`
4. Django Templates for account view/edit screens
5. Unit tests: validation edge cases, update-only-changed-fields logic (70% coverage)

---

### Phase 4 — Credit Card Management (3 programs)

| # | COBOL Source | Python Target | Description | Lines |
|---|---|---|---|---|
| 1 | `COCRDLIC.cbl` | `cards/views.py` (CardListView) | Credit Card List | 1,460 |
| 2 | `COCRDSLC.cbl` | `cards/views.py` (CardDetailView) | Credit Card View/Select | ~800 |
| 3 | `COCRDUPC.cbl` | `cards/views.py` (CardUpdateView) | Credit Card Update | ~1,200 |

**Tasks**:
1. Create `cards` Django app
2. Translate list/browse logic — Django `ListView` with pagination (replaces STARTBR/READNEXT)
3. Translate view and update logic using Django generic views + forms
4. Django Templates for card list/view/edit screens
5. Unit tests for pagination, filtering, field validation (70% coverage)

---

### Phase 5 — Transaction Management (4 programs)

| # | COBOL Source | Python Target | Description | Lines |
|---|---|---|---|---|
| 1 | `COTRN00C.cbl` | `transactions/views.py` (TransactionListView) | Transaction List | 700 |
| 2 | `COTRN01C.cbl` | `transactions/views.py` (TransactionDetailView) | Transaction View | ~600 |
| 3 | `COTRN02C.cbl` | `transactions/views.py` (TransactionCreateView) | Transaction Add | 646 |
| 4 | `COBIL00C.cbl` | `transactions/views.py` (BillPaymentView) | Bill Payment | ~500 |

**Tasks**:
1. Create `transactions` Django app
2. Refactor existing `python/cotrn02c.py` business logic into `transactions/services.py`
3. Translate remaining online transaction views
4. Translate bill payment (`COBIL00C`)
5. `CORPT00C.cbl` → `reports/views.py` (dispatches to batch report management commands)
6. Django Templates for transaction screens
7. Unit tests (**90% coverage** for transaction add and bill payment)

---

### Phase 6 — User Administration (4 programs)

| # | COBOL Source | Python Target | Description | Lines |
|---|---|---|---|---|
| 1 | `COUSR00C.cbl` | `user_admin/views.py` (UserListView) | User List | ~500 |
| 2 | `COUSR01C.cbl` | `user_admin/views.py` (UserCreateView) | User Add | ~400 |
| 3 | `COUSR02C.cbl` | `user_admin/views.py` (UserUpdateView) | User Update | ~400 |
| 4 | `COUSR03C.cbl` | `user_admin/views.py` (UserDeleteView) | User Delete | ~400 |

**Tasks**:
1. Create `user_admin` Django app (admin-only access via `@user_passes_test`)
2. Translate CRUD operations using Django generic views + `django.contrib.auth` user model
3. Django Templates for user management screens
4. Unit tests for add/update/delete with duplicate/not-found edge cases (70% coverage)

---

### Phase 7 — Export/Import & Utilities (4 programs)

| # | COBOL Source | Python Target | Description | Lines |
|---|---|---|---|---|
| 1 | `CBEXPORT.cbl` | `batch/management/commands/export_data.py` | Data export (multi-record format) | ~500 |
| 2 | `CBIMPORT.cbl` | `batch/management/commands/import_data.py` | Data import | ~500 |
| 3 | `CSUTLDTC.cbl` | Already translated: `utils/date_validation.py` | Date validation utility | 291 (done) |
| 4 | `COBSWAIT.cbl` | `utils/timer.py` | Batch wait/timer (trivial) | ~50 |

**Tasks**:
1. Translate export/import using existing `ExportRecord` model + Django ORM
2. Timer utility (replace ASSEMBLER MVSWAIT with `time.sleep`)
3. Unit tests (70% coverage)

---

### Phase 8 — Integration, Deployment & Documentation

**Tasks**:
1. Create `carddemo/settings/` with environment-based configuration:
   - `base.py` — shared settings
   - `development.py` — DEBUG=True, local PostgreSQL
   - `production.py` — DEBUG=False, connection pooling, secure cookies, HSTS
   - `testing.py` — in-memory optimizations for fast test runs
2. Configure `pyproject.toml` with all dependencies:
   - Core: `django`, `psycopg[binary]`, `django-environ`, `gunicorn`
   - Dev: `pytest`, `pytest-django`, `pytest-cov`, `factory-boy`, `ruff`, `mypy`
3. Create `Dockerfile` and `docker-compose.yml` (Django + PostgreSQL + Redis for sessions)
4. Write integration tests that run the full batch pipeline:
   - Load sample data → post transactions → calculate interest → generate statements
   - Verify performance improvements (assert cache hit counts, assert single write per account)
5. Set up CI pipeline (GitHub Actions):
   - `ruff check .` + `mypy .` + `pytest --cov --cov-fail-under=70`
   - Per-module coverage checks for 90% security/transaction modules
6. Update `docs/` with:
   - `docs/python-translation.md` — mapping table of COBOL program → Python module
   - `docs/deployment.md` — production deployment guide
   - Update `README.md` with Python usage instructions

---

## Django Project Structure (Final)

```
carddemo/                              # Django project root
  manage.py
  carddemo/                            # Project configuration
    __init__.py
    settings/
      __init__.py
      base.py                          # Shared settings
      development.py                   # Local dev settings
      production.py                    # Production settings (secure)
      testing.py                       # Test runner settings
    urls.py                            # Root URL configuration
    wsgi.py
    asgi.py
  core/                                # Django app: navigation, shared templates
    __init__.py
    views.py                           # Main menu, admin menu
    templates/
      base.html                        # Base template (replaces BMS screen layout)
      core/menu.html
      core/admin_menu.html
  accounts/                            # Django app: authentication
    __init__.py
    models.py                          # Custom user model (extends AbstractUser)
    views.py                           # Login, logout
    forms.py                           # Login form
    backends.py                        # Custom auth backend (if needed)
    templates/accounts/login.html
  accounts_mgmt/                       # Django app: account management
    __init__.py
    models.py                          # Account, Customer Django models
    views.py                           # AccountDetailView, AccountUpdateView
    forms.py                           # Account validation forms
    services.py                        # Business logic (SRP)
    templates/accounts_mgmt/
  cards/                               # Django app: credit card management
    __init__.py
    models.py                          # Card, CardXref Django models
    views.py                           # CardListView, CardDetailView, CardUpdateView
    forms.py
    templates/cards/
  transactions/                        # Django app: transaction management
    __init__.py
    models.py                          # Transaction Django model
    views.py                           # List, Detail, Create, BillPayment views
    forms.py
    services.py                        # Transaction add business logic (from cotrn02c)
    templates/transactions/
  reports/                             # Django app: report dispatching
    __init__.py
    views.py
    templates/reports/
  user_admin/                          # Django app: user administration
    __init__.py
    views.py                           # UserListView, Create, Update, Delete
    forms.py
    templates/user_admin/
  batch/                               # Django app: batch processing
    __init__.py
    services/
      __init__.py
      record_cache.py                  # Perf Improvement 1
      batch_account_updater.py         # Perf Improvement 2
      interest_calculator.py           # Interest calc business logic
      statement_generator.py           # Statement generation logic
    management/
      commands/
        post_transactions.py           # CBTRN02C
        calc_interest.py               # CBACT04C
        gen_transaction_report.py      # CBTRN01C
        gen_category_report.py         # CBTRN03C
        gen_statements.py              # CBSTM03A
        gen_statements_v2.py           # CBSTM03B
        seed_accounts.py               # CBACT01C
        list_accounts.py               # CBACT02C
        validate_accounts.py           # CBACT03C
        export_data.py                 # CBEXPORT
        import_data.py                 # CBIMPORT
  common/                              # Shared utilities (from Phase 0)
    __init__.py
    constants.py                       # (exists)
    menu.py                            # (exists)
  utils/                               # Shared utilities (from Phase 0)
    __init__.py
    date_validation.py                 # (exists)
    string_utils.py                    # (exists)
    lookup_codes.py                    # (exists)
    timer.py                           # COBSWAIT replacement
  repositories/                        # Abstract + concrete repository implementations
    __init__.py
    base.py                            # (exists — abstract interfaces)
    in_memory.py                       # (exists — for unit tests)
    django_orm.py                      # NEW — Django ORM implementations
  tests/
    __init__.py
    conftest.py                        # Shared fixtures, test DB config
    factories.py                       # Factory Boy factories
    unit/
      test_models.py
      test_repositories.py
      test_date_validation.py
      test_utils.py
      test_batch_post_transactions.py  # 90% coverage
      test_batch_interest.py           # 90% coverage
      test_batch_statements.py
      test_online_auth.py              # 90% coverage
      test_online_accounts.py
      test_online_cards.py
      test_online_transactions.py      # 90% coverage
      test_online_billpay.py           # 90% coverage
      test_online_users.py
      test_record_cache.py             # 90% coverage
      test_batch_account_updater.py    # 90% coverage
    integration/
      test_batch_pipeline.py
      test_online_workflows.py
  Dockerfile
  docker-compose.yml                   # Django + PostgreSQL + Redis
  pyproject.toml                       # Dependencies, ruff, mypy, pytest config
  .pre-commit-config.yaml              # Pre-commit hooks
```

---

## Execution Order & Dependencies

```
Phase 1 (Batch Core + Perf Improvements + Django/PostgreSQL Setup)
  +-- Django project init + PostgreSQL models
  +-- record_cache.py
  +-- batch_account_updater.py
  +-- post_transactions.py (uses both)
      calc_interest.py
      gen_transaction_report.py
      gen_statements.py
      seed/list/validate_accounts.py
                                        |
Phase 2 (Auth & Nav) <------------------+ (Django auth + session framework)
  +-- Custom user model + auth views
  +-- Login/logout with Django Templates
  +-- Menu routing via URL patterns
                    |
Phase 3-6 (Online programs) <---------- (depend on Phase 2 auth layer)
  +-- Phase 3: Account View/Update (Django generic views + forms)
  +-- Phase 4: Credit Card List/View/Update
  +-- Phase 5: Transaction List/View/Add/BillPay
  +-- Phase 6: User Admin CRUD
                    |
Phase 7 (Export/Import) <--------------- (standalone, can run in parallel with 3-6)
                    |
Phase 8 (Integration + Deployment) <--- (depends on all above)
```

---

## Estimated Effort Per Phase

| Phase | Programs | Est. New Python Lines | Est. Test Lines | Notes |
|---|---|---|---|---|
| 1 — Batch Core + Django Setup | 7 + 2 perf modules + models | ~3,000 | ~1,500 | Highest value; perf improvements + DB schema |
| 2 — Auth & Nav | 3 + custom user model | ~800 | ~600 | Django auth does the heavy lifting |
| 3 — Account Mgmt | 2 | ~1,500 | ~800 | COACTUPC is 4,237 lines of COBOL |
| 4 — Credit Cards | 3 | ~1,200 | ~600 | Django ListView handles pagination |
| 5 — Transactions | 4 (1 exists) | ~1,000 | ~600 | Existing cotrn02c refactored into service |
| 6 — User Admin | 4 | ~600 | ~400 | Django generic views + auth model |
| 7 — Export/Import | 2 + timer | ~400 | ~200 | Export model already exists |
| 8 — Integration + Deploy | Config + Docker + CI + docs | ~600 | ~500 | Wiring + deployment infrastructure |
| **Total** | **~30 programs** | **~9,100** | **~5,200** | |

---

## Translation Conventions

1. **One Django app per functional domain** — `accounts`, `cards`, `transactions`, etc. Each app is self-contained with models, views, forms, services, and templates.
2. **Business logic in service classes, not views** — Views handle HTTP; services handle business rules. This follows SRP and keeps code testable.
3. **Repository pattern preserved** — Abstract interfaces in `repositories/base.py` with Django ORM implementations in `repositories/django_orm.py`. In-memory implementations remain for unit tests.
4. **Django models for all persistent data** — Replace VSAM file definitions. Migrations manage schema evolution.
5. **`Decimal` for all monetary fields** — Never use `float` for money. Django `DecimalField` + Python `decimal.Decimal` throughout.
6. **Type hints everywhere** — `from __future__ import annotations` + full typing. Enforced by `mypy --strict`.
7. **Docstrings reference original COBOL** — e.g., "Translated from paragraph 2700-UPDATE-TCATBAL in CBTRN02C.cbl"
8. **Django Templates for all screens** — Consistent with Django ecosystem. Template inheritance from `base.html`.
9. **Structured logging** — `logging` module with JSON-formatted output for production. Log all financial operations with audit context.
10. **Environment-based configuration** — `django-environ` for 12-factor app compliance. No secrets in code.

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| `COACTUPC.cbl` is 4,237 lines — largest program | High translation effort | Decompose into Django forms + services; reuse `date_validation.py` and `lookup_codes.py` |
| BMS screen layouts have no direct HTML equivalent | Visual fidelity loss | Django Templates with Bootstrap/CSS for clean, responsive forms. Focus on functionality over pixel-perfect 3270 reproduction. |
| `CBSTM03A` uses `ALTER`/`GO TO` and control-block addressing | Hard to translate literally | Rewrite as clean Python with `for` loops and standard control flow — document divergence from COBOL |
| VSAM → PostgreSQL data migration | One-time migration effort | Build import management command (`import_data.py`) in Phase 7. Validate row counts and checksums post-migration. |
| PostgreSQL connection management in batch | Connection exhaustion under load | Use Django's `CONN_MAX_AGE` + `pgBouncer` connection pooling in production. Batch commands use `django.db.connection.close()` between large operations. |
| Decimal precision differences | Rounding discrepancies vs. COBOL COMP-3 | Use `Decimal` with explicit precision (`ROUND_HALF_EVEN` — banker's rounding). Validate against COBOL output for sample datasets. |
| Optional DB2/IMS/MQ programs not in scope | Incomplete translation | These are extension modules (`COTRTLIC`, `COTRTUPC`, `COPAUS0C`). Flag as out-of-scope in docs; translate if time permits. |
