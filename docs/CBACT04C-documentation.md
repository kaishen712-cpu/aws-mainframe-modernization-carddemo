# CBACT04C - Interest Calculation

## Overview

**Program ID:** CBACT04C
**Application:** CardDemo (AWS Mainframe Modernization)
**Type:** Batch COBOL Program
**Function:** Calculate interest charges on account balances

CBACT04C is a batch program that calculates monthly interest charges on
credit card account balances. It reads the transaction category balance file
sequentially, groups records by account, looks up the applicable interest
rate from the disclosure group file, computes monthly interest, creates
interest transaction records, and updates account balances.

---

## Program Structure

### Division Layout

| Division | Purpose |
|---|---|
| Identification | Declares program name (`CBACT04C`) and author (`AWS`) |
| Environment | File-Control for five files |
| Data | File Section FDs, Working-Storage with copybook includes, Linkage Section for PARM-DATE |
| Procedure | Main processing loop, interest calculation, and file I/O |

### Key Copybooks Used

| Copybook | Purpose |
|---|---|
| `CVTRA01Y` | Transaction category balance record (TRAN-CAT-BAL-RECORD, 50 bytes) |
| `CVACT03Y` | Card cross-reference record (CARD-XREF-RECORD, 50 bytes) |
| `CVTRA02Y` | Disclosure group record (DIS-GROUP-RECORD, 50 bytes) — interest rates |
| `CVACT01Y` | Account record (ACCOUNT-RECORD, 300 bytes) |
| `CVTRA05Y` | Transaction record (TRAN-RECORD, 350 bytes) |

### Files Accessed

| Logical Name | Access Mode | Purpose |
|---|---|---|
| TCATBAL-FILE | Sequential Input | Transaction category balances (sorted by account) |
| XREF-FILE | Random Input | Card cross-reference (read by alternate key: account ID) |
| DISCGRP-FILE | Random Input | Disclosure group (interest rates by group+type+category) |
| ACCOUNT-FILE | I-O (Random) | Account master (read and rewrite balances) |
| TRANSACT-FILE | Sequential Output | Transaction file (write interest transaction records) |

### External Parameters

| Parameter | Description |
|---|---|
| PARM-DATE | Processing date (PIC X(10), format YYYY-MM-DD), passed via JCL PARM |

---

## Program Flow

```
MAIN-PARA (PROCEDURE DIVISION USING EXTERNAL-PARMS)
  |
  |-- Open all five files
  |
  |-- PERFORM UNTIL END-OF-FILE = 'Y'
  |     |-- 1000-TCATBALF-GET-NEXT (read next category balance record)
  |     |-- IF not EOF:
  |     |     |-- Increment record count
  |     |     |-- IF new account (TRANCAT-ACCT-ID != WS-LAST-ACCT-NUM):
  |     |     |     |-- IF not first time: 1050-UPDATE-ACCOUNT (for previous account)
  |     |     |     |-- ELSE: set first-time flag to 'N'
  |     |     |     |-- Reset WS-TOTAL-INT to 0
  |     |     |     |-- Save current account as WS-LAST-ACCT-NUM
  |     |     |     |-- 1100-GET-ACCT-DATA (read account record)
  |     |     |     |-- 1110-GET-XREF-DATA (read xref by account ID)
  |     |     |-- Look up interest rate:
  |     |     |     |-- 1200-GET-INTEREST-RATE (by group-id + type + category)
  |     |     |     |-- If rate not found, try DEFAULT group
  |     |     |-- IF DIS-INT-RATE != 0:
  |     |     |     |-- 1300-COMPUTE-INTEREST
  |     |     |     |-- 1400-COMPUTE-FEES (stub — not implemented)
  |     |-- ELSE (EOF reached):
  |     |     |-- 1050-UPDATE-ACCOUNT (for the last account)
  |
  |-- Close all five files
  |-- GOBACK
```

---

## Key Processing Steps

