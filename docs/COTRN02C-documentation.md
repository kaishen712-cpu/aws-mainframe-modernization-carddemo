# COTRN02C - Add Transaction Program

## Overview

**Program ID:** COTRN02C  
**Application:** CardDemo (AWS Mainframe Modernization)  
**Type:** CICS COBOL Online Program  
**Transaction ID:** CT02  
**Function:** Add a new credit card transaction to the TRANSACT file  

COTRN02C is an interactive CICS program that allows users to enter and submit
new credit card transactions. It presents a BMS map-based screen where the user
fills in transaction details, validates every field against a comprehensive set
of business rules, and writes the new record to the VSAM TRANSACT file. The
program is part of the CardDemo credit card management system and is invoked
from the Transaction List screen (COTRN00C / CT00).

---

## Program Structure

### Division Layout

| Division | Purpose |
|---|---|
| Identification | Declares program name (`COTRN02C`) and author (`AWS`) |
| Environment | Configuration section (no special environment settings) |
| Data | Working-Storage variables, copybook includes, Linkage Section |
| Procedure | All business logic paragraphs |

### Key Copybooks Used

| Copybook | Purpose |
|---|---|
| `COCOM01Y` | Communication area (COMMAREA) shared across CardDemo programs |
| `COTRN02` | BMS map I/O areas for the Add Transaction screen (COTRN2AI / COTRN2AO) |
| `COTTL01Y` | Screen title constants |
| `CSDAT01Y` | Date/time formatting working storage |
| `CSMSG01Y` | Common message constants (e.g., invalid key message) |
| `CVTRA05Y` | Transaction record layout (TRAN-RECORD, 350 bytes) |
| `CVACT01Y` | Account record layout |
| `CVACT03Y` | Card cross-reference record layout (CARD-XREF-RECORD) |
| `DFHAID` | CICS attention identifier constants (Enter, PF keys) |
| `DFHBMSCA` | BMS attribute constants |

### VSAM Files Accessed

| Logical Name | Variable | Purpose |
|---|---|---|
| TRANSACT | `WS-TRANSACT-FILE` | Transaction master file (read/write) |
| ACCTDAT | `WS-ACCTDAT-FILE` | Account data file (declared but used indirectly) |
| CCXREF | `WS-CCXREF-FILE` | Card-to-account cross-reference (read by card number) |
| CXACAIX | `WS-CXACAIX-FILE` | Account-to-card alternate index (read by account ID) |

### External Program Called

| Program | Purpose |
|---|---|
| `CSUTLDTC` | Date validation utility; checks whether a date string is valid for a given format |

---

## Program Flow

```
MAIN-PARA
  |
  |-- If no COMMAREA (EIBCALEN = 0) --> return to sign-on screen (COSGN00C)
  |
  |-- First entry (PGM-ENTER):
  |     |-- Initialize screen to LOW-VALUES
  |     |-- If a card number was pre-selected, populate it and run PROCESS-ENTER-KEY
  |     |-- SEND-TRNADD-SCREEN
  |
  |-- Re-entry (PGM-REENTER):
        |-- RECEIVE-TRNADD-SCREEN
        |-- Evaluate key pressed:
              |-- ENTER  --> PROCESS-ENTER-KEY
              |-- PF3    --> RETURN-TO-PREV-SCREEN
              |-- PF4    --> CLEAR-CURRENT-SCREEN
              |-- PF5    --> COPY-LAST-TRAN-DATA
              |-- Other  --> Display "Invalid key" message
```

### PROCESS-ENTER-KEY

1. Validate key fields (account ID or card number)
2. Validate all data fields (type, category, source, description, amount, dates, merchant info)
3. Check confirmation flag:
   - `Y` / `y` --> `ADD-TRANSACTION`
   - `N` / `n` / blank --> prompt user to confirm
   - Other --> display "Invalid value" error

### ADD-TRANSACTION

