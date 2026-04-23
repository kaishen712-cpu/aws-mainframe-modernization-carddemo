# COTRN00C - Transaction List Program

## Overview

**Program ID:** COTRN00C  
**Application:** CardDemo (AWS Mainframe Modernization)  
**Type:** CICS COBOL Online Program  
**Transaction ID:** CT00  
**Function:** List transactions from the TRANSACT file with paginated browsing  

COTRN00C is an interactive CICS program that displays a paginated list of credit
card transactions from the TRANSACT VSAM file. Users can scroll forward and
backward through the list using PF7/PF8, optionally filter by a starting
transaction ID, and select a transaction to view its details (transferring
control to COTRN01C). The program is part of the CardDemo credit card management
system.

---

## Program Structure

### Division Layout

| Division | Purpose |
|---|---|
| Identification | Declares program name (`COTRN00C`) and author (`AWS`) |
| Environment | Configuration section (no special environment settings) |
| Data | Working-Storage variables, copybook includes, Linkage Section |
| Procedure | All business logic paragraphs |

### Key Copybooks Used

| Copybook | Purpose |
|---|---|
| `COCOM01Y` | Communication area (COMMAREA) shared across CardDemo programs |
| `COTRN00` | BMS map I/O areas for the Transaction List screen (COTRN0AI / COTRN0AO) |
| `COTTL01Y` | Screen title constants |
| `CSDAT01Y` | Date/time formatting working storage |
| `CSMSG01Y` | Common message constants (e.g., invalid key message) |
| `CVTRA05Y` | Transaction record layout (TRAN-RECORD, 350 bytes) |
| `DFHAID` | CICS attention identifier constants (Enter, PF keys) |
| `DFHBMSCA` | BMS attribute constants |

### VSAM Files Accessed

| Logical Name | Variable | Purpose |
|---|---|---|
| TRANSACT | `WS-TRANSACT-FILE` | Transaction master file (browse) |

---

## Program Flow

```
MAIN-PARA
  |
  |-- If no COMMAREA (EIBCALEN = 0) --> return to sign-on screen (COSGN00C)
  |
  |-- First entry (PGM-ENTER):
  |     |-- Initialize screen to LOW-VALUES
  |     |-- PROCESS-ENTER-KEY (load first page)
  |     |-- SEND-TRNLST-SCREEN
  |
  |-- Re-entry (PGM-REENTER):
        |-- RECEIVE-TRNLST-SCREEN
        |-- Evaluate key pressed:
              |-- ENTER  --> PROCESS-ENTER-KEY
              |-- PF3    --> RETURN-TO-PREV-SCREEN (COMEN01C)
              |-- PF7    --> PROCESS-PF7-KEY (page backward)
              |-- PF8    --> PROCESS-PF8-KEY (page forward)
              |-- Other  --> Display "Invalid key" message
```

### PROCESS-ENTER-KEY

1. Check if a transaction row was selected (SEL0001I through SEL0010I)
2. If selected with 'S' or 's', transfer to COTRN01C (View Transaction)
3. If invalid selection value, display error
4. If a starting transaction ID filter is provided, validate it is numeric
5. Reset page number and load the first page forward

### PROCESS-PAGE-FORWARD

1. Start browse at the current position (STARTBR)
2. Skip current record if not on Enter/PF7/PF3
3. Initialize 10 display slots
4. Read up to 10 records forward (READNEXT)
5. Populate display fields: transaction ID, date, description, amount
6. Check if there are more records (peek one ahead)
7. Update page number and next-page flag
8. End browse and send screen

### PROCESS-PAGE-BACKWARD

1. Start browse at the first transaction ID of the current page
2. Skip current record if not on Enter/PF8
3. Initialize 10 display slots
4. Read up to 10 records backward (READPREV), filling slots 10 down to 1
5. Update page number
6. End browse and send screen

### POPULATE-TRAN-DATA

For each transaction record read, maps the following to the corresponding
display slot (1–10):
- Transaction ID
- Origination date (formatted as MM/DD/YY)
- Description (truncated to display width)
- Amount (formatted as +99999999.99)

---

## Display Fields

Each page shows up to 10 transaction rows. Each row displays:

| Column | Source | Description |
|---|---|---|
| Selection | SEL00xxI | User types 'S' to select |
| Tran ID | TRAN-ID | 16-character transaction identifier |
| Date | TRAN-ORIG-TS | Formatted as MM/DD/YY |
| Description | TRAN-DESC | Transaction description |
| Amount | TRAN-AMT | Formatted as +99999999.99 |

### Filter Field

| Field | Description |
|---|---|
| TRNIDINI | Optional starting transaction ID filter (must be numeric) |

---

## Pagination State

The program maintains pagination state in the COMMAREA:

| Field | Purpose |
|---|---|
| CDEMO-CT00-TRNID-FIRST | Transaction ID of the first record on current page |
| CDEMO-CT00-TRNID-LAST | Transaction ID of the last record on current page |
| CDEMO-CT00-PAGE-NUM | Current page number |
| CDEMO-CT00-NEXT-PAGE-FLG | 'Y' if more pages exist forward |
| CDEMO-CT00-TRN-SEL-FLG | Selection flag from the selected row |
| CDEMO-CT00-TRN-SELECTED | Transaction ID of the selected row |

---

## Screen Navigation

| Key | Action |
|---|---|
| Enter | Validate filter / selection, reload page from beginning or transfer to view |
| PF3 | Return to previous screen (main menu — COMEN01C) |
| PF7 | Page backward (previous 10 transactions) |
| PF8 | Page forward (next 10 transactions) |
| Any other | Display "Invalid key pressed" message |

---

## Business Rules

### 1. Authentication / Session Check
- If no COMMAREA is passed (EIBCALEN = 0), the program redirects to the
  sign-on screen (`COSGN00C`).

### 2. Transaction ID Filter
- If a starting transaction ID is entered, it must be numeric.
- Non-numeric values produce the error: `"Tran ID must be Numeric ..."`

### 3. Selection Validation
- Only 'S' or 's' is a valid selection value.
- Any other non-blank value produces: `"Invalid selection. Valid value is S"`

### 4. Page Boundaries
- At the top of the list, PF7 shows: `"You are already at the top of the page..."`
- At the bottom of the list, PF8 shows: `"You are already at the bottom of the page..."`

---

## Error Handling

- VSAM browse errors display specific messages:
  - `"You are at the top of the page..."` (STARTBR NOTFND)
  - `"You have reached the bottom of the page..."` (READNEXT ENDFILE)
  - `"You have reached the top of the page..."` (READPREV ENDFILE)
  - `"Unable to lookup transaction..."` (other I/O errors)
- Validation errors set the error flag and position the cursor at the
  transaction ID input field.
- All errors are displayed in the `ERRMSGO` field of the output map.