### 1050-UPDATE-ACCOUNT
- Add total accumulated interest (WS-TOTAL-INT) to ACCT-CURR-BAL
- Reset ACCT-CURR-CYC-CREDIT to 0
- Reset ACCT-CURR-CYC-DEBIT to 0
- REWRITE the account record

### 1100-GET-ACCT-DATA
- Read account record by account ID from the account master file
- Abend on error

### 1110-GET-XREF-DATA
- Read cross-reference record by account ID (alternate key)
- This provides the card number needed for interest transaction records

### 1200-GET-INTEREST-RATE
- Build key from: ACCT-GROUP-ID + TRANCAT-TYPE-CD + TRANCAT-CD
- Read the disclosure group file
- If record not found (status '23'): try again with 'DEFAULT' as the group ID
- The interest rate is in DIS-INT-RATE (PIC S9(04)V99)

### 1300-COMPUTE-INTEREST
- **Formula**: `WS-MONTHLY-INT = (TRAN-CAT-BAL * DIS-INT-RATE) / 1200`
  - This divides the annual rate by 12 (months) and by 100 (percentage)
  - Equivalent to: `monthly_interest = balance * (annual_rate_pct / 100) / 12`
- Add WS-MONTHLY-INT to WS-TOTAL-INT (accumulated for the account)
- Write an interest transaction record (1300-B-WRITE-TX)

### 1300-B-WRITE-TX
- Generate transaction ID: `PARM-DATE + WS-TRANID-SUFFIX` (STRING concatenation)
  - WS-TRANID-SUFFIX is incremented for each interest transaction
- Set fixed fields:
  - TRAN-TYPE-CD = '01'
  - TRAN-CAT-CD = '05' (interest category, stored as 4-digit: '0005')
  - TRAN-SOURCE = 'System'
  - TRAN-DESC = 'Int. for a/c ' + ACCT-ID
  - TRAN-AMT = WS-MONTHLY-INT
  - TRAN-MERCHANT-ID = 0
  - TRAN-CARD-NUM = XREF-CARD-NUM
  - Timestamps from current date/time

### 1400-COMPUTE-FEES
- Stub paragraph — not yet implemented in the original COBOL

---

## Data Structures

### Disclosure Group Record (CVTRA02Y — 50 bytes)

| Field | PIC | Length | Description |
|---|---|---|---|
| DIS-ACCT-GROUP-ID | X(10) | 10 | Account group identifier |
| DIS-TRAN-TYPE-CD | X(02) | 2 | Transaction type code |
| DIS-TRAN-CAT-CD | 9(04) | 4 | Transaction category code |
| DIS-INT-RATE | S9(04)V99 | 6 | Annual interest rate (e.g., 18.50 = 18.50%) |
| FILLER | X(28) | 28 | Unused padding |

### Transaction Category Balance Record (CVTRA01Y — 50 bytes)

| Field | PIC | Length | Description |
|---|---|---|---|
| TRANCAT-ACCT-ID | 9(11) | 11 | Account identifier |
| TRANCAT-TYPE-CD | X(02) | 2 | Transaction type code |
| TRANCAT-CD | 9(04) | 4 | Transaction category code |
| TRAN-CAT-BAL | S9(09)V99 | 11 | Category balance |
| FILLER | X(22) | 22 | Unused padding |

---

## Interest Calculation Formula

```
monthly_interest = category_balance * (annual_interest_rate / 100) / 12
```

Or equivalently (as in the COBOL):

```
monthly_interest = (category_balance * annual_interest_rate) / 1200
```

Where `annual_interest_rate` is stored as a percentage (e.g., 18.50 means 18.50% per year).

---

## Error Handling

- File I/O errors cause the program to abend via `CEE3ABD` with code 999
- If a disclosure group record is not found for the account's group ID,
  the program falls back to a 'DEFAULT' group
- If the default group is also not found, the program abends
- If the interest rate is 0, no interest is computed for that category
