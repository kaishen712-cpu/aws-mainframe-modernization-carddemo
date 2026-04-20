# CBTRN01C - Post Daily Transactions (Simple)

## Overview

**Program ID:** CBTRN01C
**Application:** CardDemo (AWS Mainframe Modernization)
**Type:** Batch COBOL Program
**Function:** Post records from the daily transaction file to the main transaction file

CBTRN01C is a simple batch program that reads daily transaction records sequentially
and posts them by looking up the associated account via the card cross-reference file.
For each transaction, it verifies the card number against the cross-reference file,
then reads the corresponding account record. This is the simpler version of the
transaction posting process (compare with CBTRN02C which adds validation, rejection
handling, and category balance tracking).

---

## Program Structure

### Division Layout

| Division | Purpose |
|---|---|
| Identification | Declares program name (`CBTRN01C`) and author (`AWS`) |
| Environment | File-Control for six files (sequential and indexed) |
| Data | File Section FDs, Working-Storage with copybook includes |
| Procedure | Main processing loop and file I/O paragraphs |

### Key Copybooks Used

| Copybook | Purpose |
|---|---|
| `CVTRA06Y` | Daily transaction record layout (DALYTRAN-RECORD, 350 bytes) |
| `CVCUS01Y` | Customer record layout (CUSTOMER-RECORD, 500 bytes) |
| `CVACT03Y` | Card cross-reference record layout (CARD-XREF-RECORD, 50 bytes) |
| `CVACT02Y` | Card record layout (CARD-RECORD, 150 bytes) |
| `CVACT01Y` | Account record layout (ACCOUNT-RECORD, 300 bytes) |
| `CVTRA05Y` | Transaction record layout (TRAN-RECORD, 350 bytes) |

### Files Accessed

| Logical Name | Access Mode | Purpose |
|---|---|---|
| DALYTRAN-FILE | Sequential Input | Daily transaction records to process |
| CUSTOMER-FILE | Random Input | Customer master file (indexed by customer ID) |
| XREF-FILE | Random Input | Card-to-account cross-reference (indexed by card number) |
| CARD-FILE | Random Input | Card master file (indexed by card number) |
| ACCOUNT-FILE | Random Input | Account master file (indexed by account ID) |
| TRANSACT-FILE | Random Input | Transaction master file (indexed by transaction ID) |

---

## Program Flow

```
MAIN-PARA
  |
  |-- Open all six files
  |
  |-- PERFORM UNTIL END-OF-DAILY-TRANS-FILE = 'Y'
  |     |-- 1000-DALYTRAN-GET-NEXT (read next daily transaction)
  |     |-- IF not EOF:
  |     |     |-- DISPLAY the daily transaction record
  |     |     |-- 2000-LOOKUP-XREF (look up card in cross-reference)
  |     |     |-- IF xref found:
  |     |     |     |-- 3000-READ-ACCOUNT (read account by xref account ID)
  |     |     |     |-- IF account not found: DISPLAY error
  |     |     |-- ELSE: DISPLAY card verification error, skip transaction
  |
  |-- Close all six files
  |-- DISPLAY end message
  |-- GOBACK
```

### 1000-DALYTRAN-GET-NEXT
- Reads the next sequential record from the daily transaction file
- Status '00' = success, '10' = end-of-file, other = error (abend)

### 2000-LOOKUP-XREF
- Looks up the card number from the daily transaction in the cross-reference file
- INVALID KEY: sets WS-XREF-READ-STATUS to 4 (card not found)
- NOT INVALID KEY: displays successful lookup with card, account, and customer IDs

### 3000-READ-ACCOUNT
- Reads the account record using the account ID from the cross-reference
- INVALID KEY: sets WS-ACCT-READ-STATUS to 4 (account not found)
- NOT INVALID KEY: displays success message

---

## Data Structures

### Daily Transaction Record (CVTRA06Y - 350 bytes)

