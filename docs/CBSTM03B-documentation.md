# CBSTM03B — Statement Report Subroutine

## Overview

**Program ID:** CBSTM03B  
**Type:** Batch Subroutine  
**Original Language:** COBOL  
**Function:** Provides file I/O operations for the account statement program (CBSTM03A). Handles open, read, and close operations for transaction, cross-reference, customer, and account files.

In the COBOL version, this is a called subroutine (`CALL 'CBSTM03B' USING LK-M03B-AREA`). In the Python translation, it is implemented as the `StatementFileHandler` class.

## Program Structure

| Component | Description |
|-----------|-------------|
| `TrnxRecord` | Data class for transaction records (from COSTM01) |
| `XrefRecord` | Data class for cross-reference records (from CVACT03Y) |
| `CustomerRecord` | Data class for customer records (from CUSTREC) |
| `AccountRecord` | Data class for account records (from CVACT01Y) |
| `TrnxFileRepository` | Abstract interface for sequential transaction access |
| `XrefFileRepository` | Abstract interface for sequential xref access |
| `CustomerFileRepository` | Abstract interface for keyed customer access |
| `AccountFileRepository` | Abstract interface for keyed account access |
| `FileOperationResult` | Result object with return code and data |
| `StatementFileHandler` | Main class replacing the CBSTM03B subroutine |

## Program Flow

The `StatementFileHandler` manages four file types:

1. **TRNXFILE** (Transaction) — Sequential read
2. **XREFFILE** (Cross-reference) — Sequential read
3. **CUSTFILE** (Customer) — Keyed random read
4. **ACCTFILE** (Account) — Keyed random read

### Operations

| Method | COBOL Equivalent | Description |
|--------|------------------|-------------|
| `open_all()` | `M03B-OPEN` for all files | Initialize iterators for sequential files |
| `close_all()` | `M03B-CLOSE` for all files | Release iterators |
| `read_next_trnx()` | `TRNXFILE` + `M03B-READ` | Read next transaction sequentially |
| `read_next_xref()` | `XREFFILE` + `M03B-READ` | Read next xref sequentially |
| `read_customer_by_key(id)` | `CUSTFILE` + `M03B-READ-KEY` | Look up customer by ID |
| `read_account_by_key(id)` | `ACCTFILE` + `M03B-READ-KEY` | Look up account by ID |

## Return Codes

| Code | Constant | Meaning |
|------|----------|---------|
| `"00"` | `RC_OK` | Operation successful, data returned |
| `"10"` | `RC_EOF` | End of file reached (sequential reads) |
| `"12"` | `RC_ERROR` | Error (file not open, record not found) |

## Error Handling

- Reading before `open_all()` returns `RC_ERROR`
- Reading after `close_all()` returns `RC_ERROR`
- Sequential read past last record returns `RC_EOF`
- Keyed read with non-existent key returns `RC_ERROR`
- Customer and account keyed lookups work without explicit open (they use repository interfaces directly)

## Copybooks Used

| Copybook | Purpose |
|----------|---------|
| COSTM01 | Transaction record keyed by card+tran-id |
| CVACT03Y | Card cross-reference record (50 bytes) |
| CUSTREC | Customer record (500 bytes) |
| CVACT01Y | Account record (300 bytes) |