1. Start browse at end of TRANSACT file (HIGH-VALUES key)
2. Read the last record to get the highest transaction ID
3. Increment the transaction ID by 1
4. Populate the new TRAN-RECORD with screen input fields
5. Write the record to the TRANSACT file
6. On success, clear the screen and display a success message with the new transaction ID

### COPY-LAST-TRAN-DATA (PF5)

1. Validate key fields first (account/card must be valid)
2. Browse to end of TRANSACT file and read the last transaction
3. Copy the last transaction's data fields into the screen input fields
4. Call PROCESS-ENTER-KEY to allow the user to review and confirm

---

## Input Fields

All input fields are received from the BMS map `COTRN2A` into the `COTRN2AI`
record structure.

| Screen Field | COBOL Field | Type | Length | Description |
|---|---|---|---|---|
| Account ID | `ACTIDINI` | Numeric | 11 | Credit card account identifier |
| Card Number | `CARDNINI` | Numeric | 16 | Credit card number |
| Type Code | `TTYPCDI` | Numeric | 2 | Transaction type code |
| Category Code | `TCATCDI` | Numeric | 4 | Transaction category code |
| Source | `TRNSRCI` | Alphanumeric | 10 | Transaction source identifier |
| Description | `TDESCI` | Alphanumeric | 60 | Free-text transaction description |
| Amount | `TRNAMTI` | Signed decimal | 12 | Transaction amount in format `+/-99999999.99` |
| Origination Date | `TORIGDTI` | Date | 10 | Date transaction originated (`YYYY-MM-DD`) |
| Processing Date | `TPROCDTI` | Date | 10 | Date transaction is processed (`YYYY-MM-DD`) |
| Merchant ID | `MIDI` | Numeric | 9 | Merchant identifier |
| Merchant Name | `MNAMEI` | Alphanumeric | 30 | Merchant business name |
| Merchant City | `MCITYI` | Alphanumeric | 25 | Merchant city |
| Merchant Zip | `MZIPI` | Alphanumeric | 10 | Merchant zip/postal code |
| Confirm | `CONFIRMI` | Character | 1 | Confirmation flag (`Y`/`N`) |

### Key Field Logic

The user must provide **either** an Account ID **or** a Card Number (not both
are required, but at least one must be supplied):

- If **Account ID** is provided, the program looks up the cross-reference file
  (`CXACAIX`) to find the associated card number.
- If **Card Number** is provided, the program looks up the cross-reference file
  (`CCXREF`) to find the associated account ID.

---

## Outputs

### Screen Output

The program sends the `COTRN2A` map back to the terminal, which includes:
- Header information: application title, transaction name, program name, current date and time
- All input fields (pre-populated or echoed back)
- An error/info message line (`ERRMSGO`)
- On success: a green message reading  
  `"Transaction added successfully. Your Tran ID is <ID>."`

### Data Output

A new record is written to the TRANSACT VSAM file with this layout:

| Field | PIC | Length | Source |
|---|---|---|---|
| `TRAN-ID` | X(16) | 16 | Auto-generated (previous max + 1) |
| `TRAN-TYPE-CD` | X(02) | 2 | Type Code input |
| `TRAN-CAT-CD` | 9(04) | 4 | Category Code input |
| `TRAN-SOURCE` | X(10) | 10 | Source input |
| `TRAN-DESC` | X(100) | 100 | Description input |
| `TRAN-AMT` | S9(09)V99 | 11 | Amount input (parsed via NUMVAL-C) |
| `TRAN-MERCHANT-ID` | 9(09) | 9 | Merchant ID input |
| `TRAN-MERCHANT-NAME` | X(50) | 50 | Merchant Name input |
| `TRAN-MERCHANT-CITY` | X(50) | 50 | Merchant City input |
| `TRAN-MERCHANT-ZIP` | X(10) | 10 | Merchant Zip input |
| `TRAN-CARD-NUM` | X(16) | 16 | Card Number (resolved) |
| `TRAN-ORIG-TS` | X(26) | 26 | Origination Date input |
| `TRAN-PROC-TS` | X(26) | 26 | Processing Date input |
| FILLER | X(20) | 20 | Unused padding |

