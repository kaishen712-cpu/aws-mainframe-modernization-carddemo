# CardDemo COBOL-to-Python Translation: Execution Plan

## Scope Summary

The CardDemo application contains **31 COBOL programs**, **30 copybooks**, **17 BMS mapsets**, and **38 JCL files**. A Phase 0 foundation already exists in `python/` with:

- **Models**: `records.py` (12 dataclasses), `commarea.py`, `export_record.py`, `report.py`
- **Repositories**: Abstract interfaces (`base.py`) and in-memory implementations (`in_memory.py`) for all 11 VSAM file types
- **Utils**: `date_validation.py`, `string_utils.py`, `lookup_codes.py`
- **Common**: `constants.py`, `menu.py`
- **One translated program**: `cotrn02c.py` (Add Transaction) with full test suite (`test_cotrn02c.py`, 694 lines)

The plan below translates the remaining 30 COBOL programs into Python, integrates the two requested performance improvements, and produces a fully testable Python application.

---

## Performance Improvements (Woven Into Plan)

### Improvement 1: Cache Customer/Account Records During Transaction Processing

**What changes**: In `CBTRN02C` (daily transaction posting), the COBOL code performs a VSAM `READ` of the cross-reference file and account file for *every single transaction*, even when consecutive transactions belong to the same card/account. The Python translation will introduce a `RecordCache` that stores the last-read cross-reference and account records in memory. A new disk read only happens when the card number or account ID changes.

**Where it lands**: Phase 2 (`cbtrn02c.py` — batch transaction posting)

**Design**:
```python
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

**What changes**: The COBOL `CBTRN02C` rewrites the account master record after *every single posted transaction* (updating `ACCT-CURR-BAL`, `ACCT-CURR-CYC-CREDIT`, `ACCT-CURR-CYC-DEBIT`). The Python translation will accumulate balance deltas in a `dict[acct_id, BalanceDelta]` and flush a single `update()` per account at the end of the batch run.

**Where it lands**: Phase 2 (`cbtrn02c.py` — batch transaction posting)

**Design**:
```python
@dataclass
class BalanceDelta:
    """Accumulated balance changes for one account."""
    curr_bal_delta: float = 0.0
    cyc_credit_delta: float = 0.0
    cyc_debit_delta: float = 0.0

class BatchAccountUpdater:
    """Accumulates balance changes and writes once per account."""
    def __init__(self, account_repo):
        self._repo = account_repo
        self._deltas: dict[str, BalanceDelta] = {}

    def accumulate(self, acct_id: str, amount: float) -> None:
        delta = self._deltas.setdefault(acct_id, BalanceDelta())
        delta.curr_bal_delta += amount
        if amount >= 0:
            delta.cyc_credit_delta += amount
        else:
            delta.cyc_debit_delta += amount

    def flush(self) -> list[str]:
        """Write all accumulated changes. Returns list of failed acct_ids."""
        failures = []
        for acct_id, delta in self._deltas.items():
            record = self._repo.lookup_by_id(acct_id)
            if record is None:
                failures.append(acct_id)
                continue
            record.acct_curr_bal += delta.curr_bal_delta
            record.acct_curr_cyc_credit += delta.cyc_credit_delta
            record.acct_curr_cyc_debit += delta.cyc_debit_delta
            self._repo.update(record)
        self._deltas.clear()
        return failures
