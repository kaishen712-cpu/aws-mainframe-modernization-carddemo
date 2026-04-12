# CardDemo COBOL-to-Python Translation Mapping

## Overview

This document maps each of the 31 original COBOL programs to their Python equivalents in the CardDemo Django application.

## Online Programs (CICS Transactions → Django Views)

| # | COBOL Program | Transaction | Python Module | Description |
|---|---|---|---|---|
| 1 | `COSGN00C.cbl` | CC00 | `accounts/views.py` (login/logout) | Sign-on / authentication |
| 2 | `COMEN01C.cbl` | CM00 | `core/views.py` (main_menu) | Main menu (regular users) |
| 3 | `COADM01C.cbl` | CA00 | `core/views.py` (admin_menu) | Admin menu |
| 4 | `COACTVWC.cbl` | CAVW | `accounts_mgmt/views.py` (AccountDetailView) | Account view |
| 5 | `COACTUPC.cbl` | CAUP | `accounts_mgmt/views.py` (AccountUpdateView) | Account update |
| 6 | `COCRDLIC.cbl` | CCLI | `cards/views.py` (CardListView) | Credit card list |
| 7 | `COCRDSLC.cbl` | CCDL | `cards/views.py` (CardDetailView) | Credit card view/select |
| 8 | `COCRDUPC.cbl` | CCUP | `cards/views.py` (CardUpdateView) | Credit card update |
| 9 | `COTRN00C.cbl` | CT00 | `transactions/views.py` (TransactionListView) | Transaction list |
| 10 | `COTRN01C.cbl` | CT01 | `transactions/views.py` (TransactionDetailView) | Transaction view |
| 11 | `COTRN02C.cbl` | CT02 | `transactions/views.py` (TransactionCreateView) | Transaction add |
| 12 | `COBIL00C.cbl` | CB00 | `transactions/views.py` (BillPaymentView) | Bill payment |
| 13 | `CORPT00C.cbl` | CR00 | `reports/views.py` (ReportView) | Transaction reports |
| 14 | `COUSR00C.cbl` | CU00 | `user_admin/views.py` (UserListView) | User list |
| 15 | `COUSR01C.cbl` | CU01 | `user_admin/views.py` (UserCreateView) | User add |
| 16 | `COUSR02C.cbl` | CU02 | `user_admin/views.py` (UserUpdateView) | User update |
| 17 | `COUSR03C.cbl` | CU03 | `user_admin/views.py` (UserDeleteView) | User delete |

## Batch Programs (JCL Jobs → Django Management Commands)

| # | COBOL Program | JCL Job | Python Module | Description |
|---|---|---|---|---|
| 18 | `CBTRN02C.cbl` | POSTTRAN | `batch/management/commands/post_transactions.py` | Daily transaction posting (+ RecordCache + BatchAccountUpdater) |
| 19 | `CBACT04C.cbl` | INTCALC | `batch/management/commands/calc_interest.py` | Interest calculation |
| 20 | `CBTRN01C.cbl` | TRANREPT | `batch/management/commands/gen_transaction_report.py` | Transaction report generation |
| 21 | `CBTRN03C.cbl` | — | `batch/management/commands/gen_category_report.py` | Transaction category balance report |
| 22 | `CBSTM03A.CBL` | CREASTMT | `batch/management/commands/gen_statements.py` | Statement generation |
| 23 | `CBSTM03B.CBL` | — | `batch/management/commands/gen_statements_v2.py` | Statement generation variant |
| 24 | `CBACT01C.cbl` | ACCTFILE | `batch/management/commands/seed_accounts.py` | Account file seed |
| 25 | `CBACT02C.cbl` | — | `batch/management/commands/list_accounts.py` | Account file list |
| 26 | `CBACT03C.cbl` | — | `batch/management/commands/validate_accounts.py` | Account file validation |
| 27 | `CBEXPORT.cbl` | — | `batch/management/commands/export_data.py` | Data export (multi-record format) |
| 28 | `CBIMPORT.cbl` | — | `batch/management/commands/import_data.py` | Data import |

## Utility Programs

