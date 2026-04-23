# COBIL00C - Bill Payment Program

## Overview

**Program ID:** COBIL00C  
**Application:** CardDemo (AWS Mainframe Modernization)  
**Type:** CICS COBOL Online Program  
**Transaction ID:** CB00  
**Function:** Pay account balance (full payment) and create a payment transaction  

COBIL00C is an interactive CICS program that allows users to make a bill payment
against their credit card account. It looks up the account by account ID,
displays the current balance, and upon confirmation writes a payment transaction
to the TRANSACT file and updates the account balance in the ACCTDAT file. The
program is part of the CardDemo credit card management system.

---

## Program Structure

### Division Layout

| Division | Purpose |
|---|---|
| Identification | Declares program name (`COBIL00C`) and author (`AWS`) |
| Environment | Configuration section (no special environment settings) |
| Data | Working-Storage variables, copybook includes, Linkage Section |
| Procedure | All business logic paragraphs |

### Key Copybooks Used

| Copybook | Purpose |
|---|---|
| `COCOM01Y` | Communication area (COMMAREA) shared across CardDemo programs |
| `COBIL00` | BMS map I/O areas for the Bill Payment screen (COBIL0AI / COBIL0AO) |
| `COTTL01Y` | Screen title constants |
| `CSDAT01Y` | Date/time formatting working storage |
| `CSMSG01Y` | Common message constants (e.g., invalid key message) |
| `CVACT01Y` | Account record layout (ACCOUNT-RECORD, 300 bytes) |
| `CVACT03Y` | Card cross-reference record layout (CARD-XREF-RECORD, 50 bytes) |
| `CVTRA05Y` | Transaction record layout (TRAN-RECORD, 350 bytes) |
| `DFHAID` | CICS attention identifier constants (Enter, PF keys) |
| `DFHBMSCA` | BMS attribute constants |

### VSAM Files Accessed

| Logical Name | Variable | Purpose |
|---|---|---|
| TRANSACT | `WS-TRANSACT-FILE` | Transaction master file (write new payment) |
| ACCTDAT | `WS-ACCTDAT-FILE` | Account data file (read/update balance) |
| CXACAIX | `WS-CXACAIX-FILE` | Account-to-card alternate index (resolve card number) |

---

## Program Flow

```
MAIN-PARA
  |
  |-- If no COMMAREA (EIBCALEN = 0) --> return to sign-on screen (COSGN00C)
  |
  |-- First entry (PGM-ENTER):
  |     |-- Initialize screen to LOW-VALUES
  |     |-- If account was pre-selected, populate and PROCESS-ENTER-KEY
  |     |-- SEND-BILLPAY-SCREEN
  |
  |-- Re-entry (PGM-REENTER):
        |-- RECEIVE-BILLPAY-SCREEN
        |-- Evaluate key pressed:
              |-- ENTER  --> PROCESS-ENTER-KEY
              |-- PF3    --> RETURN-TO-PREV-SCREEN
              |-- PF4    --> CLEAR-CURRENT-SCREEN
              |-- Other  --> Display "Invalid key" message
```

### PROCESS-ENTER-KEY

1. Validate that account ID is not empty
2. Check confirmation flag:
   - `Y`/`y` → set confirmed, read account
   - `N`/`n` → clear screen, set error (cancel)
   - Blank → read account (show balance, prompt for confirmation)
   - Other → display "Invalid value" error
3. Read account from ACCTDAT file
4. Display current balance
5. If balance is zero or negative, display "You have nothing to pay..."
6. If confirmed:
   a. Look up card number from CXACAIX cross-reference
   b. Generate next transaction ID (browse to end of TRANSACT, read last, add 1)
   c. Create payment transaction record with:
      - Type: '02', Category: 2, Source: 'POS TERM'
      - Description: 'BILL PAYMENT - ONLINE'
      - Amount: current balance
      - Merchant: ID 999999999, Name 'BILL PAYMENT', City/Zip 'N/A'
   d. Write transaction to TRANSACT file
   e. Update account balance (subtract payment amount)
   f. Display success message with transaction ID

---

## Input Fields

| Screen Field | COBOL Field | Description |
|---|---|---|
| Account ID | ACTIDINI | Credit card account identifier (required) |
| Current Balance | CURBALI | Display-only: current account balance |
| Confirm | CONFIRMI | Confirmation flag (Y/N) |

---

## Business Rules

### 1. Authentication / Session Check
- If no COMMAREA is passed (EIBCALEN = 0), the program redirects to the
  sign-on screen (`COSGN00C`).

### 2. Account ID Required
- Account ID cannot be empty: `"Acct ID can NOT be empty..."`

### 3. Account Validation
- Account must exist in ACCTDAT: `"Account ID NOT found..."`

### 4. Balance Check
- If current balance is zero or negative: `"You have nothing to pay..."`

### 5. Confirmation Workflow
- `Y`/`y`: Proceed with payment
- `N`/`n`: Cancel and clear screen
- Blank: Display balance and prompt for confirmation
- Other: `"Invalid value. Valid values are (Y/N)..."`

### 6. Payment Processing
- Payment amount equals the full current balance (ACCT-CURR-BAL)
- A new transaction record is created in the TRANSACT file
- Account balance is reduced by the payment amount
- Transaction ID is auto-generated (max existing + 1)

### 7. Transaction Record Fields
| Field | Value |
|---|---|
| TRAN-TYPE-CD | '02' |
| TRAN-CAT-CD | 2 |
| TRAN-SOURCE | 'POS TERM' |
| TRAN-DESC | 'BILL PAYMENT - ONLINE' |
| TRAN-AMT | Current balance |
| TRAN-MERCHANT-ID | 999999999 |
| TRAN-MERCHANT-NAME | 'BILL PAYMENT' |
| TRAN-MERCHANT-CITY | 'N/A' |
| TRAN-MERCHANT-ZIP | 'N/A' |

---

## Screen Navigation

| Key | Action |
|---|---|
| Enter | Validate account, display balance, or process payment |
| PF3 | Return to previous screen |
| PF4 | Clear all fields |
| Any other | Display "Invalid key pressed" message |

---

## Error Handling

- `"Acct ID can NOT be empty..."` — blank account ID
- `"Account ID NOT found..."` — account not in ACCTDAT or CXACAIX
- `"You have nothing to pay..."` — balance is zero or negative
- `"Invalid value. Valid values are (Y/N)..."` — bad confirmation input
- `"Tran ID already exist..."` — duplicate transaction ID (DUPKEY/DUPREC)
- `"Unable to Add Bill pay Transaction..."` — other write error
- `"Unable to Update Account..."` — account update error
- `"Payment successful. Your Transaction ID is <ID>."` — success message