```

---

## Phased Execution Plan

### Phase 1 — Batch Processing Core (7 programs)

These are the non-interactive batch COBOL programs. They have no CICS/BMS dependency, making them the simplest to translate. The two performance improvements land here.

| # | COBOL Source | Python Target | Description | Lines | Priority |
|---|---|---|---|---|---|
| 1 | `CBTRN02C.cbl` | `python/batch/cbtrn02c.py` | Daily transaction posting (+ **both perf improvements**) | 732 | **Critical** |
| 2 | `CBACT04C.cbl` | `python/batch/cbact04c.py` | Interest calculation | 653 | High |
| 3 | `CBTRN01C.cbl` | `python/batch/cbtrn01c.py` | Transaction report generation | ~600 | High |
| 4 | `CBTRN03C.cbl` | `python/batch/cbtrn03c.py` | Transaction category balance report | ~500 | Medium |
| 5 | `CBSTM03A.CBL` | `python/batch/cbstm03a.py` | Statement generation (text + HTML) | 924 | High |
| 6 | `CBSTM03B.CBL` | `python/batch/cbstm03b.py` | Statement generation variant | ~800 | Medium |
| 7 | `CBACT01C.cbl` through `CBACT03C.cbl` | `python/batch/cbact01c.py`, `cbact02c.py`, `cbact03c.py` | Account file utilities (seed, list, validate) | ~400 ea | Medium |

**Tasks**:
1. Create `python/batch/` package with `__init__.py`
2. Create `python/batch/record_cache.py` — the `RecordCache` class (Perf Improvement 1)
3. Create `python/batch/batch_account_updater.py` — the `BatchAccountUpdater` class (Perf Improvement 2)
4. Translate `CBTRN02C.cbl` → `python/batch/cbtrn02c.py`
   - Replace per-transaction VSAM READs with `RecordCache` lookups
   - Replace per-transaction account REWRITEs with `BatchAccountUpdater.accumulate()`
   - Call `BatchAccountUpdater.flush()` after all transactions processed
   - Preserve all validation logic (card lookup, credit limit, expiration check)
   - Preserve reject-file writing for failed transactions
5. Write unit tests: `python/tests/test_batch_cbtrn02c.py`
   - Test that cache prevents redundant reads (mock/spy on repository)
   - Test that account updates are batched (single write per account)
   - Test validation rules: invalid card, overlimit, expired account
   - Test reject-file output for failed transactions
6. Translate remaining batch programs (CBACT04C, CBTRN01C, CBTRN03C, CBSTM03A/B, CBACT01C-03C)
7. Write unit tests for each

**Deliverable**: All batch programs runnable via `python -m python.batch.<module>` with CLI argument support for input/output file paths.

---

### Phase 2 — Authentication & Navigation (3 programs)

The CICS sign-on and menu programs. These form the session management layer.

| # | COBOL Source | Python Target | Description | Lines |
|---|---|---|---|---|
| 1 | `COSGN00C.cbl` | `python/online/cosgn00c.py` | Sign-on / authentication | 261 |
| 2 | `COMEN01C.cbl` | `python/online/comen01c.py` | Main menu (regular users) | 309 |
| 3 | `COADM01C.cbl` | `python/online/coadm01c.py` | Admin menu | ~300 |

**Tasks**:
1. Create `python/online/` package
2. Create `python/online/session.py` — session context replacing CICS COMMAREA passing
   - Wraps `CardDemoCommarea` (already in `python/models/commarea.py`)
   - Provides `navigate_to(program)`, `is_authenticated`, `current_user` etc.
3. Translate authentication logic from `COSGN00C` (VSAM user security file read, password comparison, user-type routing)
4. Translate menu routing from `COMEN01C` and `COADM01C` (already have menu definitions in `python/common/menu.py`)
5. Unit tests for auth validation, menu option routing, admin vs. user access

---

### Phase 3 — Account Management (2 programs)

| # | COBOL Source | Python Target | Description | Lines |
|---|---|---|---|---|
| 1 | `COACTVWC.cbl` | `python/online/coactvwc.py` | Account View | 942 |
| 2 | `COACTUPC.cbl` | `python/online/coactupc.py` | Account Update | 4,237 |

**Tasks**:
1. Translate `COACTVWC` — read-only account display (account + customer + card xref lookup)
2. Translate `COACTUPC` — full account update with field-level validation
   - This is the **largest single program** (4,237 lines). Decompose into:
     - Input validation module (date fields, numeric fields, SSN, phone, state/zip)
     - Account update logic (change detection, REWRITE)
     - Already have: date validation (`date_validation.py`), lookup codes (`lookup_codes.py`)
3. Unit tests: validation edge cases, update-only-changed-fields logic

---

### Phase 4 — Credit Card Management (3 programs)

| # | COBOL Source | Python Target | Description | Lines |
|---|---|---|---|---|
| 1 | `COCRDLIC.cbl` | `python/online/cocrdlic.py` | Credit Card List | 1,460 |
| 2 | `COCRDSLC.cbl` | `python/online/cocrdslc.py` | Credit Card View/Select | ~800 |
| 3 | `COCRDUPC.cbl` | `python/online/cocrdupc.py` | Credit Card Update | ~1,200 |

**Tasks**:
1. Translate list/browse logic (STARTBR/READNEXT pagination pattern → Python iterator with page windowing)
2. Translate view and update logic
3. Unit tests for pagination, filtering, field validation

---

### Phase 5 — Transaction Management (4 programs)

| # | COBOL Source | Python Target | Description | Lines |
|---|---|---|---|---|
| 1 | `COTRN00C.cbl` | `python/online/cotrn00c.py` | Transaction List | 700 |
| 2 | `COTRN01C.cbl` | `python/online/cotrn01c.py` | Transaction View | ~600 |
| 3 | `COTRN02C.cbl` | Already exists: `python/cotrn02c.py` | Transaction Add | 646 |
| 4 | `COBIL00C.cbl` | `python/online/cobil00c.py` | Bill Payment | ~500 |

**Tasks**:
1. Move existing `python/cotrn02c.py` → `python/online/cotrn02c.py` (refactor imports to use shared models/repos)
2. Translate remaining online transaction programs
3. Translate bill payment (COBIL00C)
4. `CORPT00C.cbl` → `python/online/corpt00c.py` (Transaction Reports — dispatches to batch report jobs)
5. Unit tests

---

### Phase 6 — User Administration (4 programs)

| # | COBOL Source | Python Target | Description | Lines |
|---|---|---|---|---|
| 1 | `COUSR00C.cbl` | `python/online/cousr00c.py` | User List | ~500 |
| 2 | `COUSR01C.cbl` | `python/online/cousr01c.py` | User Add | ~400 |
| 3 | `COUSR02C.cbl` | `python/online/cousr02c.py` | User Update | ~400 |
| 4 | `COUSR03C.cbl` | `python/online/cousr03c.py` | User Delete | ~400 |

**Tasks**:
1. Translate CRUD operations against user security file
2. Unit tests for add/update/delete with duplicate/not-found edge cases

---

### Phase 7 — Export/Import & Utilities (4 programs)

| # | COBOL Source | Python Target | Description | Lines |
|---|---|---|---|---|
| 1 | `CBEXPORT.cbl` | `python/batch/cbexport.py` | Data export (multi-record format) | ~500 |
| 2 | `CBIMPORT.cbl` | `python/batch/cbimport.py` | Data import | ~500 |
| 3 | `CSUTLDTC.cbl` | Already translated: `python/utils/date_validation.py` | Date validation utility | 291 (done) |
| 4 | `COBSWAIT.cbl` | `python/utils/timer.py` | Batch wait/timer (trivial) | ~50 |

**Tasks**:
1. Translate export/import using existing `ExportRecord` model
2. Timer utility (replace ASSEMBLER MVSWAIT with `time.sleep`)
3. Unit tests

---

### Phase 8 — Integration, CLI & Documentation

**Tasks**:
1. Create `python/main.py` — CLI entry point using `argparse`
   - `python -m python.main batch post-transactions --input daily.dat --output rejects.dat`
   - `python -m python.main batch calc-interest --date 2024-06-30`
   - `python -m python.main batch gen-statements --output statements/`
   - `python -m python.main online` → starts interactive session (text-based menu)
2. Create `python/config.py` — file paths, data directories, configurable settings
3. Add `pyproject.toml` with dependencies (standard library only for core; `pytest` for tests)
4. Write integration tests that run the full batch pipeline:
   - Load sample data → post transactions → calculate interest → generate statements
   - Verify performance improvements are active (assert cache hit counts, assert single write per account)
5. Update `docs/` with:
   - `docs/python-translation.md` — mapping table of COBOL program → Python module
   - Update `README.md` with Python usage instructions

---

## File/Folder Structure (Final)

```
python/
  __init__.py
  main.py                          # CLI entry point
  config.py                        # File paths & settings
  models/
    __init__.py
    commarea.py                    # (exists)
    records.py                     # (exists)
    export_record.py               # (exists)
    report.py                      # (exists)
  repositories/
    __init__.py
    base.py                        # (exists)
    in_memory.py                   # (exists)
    file_based.py                  # NEW — flat-file backed repos for production use
  common/
    __init__.py
    constants.py                   # (exists)
    menu.py                        # (exists)
  utils/
    __init__.py
    date_validation.py             # (exists)
    string_utils.py                # (exists)
    lookup_codes.py                # (exists)
    timer.py                       # NEW — COBSWAIT replacement
  batch/
    __init__.py
    record_cache.py                # NEW — Perf Improvement 1
    batch_account_updater.py       # NEW — Perf Improvement 2
    cbtrn02c.py                    # Daily transaction posting
    cbact04c.py                    # Interest calculation
    cbtrn01c.py                    # Transaction report
    cbtrn03c.py                    # Category balance report
    cbstm03a.py                    # Statement generation
    cbstm03b.py                    # Statement generation variant
    cbact01c.py                    # Account seed
    cbact02c.py                    # Account list
    cbact03c.py                    # Account validate
    cbexport.py                    # Data export
    cbimport.py                    # Data import
  online/
    __init__.py
    session.py                     # Session context (replaces CICS COMMAREA passing)
    cosgn00c.py                    # Sign-on
    comen01c.py                    # Main menu
    coadm01c.py                    # Admin menu
    coactvwc.py                    # Account View
    coactupc.py                    # Account Update
    cocrdlic.py                    # Credit Card List
    cocrdslc.py                    # Credit Card View
    cocrdupc.py                    # Credit Card Update
    cotrn00c.py                    # Transaction List
    cotrn01c.py                    # Transaction View
    cotrn02c.py                    # Transaction Add (moved from python/)
    cobil00c.py                    # Bill Payment
    corpt00c.py                    # Transaction Reports
    cousr00c.py                    # User List
    cousr01c.py                    # User Add
    cousr02c.py                    # User Update
    cousr03c.py                    # User Delete
  tests/
    __init__.py                    # (exists)
    test_models.py                 # (exists)
    test_repositories.py           # (exists)
    test_date_validation.py        # (exists)
    test_utils.py                  # (exists)
    test_batch_cbtrn02c.py         # NEW — incl. cache & batching tests
    test_batch_cbact04c.py         # NEW
    test_batch_statements.py       # NEW
    test_online_auth.py            # NEW
    test_online_accounts.py        # NEW
    test_online_cards.py           # NEW
    test_online_transactions.py    # NEW
    test_online_users.py           # NEW
    test_integration.py            # NEW — end-to-end pipeline