| # | COBOL Program | Python Module | Description |
|---|---|---|---|
| 29 | `CSUTLDTC.cbl` | `python/utils/date_validation.py` | Date validation utility (Phase 0) |
| 30 | `COBSWAIT.cbl` | `utils/timer.py` | Batch wait/timer (replaces ASSEMBLER MVSWAIT) |
| 31 | `COTRN02C.cbl` | `python/cotrn02c.py` | Transaction add business logic (Phase 0 prototype) |

## Performance Improvements

| Improvement | COBOL Pattern | Python Module | Description |
|---|---|---|---|
| RecordCache | Per-txn VSAM READ in CBTRN02C | `batch/services/record_cache.py` | LRU cache for xref/account lookups during batch processing |
| BatchAccountUpdater | Per-txn REWRITE in CBTRN02C | `batch/services/batch_account_updater.py` | Accumulates balance deltas, flushes once per account atomically |

## Data Model Mapping (COBOL Copybooks → Django Models)

| Copybook | COBOL Record | Django Model | DB Table | Module |
|---|---|---|---|---|
| `CVACT01Y.cpy` | ACCOUNT-RECORD | `Account` | `account` | `batch/models.py` |
| `CVACT02Y.cpy` | CARD-RECORD | `Card` | `card` | `batch/models.py` |
| `CVACT03Y.cpy` | CARD-XREF-RECORD | `CardXref` | `card_xref` | `batch/models.py` |
| `CVCUS01Y.cpy` | CUSTOMER-RECORD | `Customer` | `customer` | `batch/models.py` |
| `CVTRA05Y.cpy` | TRAN-RECORD | `Transaction` | `transaction` | `batch/models.py` |
| `CVTRA06Y.cpy` | DALYTRAN-RECORD | `DailyTransaction` | `daily_transaction` | `batch/models.py` |
| `CVTRA01Y.cpy` | TRAN-CAT-BAL-RECORD | `TranCatBal` | `tran_cat_bal` | `batch/models.py` |
| `CVTRA02Y.cpy` | DIS-GROUP-RECORD | `DisclosureGroup` | `disclosure_group` | `batch/models.py` |
| `CVTRA03Y.cpy` | TRAN-TYPE-RECORD | `TransactionType` | `transaction_type` | `batch/models.py` |
| `CVTRA04Y.cpy` | TRAN-CAT-TYPE-RECORD | `TransactionCategory` | `transaction_category` | `batch/models.py` |
| `CSUSR01Y.cpy` | SEC-USER-DATA | `UserSecurity` | `user_security` | `batch/models.py` |
| `COSTM01.CPY` | TRNX-RECORD | `TransactionIndex` | `transaction_index` | `batch/models.py` |

## Technology Mapping

| COBOL Technology | Python Equivalent |
|---|---|
| VSAM KSDS/AIX | PostgreSQL (Django ORM) |
| CICS transactions | Django views + URL routing |
| BMS maps (3270 screens) | Django Templates |
| JCL batch jobs | Django management commands |
| Copybooks | Django models + dataclasses |
| COBOL file I/O | Repository pattern (abstract + Django ORM) |
| CICS COMMAREA | Django sessions (database-backed) |
| COBOL paragraph PERFORM | Python functions/methods |
| EBCDIC fixed-length records | UTF-8 + Django ORM |
| RACF security | Django auth + `django.contrib.auth` |

## Optional/Out-of-Scope Programs

The following programs depend on optional mainframe technologies (DB2, IMS, MQ) and are flagged as out-of-scope for the initial migration:

| COBOL Program | Transaction | Technology | Status |
|---|---|---|---|
| `COTRTLIC.cbl` | CTLI | DB2 | Out of scope |
| `COTRTUPC.cbl` | CTTU | DB2 | Out of scope |
| `COPAUS0C.cbl` | CPVS | IMS + DB2 + MQ | Out of scope |
| `COPAUS1C.cbl` | CPVD | IMS + DB2 | Out of scope |
| `COPAUA0C.cbl` | CP00 | IMS + MQ | Out of scope |
| `CODATE01.cbl` | CDRD | MQ | Out of scope |
| `COACCT01.cbl` | CDRA | MQ | Out of scope |
