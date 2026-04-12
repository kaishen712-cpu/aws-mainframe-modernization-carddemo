# CardDemo Codebase Analysis

## 1. Plain English Summary

CardDemo is a **credit card management system** built to simulate the kind of application that runs on a traditional IBM mainframe. It handles the full lifecycle of credit card operations for a fictional bank ("Bank of XYZ"):

- **User authentication** — Customers and admins log in via a terminal-style sign-on screen. Admins get an admin menu; regular users get a standard menu.
- **Account management** — Users can view and update their credit card account details (balances, credit limits, expiration dates, etc.).
- **Credit card management** — Users can list, view, and update credit cards linked to their accounts.
- **Transaction processing** — The core of the application. Daily transactions are read from a flat file, validated (card number lookup, credit limit check, expiration check), and posted to the master transaction file. Rejected transactions are written to a separate rejects file.
- **Interest calculation** — A batch job reads transaction category balances, looks up the applicable interest rate from a disclosure group table, computes monthly interest, and updates account balances.
- **Statement generation** — Another batch job produces account statements in both plain-text and HTML format, pulling together customer info, account details, and transaction history.
- **Bill payment** — Users can make payments against their credit card balance.
- **Transaction reporting** — Users can generate reports on their transactions.
- **Admin functions** — Admins can manage users (list, add, update, delete) and optionally manage transaction types via DB2.
- **Optional modules** — The app also has extensions for credit card authorization processing (via IMS/DB2/MQ), transaction type management (via DB2), and account data extraction (via MQ/VSAM).

The application is specifically designed by AWS as a **realistic mainframe workload** for testing migration and modernization tooling. It intentionally uses a variety of mainframe coding patterns (ALTER/GO TO, COMP/COMP-3 variables, control block addressing, copybooks with REDEFINES/OCCURS, etc.) to exercise analysis and transformation tools.

---

## 2. Programming Language

The application is written primarily in **COBOL** (31 `.cbl` source files in the core `app/cbl/` directory), with supporting technologies:

| Technology | Role | File types |
|---|---|---|
| **COBOL** | Primary application logic (online CICS programs + batch programs) | `.cbl` |
| **BMS (Basic Mapping Support)** | Terminal screen/map definitions for CICS 3270 screens | `.bms` |
| **JCL (Job Control Language)** | Batch job definitions and execution control | `.jcl` |
| **COBOL Copybooks** | Shared data structures and record layouts included via `COPY` | `.cpy` |
| **Assembler** | Two utility subroutines (timer wait, date formatting) | `.asm` |
| **Python** | A small helper script (separate from the mainframe app) | `.py` |

---

## 3. Five Most Important Files

### 1. `app/cbl/CBTRN02C.cbl` — Daily Transaction Posting (732 lines)
The **heart of the batch processing pipeline**. This program:
- Reads the daily transaction file sequentially
- Validates each transaction (card number cross-reference lookup, account existence check, credit limit verification, expiration date check)
- Posts valid transactions to the master transaction VSAM file
- Updates the transaction category balance file (TCATBAL) and the account master file (current balance, cycle credits/debits)
- Writes rejected transactions to a rejects file with failure reason codes
- This is the single most critical business-logic program in the application.

### 2. `app/cbl/COSGN00C.cbl` — Sign-On / Authentication (261 lines)
The **entry point** for all online users. This CICS program:
- Displays the login screen and handles user ID / password entry
- Reads the user security VSAM file to authenticate credentials
- Routes admin users to the admin menu (`COADM01C`) and regular users to the main menu (`COMEN01C`)
- All other online programs depend on successful authentication through this program.

### 3. `app/cbl/CBACT04C.cbl` — Interest Calculation (653 lines)
The **financial engine** of the application. This batch program:
- Sequentially reads the transaction category balance file
- For each account, looks up the applicable interest rate from the disclosure group file
- Computes monthly interest as `(balance * rate) / 1200`
- Writes interest charge transactions to the transaction file
- Updates account balances with accrued interest
- Contains a stub for fee computation (`1400-COMPUTE-FEES`) — not yet implemented.

### 4. `app/cbl/CBSTM03A.CBL` — Statement Generation (924 lines)
The **largest and most complex program** in the codebase. It:
- Generates account statements in both plain-text and HTML formats
- Traverses multiple files (transactions, cross-reference, customer, account) to assemble statement data
- Intentionally uses advanced/legacy COBOL patterns: `ALTER` / `GO TO`, control block addressing (PSA → TCB → TIOT), COMP/COMP-3 variables, 2D arrays, and subroutine calls
- Serves as a comprehensive modernization test case.