```

---

## Execution Order & Dependencies

```
Phase 1 (Batch Core + Perf Improvements)
  ├── record_cache.py ──────────────────┐
  ├── batch_account_updater.py ─────────┤
  └── cbtrn02c.py (uses both above) ────┤
      cbact04c.py ──────────────────────┤
      cbtrn01c.py ──────────────────────┤
      cbstm03a.py / cbstm03b.py ───────┤
      cbact01c-03c.py ─────────────────┘
                                        │
Phase 2 (Auth & Nav) ◄──────────────────┘ (depends on models/repos from Phase 0)
  ├── session.py
  ├── cosgn00c.py
  └── comen01c.py / coadm01c.py
                    │
Phase 3-6 (Online programs) ◄───────── (depend on Phase 2 session layer)
  ├── Phase 3: Account View/Update
  ├── Phase 4: Credit Card List/View/Update
  ├── Phase 5: Transaction List/View/Add/BillPay
  └── Phase 6: User Admin CRUD
                    │
Phase 7 (Export/Import) ◄────────────── (standalone, can run in parallel with 3-6)
                    │
Phase 8 (Integration) ◄─────────────── (depends on all above)
```

---

## Estimated Effort Per Phase

| Phase | Programs | Est. New Python Lines | Est. Test Lines | Notes |
|---|---|---|---|---|
| 1 — Batch Core | 7 + 2 perf modules | ~2,500 | ~1,200 | Highest value; perf improvements here |
| 2 — Auth & Nav | 3 + session module | ~600 | ~400 | Straightforward |
| 3 — Account Mgmt | 2 | ~1,500 | ~800 | COACTUPC is 4,237 lines of COBOL |
| 4 — Credit Cards | 3 | ~1,200 | ~600 | Pagination logic is repetitive |
| 5 — Transactions | 4 (1 exists) | ~800 | ~400 | COTRN02C already done |
| 6 — User Admin | 4 | ~600 | ~400 | Simple CRUD |
| 7 — Export/Import | 2 + timer | ~400 | ~200 | Export model already exists |
| 8 — Integration | CLI + config + docs | ~400 | ~500 | Wiring everything together |
| **Total** | **~30 programs** | **~8,000** | **~4,500** | |

---

## Translation Conventions

1. **One Python module per COBOL program** — keeps traceability clear
2. **Business logic separated from I/O** — all file/screen operations go through repository interfaces (already established in Phase 0)
3. **No CICS dependency** — CICS `EXEC` calls are replaced by method calls on the session/repository layer
4. **Dataclasses for all record types** — already done in `python/models/records.py`
5. **Type hints everywhere** — `from __future__ import annotations` + full typing
6. **Docstrings reference original COBOL** — e.g., "Translated from paragraph 2700-UPDATE-TCATBAL in CBTRN02C.cbl"
7. **`pytest` for testing** — mirrors the `unittest` approach already used in `test_cotrn02c.py` but more idiomatic

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| `COACTUPC.cbl` is 4,237 lines — largest program | High translation effort | Decompose into validation sub-modules; reuse existing `date_validation.py` and `lookup_codes.py` |
| BMS screen layouts have no Python equivalent | Loss of presentation fidelity | Translate business logic only; provide a simple text-based CLI interface for online programs |
| `CBSTM03A` uses `ALTER`/`GO TO` and control-block addressing | Hard to translate literally | Rewrite as clean Python with `for` loops and standard control flow — document divergence from COBOL |
| VSAM file format specifics (KSDS key structure, AIX) | Data compatibility | The repository abstraction layer already handles this — in-memory for tests, file-based for production |
| Optional DB2/IMS/MQ programs not in scope | Incomplete translation | These are extension modules (`COTRTLIC`, `COTRTUPC`, `COPAUS0C`). Flag as out-of-scope in docs; translate if time permits |