**Total record length: 350 bytes**

---

## Business Rules

### 1. Authentication / Session Check
- If no COMMAREA is passed (EIBCALEN = 0), the program redirects to the
  sign-on screen (`COSGN00C`). This prevents unauthenticated access.

### 2. Key Field Validation
- **At least one** of Account ID or Card Number must be provided.
- Account ID must be numeric. If provided, it is used to look up the card
  number from the `CXACAIX` alternate index file.
- Card Number must be numeric. If provided, it is used to look up the account
  ID from the `CCXREF` cross-reference file.
- If the lookup fails (record not found), an error is displayed.

### 3. Required Data Fields
All of the following fields are mandatory (cannot be blank):
- Transaction Type Code
- Transaction Category Code
- Transaction Source
- Transaction Description
- Transaction Amount
- Origination Date
- Processing Date
- Merchant ID
- Merchant Name
- Merchant City
- Merchant Zip

### 4. Numeric Validation
- Type Code must be numeric (2-digit).
- Category Code must be numeric (4-digit).
- Merchant ID must be numeric (9-digit).

### 5. Amount Format Validation
- Must match the pattern `[+/-]99999999.99`
  - Position 1: sign character (`+` or `-`)
  - Positions 2-9: eight numeric digits
  - Position 10: decimal point (`.`)
  - Positions 11-12: two numeric digits
- The value is converted using `NUMVAL-C` and re-formatted for display.

### 6. Date Format Validation
- Both Origination Date and Processing Date must match `YYYY-MM-DD`:
  - Positions 1-4: numeric (year)
  - Position 5: hyphen
  - Positions 6-7: numeric (month)
  - Position 8: hyphen
  - Positions 9-10: numeric (day)
- After format validation, dates are validated for calendar correctness
  by calling the `CSUTLDTC` utility subroutine. If the result severity code
  is not `0000` and the message number is not `2513`, the date is rejected.

### 7. Transaction ID Generation
- The new transaction ID is generated by browsing to the end of the TRANSACT
  file, reading the last (highest) record, and adding 1 to its ID.
- If the file is empty (ENDFILE), the ID starts at 1 (from ZEROS + 1).

### 8. Duplicate Protection
- If the generated transaction ID already exists (DUPKEY / DUPREC response
  from the CICS WRITE), the program displays an error:
  `"Tran ID already exist..."`

### 9. Confirmation Workflow
- The user must type `Y` or `y` in the Confirm field and press Enter to
  actually write the transaction.
- `N`, `n`, blank, or LOW-VALUES prompt the user to confirm.
- Any other value is rejected as invalid.

### 10. Screen Navigation
| Key | Action |
|---|---|
| Enter | Validate and (if confirmed) add the transaction |
| PF3 | Return to the previous screen (or main menu) |
| PF4 | Clear all input fields on the screen |
| PF5 | Copy the last transaction's data into the current screen fields |
| Any other | Display "Invalid key pressed" message |

---

## Error Handling

- VSAM file I/O errors display specific messages:
  - `"Account ID NOT found..."` / `"Card Number NOT found..."`
  - `"Unable to lookup Acct in XREF AIX file..."`
  - `"Unable to lookup Card # in XREF file..."`
  - `"Transaction ID NOT found..."`
  - `"Unable to lookup Transaction..."`
  - `"Unable to Add Transaction..."`
  - `"Tran ID already exist..."`
- Validation errors set the error flag and position the cursor at the
  offending field via BMS cursor positioning (negative length value).
- All errors are displayed in the `ERRMSGO` field of the output map.
- The program uses `DISPLAY` statements for certain VSAM error codes
  (response/reason codes) for debugging purposes.