### 5. `app/cpy/COCOM01Y.cpy` — Communication Area (Commarea) Copybook (48 lines)
The **shared data contract** between every online CICS program. It defines:
- Navigation context (from/to transaction IDs and program names)
- User identity and type (admin vs. regular user)
- Program re-entry state
- Customer, account, and card identifiers
- Last map/mapset tracking
- Every CICS program `COPY`s this structure and passes it through `DFHCOMMAREA`, making it the backbone of the application's screen-to-screen navigation.

---

## 4. Performance Improvement Opportunities

### 4.1 Redundant I/O in Transaction Posting (`CBTRN02C.cbl`)
**Problem:** For every single daily transaction, the program performs a random `READ` of the cross-reference file (line 383) and then a random `READ` of the account file (line 395). If multiple transactions belong to the same card/account, the same records are read repeatedly.

**Improvement:** Cache the last-read cross-reference and account records in working storage. Only perform a new file READ when the card number or account ID changes. The interest calculator (`CBACT04C.cbl`) already does this pattern correctly with `WS-LAST-ACCT-NUM` — the same approach should be applied to `CBTRN02C`.

### 4.2 Per-Transaction Account REWRITE (`CBTRN02C.cbl`, line 554)
**Problem:** The account master record is rewritten to VSAM after *every single transaction* (`2800-UPDATE-ACCOUNT-REC`). For accounts with many daily transactions, this means dozens or hundreds of redundant VSAM REWRITE operations for the same record.

**Improvement:** Accumulate balance changes in working storage and perform a single REWRITE per account after all of that account's transactions have been processed. This requires pre-sorting the daily transaction file by account (or card number), which could be done via a JCL SORT step before POSTTRAN.

### 4.3 Repeated FUNCTION CURRENT-DATE Calls (`CBTRN02C.cbl`, `CBACT04C.cbl`)
**Problem:** `Z-GET-DB2-FORMAT-TIMESTAMP` calls `FUNCTION CURRENT-DATE` on every invocation (once per transaction posted, once per interest record written). This is a system call that's unnecessarily repeated when the same timestamp (or a close-enough one) would suffice.

**Improvement:** Call `FUNCTION CURRENT-DATE` once at program start (or once per batch of N records) and reuse the value. The sub-second precision is not meaningful for batch posting timestamps.

### 4.4 Sequential Scan in Statement Generation (`CBSTM03A.CBL`)
**Problem:** The statement program uses `ALTER` / `GO TO` for file dispatch (lines 300-314) and loads transaction data into a fixed 2D in-memory array (`WS-TRNX-TABLE` — 51 cards x 10 transactions = 510 slots). This hard-coded limit means:
- Accounts with more than 10 transactions per card will be truncated
- The 51-card limit restricts the number of cards per batch run
- The `ALTER` pattern makes the control flow difficult to follow and optimize

**Improvement:** Replace the `ALTER`/`GO TO` dispatch with `EVALUATE` or direct `PERFORM` calls. Consider processing statements one account at a time rather than loading everything into a fixed-size array, which would remove the artificial limits and reduce memory usage.

### 4.5 No Batch Commit / Checkpoint Logic
**Problem:** Neither `CBTRN02C` nor `CBACT04C` implement any checkpoint/restart logic. If either program abends midway through processing (e.g., at transaction 50,000 of 100,000), the entire job must be restarted from the beginning, re-processing all already-completed records.

**Improvement:** Implement periodic checkpointing — e.g., every N records, write the current position to a checkpoint file. On restart, read the checkpoint and resume from that point. This is standard practice for high-volume mainframe batch jobs.

### 4.6 Hardcoded Screen Element Mapping (`COMEN01C.cbl`, `COTRN00C.cbl`)
**Problem:** Menu options and transaction list rows are mapped to screen fields via large `EVALUATE` blocks with hardcoded field names (e.g., `OPTN001O` through `OPTN012O` in COMEN01C lines 274-301, and `SEL0001I` through `SEL0010I` in COTRN00C lines 149-181). This doesn't affect runtime performance directly but creates maintenance overhead and makes the code brittle.

**Improvement:** Use BMS array (OCCURS) definitions instead of individually named fields, allowing loop-based population and reducing the EVALUATE blocks to simple indexed MOVEs.

### 4.7 TCATBAL File Read-then-Write Pattern (`CBTRN02C.cbl`, lines 467-501)
**Problem:** For each transaction, the program reads the TCATBAL record, then either creates or updates it. The file is opened I-O with RANDOM access, but the READ + REWRITE pattern generates two I/O operations per transaction for the same key.

**Improvement:** If the daily transaction file is sorted by account + type + category, consecutive transactions for the same category could be accumulated in memory and written/rewritten once, similar to the improvement suggested in 4.2.
