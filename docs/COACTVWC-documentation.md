# COACTVWC - Account View Program

## Overview

**Program ID:** COACTVWC
**Application:** CardDemo (AWS Mainframe Modernization)
**Type:** CICS COBOL Online Program
**Transaction ID:** CAVW
**Function:** Display account details in read-only mode

COACTVWC is an interactive CICS program that allows users to view account
details by entering an account ID. It looks up the account in the card
cross-reference file, retrieves the account master record, and fetches
associated customer information to display a comprehensive account view.

---

## Program Structure

### Key Copybooks Used

| Copybook | Purpose |
|---|---|
| `COCOM01Y` | Communication area (COMMAREA) shared across CardDemo programs |
| `COACTVW` | BMS map I/O areas for the Account View screen |
| `COTTL01Y` | Screen title constants |
| `CSDAT01Y` | Date/time formatting working storage |
| `CSMSG01Y` | Common message constants |
| `CSMSG02Y` | Abend message variables |
| `CSUSR01Y` | Signed-on user data |
| `CVACT01Y` | Account record layout (300 bytes) |
| `CVACT02Y` | Card record layout (150 bytes) |
| `CVACT03Y` | Card cross-reference record layout (50 bytes) |
| `CVCUS01Y` | Customer record layout (500 bytes) |
| `CSSTRPFY` | PF key storage/mapping utility |

### VSAM Files Accessed

| Logical Name | Purpose |
|---|---|
| ACCTDAT | Account master file (read) |
| CUSTDAT | Customer master file (read) |
| CXACAIX | Card cross-reference by account ID (alternate index, read) |

---

## Program Flow

```
0000-MAIN
  |
  |-- If PF3 pressed --> XCTL to calling program or main menu
  |
  |-- First entry (PGM-ENTER):
  |     |-- 1000-SEND-MAP (display empty form with prompt)
  |
  |-- Re-entry (PGM-REENTER):
        |-- 2000-PROCESS-INPUTS
        |     |-- 2100-RECEIVE-MAP (get screen input)
        |     |-- 2200-EDIT-MAP-INPUTS
        |           |-- 2210-EDIT-ACCOUNT (validate account ID)
        |-- If INPUT-ERROR --> 1000-SEND-MAP with error
        |-- Else:
              |-- 9000-READ-ACCT
              |     |-- 9200-GETCARDXREF-BYACCT (look up cross-ref)
              |     |-- 9300-GETACCTDATA-BYACCT (read account master)
              |     |-- 9400-GETCUSTDATA-BYCUST (read customer master)
              |-- 1000-SEND-MAP (display data)
```

---

## Input Fields

| Screen Field | Description | Validation |
|---|---|---|
| Account ID | 11-digit account identifier | Must be numeric, non-zero, must exist in cross-reference file |

---

## Output Fields

The program displays the following data when an account is found:

### Account Information
- Active Status, Current Balance, Credit Limit, Cash Credit Limit
- Current Cycle Credit, Current Cycle Debit
- Open Date, Expiration Date, Reissue Date
- Group ID

### Customer Information
- Customer ID, SSN (formatted as XXX-XX-XXXX), FICO Score, Date of Birth
- First Name, Middle Name, Last Name
- Address (Line 1, Line 2, City, State, Zip, Country)
- Phone Numbers (1 and 2)
- Government Issued ID, EFT Account ID
- Primary Card Holder Indicator

---

## Business Rules

1. **Account ID is required** - must be provided, must be numeric, must be non-zero.
2. **Cross-reference lookup** - Account ID is used to look up the card cross-reference file (CXACAIX) to find associated customer ID and card number.
3. **Account master lookup** - Account ID is used to read the account master file (ACCTDAT).
4. **Customer master lookup** - Customer ID (from cross-reference) is used to read the customer master file (CUSTDAT).
5. **Read-only** - No data modification is performed. This is purely a view operation.
6. **SSN formatting** - Customer SSN is displayed formatted as XXX-XX-XXXX.

---

## Error Messages

| Condition | Message |
|---|---|
| No account ID entered | "Account number not provided" |
| Account ID not numeric/zero | "Account Filter must be a non-zero 11 digit number" |
| No input received | "No input received" |
| Account not in cross-reference | "Account: XXX not found in Cross ref file" |
| Account not in master file | "Account: XXX not found in Acct Master file" |
| Customer not in master file | "CustId: XXX not found in customer master" |

---

## Screen Navigation

| Key | Action |
|---|---|
| Enter | Submit account ID and display details |
| PF3 | Return to calling program or main menu |
| Any other | Treated as Enter |
