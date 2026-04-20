# COCRDSLC - Credit Card View Program

## Overview

**Program ID:** COCRDSLC
**Application:** CardDemo (AWS Mainframe Modernization)
**Type:** CICS COBOL Online Program
**Transaction ID:** CCDL
**Function:** View credit card details (read-only)

COCRDSLC is an interactive CICS program that displays credit card details
in read-only mode. It shows card information along with associated account
and customer data. The program can be invoked directly or via transfer
(XCTL) from the Credit Card List program (COCRDLIC).

---

## Program Structure

### Key Copybooks Used

| Copybook | Purpose |
|---|---|
| `COCOM01Y` | Communication area (COMMAREA) |
| `COCRDSL` | BMS map I/O areas for the Card Detail screen |
| `COTTL01Y` | Screen title constants |
| `CSDAT01Y` | Date/time formatting |
| `CSMSG01Y` | Common message constants |
| `CSMSG02Y` | Abend message variables |
| `CSUSR01Y` | Signed-on user data |
| `CVACT01Y` | Account record layout (300 bytes) |
| `CVACT02Y` | Card record layout (150 bytes) |
| `CVACT03Y` | Card cross-reference record (50 bytes) |
| `CVCUS01Y` | Customer record layout (500 bytes) |
| `CVCRD01Y` | Card work area |
| `CSSTRPFY` | PF key storage/mapping |

### VSAM Files Accessed

| Logical Name | Purpose |
|---|---|
| CARDDAT | Card master file (read) |
| CARDAIX | Card file alternate index by account (read) |
| ACCTDAT | Account master file (read) |
| CUSTDAT | Customer master file (read) |
| CXACAIX | Card cross-reference by account (read) |

---

## Program Flow

```
0000-MAIN
  |
  |-- PF3 --> XCTL to calling program or main menu
  |
  |-- From COCRDLIC (card list):
  |     |-- Account ID and Card Number already set
  |     |-- 9000-READ-DATA (fetch card, account, customer)
  |     |-- 1000-SEND-MAP (display details)
  |
  |-- Direct entry:
  |     |-- 1000-SEND-MAP (prompt for account ID / card number)
  |
  |-- Re-entry:
        |-- 2000-PROCESS-INPUTS
        |     |-- 2100-RECEIVE-MAP
        |     |-- 2200-EDIT-MAP-INPUTS
        |           |-- 2210-EDIT-ACCOUNT (validate account ID)
        |           |-- 2220-EDIT-CARD (validate card number)
        |
        |-- 9000-READ-DATA
        |     |-- 9100-GETCARD-BYACCTCARD (read by card number)
        |     |-- 9150-GETCARD-BYACCT (read by account, alternate)
        |
        |-- 1000-SEND-MAP (display results)
```

---

## Input Fields

| Field | Validation |
|---|---|
| Account ID | Must be 11-digit numeric, non-zero (required if no card number) |
| Card Number | Must be 16-digit numeric, non-zero (required if no account ID) |

At least one of Account ID or Card Number must be provided.

---

## Output Fields

### Card Information
- Card Number
- Embossed Name
- Expiration Date (Month/Year)
- Active Status

### Account Information (from ACCTDAT via CARDXREF)
- Account ID
- Account Status
- Current Balance
- Credit Limit

### Customer Information (from CUSTDAT via CARDXREF)
- Customer ID
- Customer Name
- Address

---

## Business Rules

1. **At least one search key required** — either account ID or card number must be provided.
2. **Card lookup by card number** — primary lookup uses the card number as KSDS key.
3. **Card lookup by account** — alternate lookup uses account ID via CARDAIX alternate index.
4. **Cross-reference lookup** — account and customer data retrieved via CARDXREF.
5. **Read-only display** — no data modification is performed.
6. **Protected fields when from list** — when invoked from COCRDLIC, the search fields are display-only (protected).
7. **Editable fields on direct entry** — when entered directly, search fields are editable.

---

## Error Messages

| Condition | Message |
|---|---|
| Account ID not provided | "Account ID not provided" |
| Account ID non-numeric | "Account filter, if supplied must be a 11 digit number" |
| Card number not provided | "Card number not provided" |
| Card number non-numeric | "Card ID filter, if supplied must be a 16 digit number" |
| Neither provided | "Please provide account ID and/or card number" |
| Not in xref | "Did not find account in card xref file" |
| Card not found | "Did not find acct+card combination in card file" |

---

## Screen Navigation

| Key | Action |
|---|---|
| Enter | Submit search criteria |
| PF3 | Return to calling program or main menu |