| Field | PIC | Length | Description |
|---|---|---|---|
| DALYTRAN-ID | X(16) | 16 | Transaction identifier |
| DALYTRAN-TYPE-CD | X(02) | 2 | Transaction type code |
| DALYTRAN-CAT-CD | 9(04) | 4 | Transaction category code |
| DALYTRAN-SOURCE | X(10) | 10 | Transaction source |
| DALYTRAN-DESC | X(100) | 100 | Transaction description |
| DALYTRAN-AMT | S9(09)V99 | 11 | Transaction amount (signed decimal) |
| DALYTRAN-MERCHANT-ID | 9(09) | 9 | Merchant identifier |
| DALYTRAN-MERCHANT-NAME | X(50) | 50 | Merchant name |
| DALYTRAN-MERCHANT-CITY | X(50) | 50 | Merchant city |
| DALYTRAN-MERCHANT-ZIP | X(10) | 10 | Merchant zip code |
| DALYTRAN-CARD-NUM | X(16) | 16 | Card number |
| DALYTRAN-ORIG-TS | X(26) | 26 | Origination timestamp |
| DALYTRAN-PROC-TS | X(26) | 26 | Processing timestamp |
| FILLER | X(20) | 20 | Unused padding |

### Card Cross-Reference Record (CVACT03Y - 50 bytes)

| Field | PIC | Length | Description |
|---|---|---|---|
| XREF-CARD-NUM | X(16) | 16 | Card number (primary key) |
| XREF-CUST-ID | 9(09) | 9 | Customer identifier |
| XREF-ACCT-ID | 9(11) | 11 | Account identifier |
| FILLER | X(14) | 14 | Unused padding |

### Account Record (CVACT01Y - 300 bytes)

| Field | PIC | Length | Description |
|---|---|---|---|
| ACCT-ID | 9(11) | 11 | Account identifier |
| ACCT-ACTIVE-STATUS | X(01) | 1 | Active status flag |
| ACCT-CURR-BAL | S9(10)V99 | 12 | Current balance |
| ACCT-CREDIT-LIMIT | S9(10)V99 | 12 | Credit limit |
| ACCT-CASH-CREDIT-LIMIT | S9(10)V99 | 12 | Cash credit limit |
| ACCT-OPEN-DATE | X(10) | 10 | Account open date |
| ACCT-EXPIRAION-DATE | X(10) | 10 | Account expiration date |
| ACCT-REISSUE-DATE | X(10) | 10 | Card reissue date |
| ACCT-CURR-CYC-CREDIT | S9(10)V99 | 12 | Current cycle credits |
| ACCT-CURR-CYC-DEBIT | S9(10)V99 | 12 | Current cycle debits |
| ACCT-ADDR-ZIP | X(10) | 10 | Account address zip code |
| ACCT-GROUP-ID | X(10) | 10 | Disclosure group identifier |
| FILLER | X(178) | 178 | Unused padding |

---

## Business Rules

1. **Sequential Processing**: Daily transactions are read one at a time from a sequential file.
2. **Card Verification**: Each transaction's card number is verified against the cross-reference file.
3. **Account Lookup**: If the card is valid, the corresponding account is read using the account ID from the cross-reference.
4. **Error Reporting**: Invalid cards and missing accounts are reported via DISPLAY statements but do not cause the program to abend.
5. **Fatal Errors**: File I/O errors (other than expected conditions like EOF or INVALID KEY) cause the program to abend with code 999.

---

## Error Handling

- **Card not in XREF**: Transaction is skipped with a DISPLAY message showing the card number and transaction ID.
- **Account not found**: A DISPLAY message shows the account ID that was not found.
- **File I/O errors**: Any unexpected file status causes the program to display the I/O status and abend via `CEE3ABD` with abend code 999.

---

## Limitations

This is the "simple" version of transaction posting. It does NOT:
- Write transactions to the main transaction file
- Update account balances
- Track transaction category balances
- Reject invalid transactions to a separate file
- Validate credit limits or expiration dates

These features are implemented in CBTRN02C (the advanced version).
