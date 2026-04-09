# COTRN01C - Transaction View Program

## Overview

**Program ID:** COTRN01C  
**Application:** CardDemo (AWS Mainframe Modernization)  
**Type:** CICS COBOL Online Program  
**Transaction ID:** CT01  
**Function:** View a single transaction's details (read-only)  

COTRN01C is an interactive CICS program that displays the full details of a
single credit card transaction. It reads a transaction by ID from the TRANSACT
VSAM file and displays all fields in a read-only format. The program is
typically invoked from the Transaction List screen (COTRN00C) when the user
selects a transaction to view.

---

## Program Structure

### Division Layout

| Division | Purpose |
|---|---|
| Identification | Declares program name (`COTRN01C`) and author (`AWS`) |
| Environment | Configuration section (no special environment settings) |
| Data | Working-Storage variables, copybook includes, Linkage Section |
| Procedure | All business logic paragraphs |

### Key Copybooks Used

| Copybook | Purpose |
|---|---|
| `COCOM01Y` | Communication area (COMMAREA) shared across CardDemo programs |
| `COTRN01` | BMS map I/O areas for the Transaction View screen (COTRN1AI / COTRN1AO) |
| `COTTL01Y` | Screen title constants |
| `CSDAT01Y` | Date/time formatting working storage |
| `CSMSG01Y` | Common message constants (e.g., invalid key message) |
| `CVTRA05Y` | Transaction record layout (TRAN-RECORD, 350 bytes) |
| `DFHAID` | CICS attention identifier constants (Enter, PF keys) |
| `DFHBMSCA` | BMS attribute constants |

### VSAM Files Accessed

| Logical Name | Variable | Purpose |
|---|---|---|
| TRANSACT | `WS-TRANSACT-FILE` | Transaction master file (read) |

---

## Program Flow

```
MAIN-PARA
  |
  |-- If no COMMAREA (EIBCALEN = 0) --> return to sign-on screen (COSGN00C)
  |
  |-- First entry (PGM-ENTER):
  |     |-- Initialize screen to LOW-VALUES
  |     |-- If a transaction was pre-selected, populate ID and PROCESS-ENTER-KEY
  |     |-- SEND-TRNVIEW-SCREEN
  |
  |-- Re-entry (PGM-REENTER):
        |-- RECEIVE-TRNVIEW-SCREEN
        |-- Evaluate key pressed:
              |-- ENTER  --> PROCESS-ENTER-KEY
              |-- PF3    --> RETURN-TO-PREV-SCREEN
              |-- PF4    --> CLEAR-CURRENT-SCREEN
              |-- PF5    --> Return to Transaction List (COTRN00C)
              |-- Other  --> Display "Invalid key" message
```

### PROCESS-ENTER-KEY

1. Validate that the transaction ID input is not empty
2. Clear all display fields
3. Read the transaction record from the TRANSACT file by ID
4. If found, populate all display fields with the transaction data
5. If not found, display error message

---

## Display Fields

| Screen Field | Source Field | Description |
|---|---|---|
| Tran ID (input) | TRNIDINI | Transaction ID entered by user |
| Tran ID | TRAN-ID | Transaction identifier (from record) |
| Card Number | TRAN-CARD-NUM | Associated card number |
| Type Code | TRAN-TYPE-CD | Transaction type code |
| Category Code | TRAN-CAT-CD | Transaction category code |
| Source | TRAN-SOURCE | Transaction source |
| Amount | TRAN-AMT | Formatted as +99999999.99 |
| Description | TRAN-DESC | Transaction description |
| Orig Date | TRAN-ORIG-TS | Origination timestamp |
| Proc Date | TRAN-PROC-TS | Processing timestamp |
| Merchant ID | TRAN-MERCHANT-ID | Merchant identifier |
| Merchant Name | TRAN-MERCHANT-NAME | Merchant business name |
| Merchant City | TRAN-MERCHANT-CITY | Merchant city |
| Merchant Zip | TRAN-MERCHANT-ZIP | Merchant zip code |

---

## Screen Navigation

| Key | Action |
|---|---|
| Enter | Look up and display the transaction by ID |
| PF3 | Return to previous screen (caller or main menu) |
| PF4 | Clear all fields on the screen |
| PF5 | Return to Transaction List (COTRN00C) |
| Any other | Display "Invalid key pressed" message |

---

## Business Rules

### 1. Authentication / Session Check
- If no COMMAREA is passed (EIBCALEN = 0), the program redirects to the
  sign-on screen (`COSGN00C`).

### 2. Transaction ID Required
- The transaction ID input field cannot be empty.
- Empty ID produces: `"Tran ID can NOT be empty..."`

### 3. Transaction Lookup
- The transaction is read from the TRANSACT file by its primary key (TRAN-ID).
- If not found: `"Transaction ID NOT found..."`
- If other I/O error: `"Unable to lookup Transaction..."`

### 4. Read-Only Display
- This program is view-only. No modifications are made to any data files.
- The amount field is formatted using PIC +99999999.99 for display.

---

## Error Handling

- `"Tran ID can NOT be empty..."` — when the ID input is blank
- `"Transaction ID NOT found..."` — when the VSAM READ returns NOTFND
- `"Unable to lookup Transaction..."` — when any other VSAM error occurs
- All errors are displayed in the `ERRMSGO` field of the output map.
