# CBTRN02C (Batch) - Post Daily Transactions (Advanced)

## Overview

**Program ID:** CBTRN02C (Batch)
**Application:** CardDemo (AWS Mainframe Modernization)
**Type:** Batch COBOL Program
**Function:** Post records from the daily transaction file with validation, rejection handling, and balance tracking

CBTRN02C is the advanced batch transaction posting program. It reads daily
transaction records sequentially, validates each one (card cross-reference
lookup, account verification, credit limit check, expiration date check),
and either posts valid transactions to the main transaction file or writes
rejected transactions to a rejects file with a reason code. It also updates
account balances and transaction category balances.

This is the enhanced version of CBTRN01C, adding:
- Transaction validation (credit limit, expiration date)
- Rejected transaction handling with reason codes
- Transaction category balance tracking (create or update)
- Account balance updates (current balance, cycle credits/debits)
- Writing posted transactions to the main transaction file
- Processing timestamp generation
- Transaction and rejection counters

---

## Program Structure

### Division Layout

| Division | Purpose |
|---|---|
| Identification | Declares program name (`CBTRN02C`) and author (`AWS`) |
| Environment | File-Control for six files |
| Data | File Section FDs, Working-Storage with copybook includes |
| Procedure | Main processing loop, validation, posting, and file I/O |

### Key Copybooks Used

| Copybook | Purpose |
|---|---|
| `CVTRA06Y` | Daily transaction record layout (DALYTRAN-RECORD, 350 bytes) |
| `CVTRA05Y` | Transaction record layout (TRAN-RECORD, 350 bytes) |
| `CVACT03Y` | Card cross-reference record layout (CARD-XREF-RECORD, 50 bytes) |
| `CVACT01Y` | Account record layout (ACCOUNT-RECORD, 300 bytes) |
| `CVTRA01Y` | Transaction category balance record (TRAN-CAT-BAL-RECORD, 50 bytes) |

### Files Accessed

| Logical Name | Access Mode | Purpose |
|---|---|---|
| DALYTRAN-FILE | Sequential Input | Daily transaction records to process |
| TRANSACT-FILE | Output | Main transaction file (write posted transactions) |
| XREF-FILE | Random Input | Card cross-reference (indexed by card number) |
| DALYREJS-FILE | Sequential Output | Rejected transactions with reason codes |
| ACCOUNT-FILE | I-O (Random) | Account master (read and rewrite balances) |
| TCATBAL-FILE | I-O (Random) | Transaction category balances (read, write, rewrite) |

---

## Program Flow

```
MAIN-PARA
  |
  |-- Open all six files
  |
  |-- PERFORM UNTIL END-OF-FILE = 'Y'
  |     |-- 1000-DALYTRAN-GET-NEXT (read next daily transaction)
  |     |-- IF not EOF:
  |     |     |-- Increment transaction count
  |     |     |-- 1500-VALIDATE-TRAN
  |     |     |     |-- 1500-A-LOOKUP-XREF (verify card number)
  |     |     |     |-- IF valid: 1500-B-LOOKUP-ACCT
  |     |     |     |     |-- Verify account exists
  |     |     |     |     |-- Check credit limit (overlimit check)
  |     |     |     |     |-- Check expiration date
  |     |     |-- IF validation passed (reason = 0):
  |     |     |     |-- 2000-POST-TRANSACTION
  |     |     |     |     |-- Copy daily tran fields to tran record
  |     |     |     |     |-- Generate processing timestamp
  |     |     |     |     |-- 2700-UPDATE-TCATBAL (update category balance)
  |     |     |     |     |-- 2800-UPDATE-ACCOUNT-REC (update account balance)
  |     |     |     |     |-- 2900-WRITE-TRANSACTION-FILE
  |     |     |-- ELSE:
  |     |     |     |-- Increment reject count
  |     |     |     |-- 2500-WRITE-REJECT-REC
  |
  |-- Close all six files
  |-- Display transaction and reject counts
  |-- If rejects > 0: set RETURN-CODE = 4
  |-- GOBACK
```

---

## Validation Rules

### 1500-A-LOOKUP-XREF
- Looks up the card number in the cross-reference file
- **Fail reason 100**: Card number not found (INVALID KEY)

### 1500-B-LOOKUP-ACCT
- Reads the account by the xref account ID
- **Fail reason 101**: Account record not found (INVALID KEY)
- **Fail reason 102**: Overlimit — `ACCT-CURR-CYC-CREDIT - ACCT-CURR-CYC-DEBIT + DALYTRAN-AMT` exceeds `ACCT-CREDIT-LIMIT`
- **Fail reason 103**: Transaction received after account expiration date

---

## Transaction Posting (2000-POST-TRANSACTION)

1. Copy all fields from daily transaction to main transaction record
2. Generate a DB2-format processing timestamp from current date/time
3. Update transaction category balance (2700-UPDATE-TCATBAL)
4. Update account balances (2800-UPDATE-ACCOUNT-REC)
5. Write the transaction record to the main file (2900-WRITE-TRANSACTION-FILE)

### Category Balance Update (2700-UPDATE-TCATBAL)
- Key: account ID + transaction type code + category code
- If record exists: add transaction amount to existing balance (REWRITE)
- If record not found: create new record with transaction amount (WRITE)

### Account Balance Update (2800-UPDATE-ACCOUNT-REC)
- Add transaction amount to ACCT-CURR-BAL
- If amount >= 0: add to ACCT-CURR-CYC-CREDIT
- If amount < 0: add to ACCT-CURR-CYC-DEBIT
- REWRITE the account record

---

## Rejection Handling

Rejected transactions are written to the DALYREJS file with:
- The original 350-byte transaction data
- An 80-byte validation trailer containing:
  - 4-digit fail reason code
  - 76-character fail reason description

### Rejection Reason Codes

| Code | Description |
|---|---|
| 100 | INVALID CARD NUMBER FOUND |
| 101 | ACCOUNT RECORD NOT FOUND |
| 102 | OVERLIMIT TRANSACTION |
| 103 | TRANSACTION RECEIVED AFTER ACCT EXPIRATION |

---

## Error Handling

- File I/O errors (other than expected conditions) cause the program to abend via `CEE3ABD` with code 999
- Reject count > 0 sets RETURN-CODE to 4 (warning)
- Transaction and rejection counts are displayed at program end
