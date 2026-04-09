# COACTUPC - Account Update Program

## Overview

**Program ID:** COACTUPC
**Application:** CardDemo (AWS Mainframe Modernization)
**Type:** CICS COBOL Online Program
**Transaction ID:** CAUP
**Function:** Update account and customer details

COACTUPC is the largest program in the CardDemo application (4,236 lines).
It is an interactive CICS program that allows users to update account
details including status, credit limits, dates, and associated customer
information.  It implements a confirmation workflow requiring the user to
press PF5 to commit changes.

---

## Program Structure

### Key Copybooks Used

| Copybook | Purpose |
|---|---|
| `COCOM01Y` | Communication area (COMMAREA) |
| `COACTUP` | BMS map I/O areas for the Account Update screen |
| `COTTL01Y` | Screen title constants |
| `CSDAT01Y` | Date/time formatting |
| `CSMSG01Y` | Common message constants |
| `CSMSG02Y` | Abend message variables |
| `CSUSR01Y` | Signed-on user data |
| `CVACT01Y` | Account record layout (300 bytes) |
| `CVACT03Y` | Card cross-reference record (50 bytes) |
| `CVCUS01Y` | Customer record layout (500 bytes) |
| `CSSETATY` | Screen attribute setting (used 39 times with REPLACING) |
| `CSSTRPFY` | PF key storage/mapping |
| `CSUTLDPY` | Date validation procedures |
| `CSUTLDWY` | Date validation working storage |
| `CSLKPCDY` | North America phone area code lookup |

### VSAM Files Accessed

| Logical Name | Purpose |
|---|---|
| ACCTDAT | Account master file (read/update) |
| CUSTDAT | Customer master file (read/update) |
| CXACAIX | Card cross-reference by account (read) |

---

## Program Flow

```
0000-MAIN
  |
  |-- PF3 --> XCTL to calling program or main menu
  |
  |-- First entry (PGM-ENTER):
  |     |-- 1000-SEND-MAP (empty form, prompt for account ID)
  |
  |-- Re-entry (PGM-REENTER):
        |-- 2000-PROCESS-INPUTS
        |     |-- 2100-RECEIVE-MAP
        |     |-- 2200-EDIT-MAP-INPUTS
        |           |-- 2210-EDIT-ACCOUNT (validate ID)
        |           |-- 2250-EDIT-UPDATE-FIELDS (validate changes)
        |
        |-- If first fetch needed:
        |     |-- 9000-READ-ACCT (xref -> account -> customer)
        |     |-- Show details, prompt for edits
        |
        |-- If edits submitted:
        |     |-- Detect changes vs. old values
        |     |-- Validate each changed field
        |     |-- If valid: prompt for PF5 confirmation
        |     |-- If PF5 confirmed:
        |           |-- 9600-WRITE-PROCESSING
        |           |     |-- READ-UPDATE (lock record)
        |           |     |-- Verify no concurrent change
        |           |     |-- REWRITE account record
        |           |     |-- REWRITE customer record
        |           |-- Show success/failure message
```

---

## Updatable Fields

### Account Fields
| Field | Validation |
|---|---|
| Active Status | Must be 'Y' or 'N' |
| Credit Limit | Must be numeric |
| Cash Credit Limit | Must be numeric |
| Expiration Date | Must be valid date (YYYY-MM-DD) |
| Reissue Date | Must be valid date (YYYY-MM-DD) |
| Group ID | Alphanumeric |

### Customer Fields
| Field | Validation |
|---|---|
| First/Middle/Last Name | Alpha + spaces only |
| Address Lines | Alphanumeric |
| State Code | 2-character code |
| Country Code | 3-character code |
| Zip Code | Alphanumeric |
| Phone Numbers | Validated with area code lookup |
| EFT Account ID | Alphanumeric |
| Primary Cardholder | 'Y' or 'N' |

---

## Business Rules

1. **Account ID is required** - must be numeric, non-zero, 11 digits.
2. **Cross-reference lookup** - Account must exist in CXACAIX.
3. **Account master read** - Account must exist in ACCTDAT.
4. **Customer master read** - Customer must exist in CUSTDAT.
5. **Change detection** - Old values (stored in COMMAREA) are compared with new input; "No change detected" if identical.
6. **Field validation** - Each changed field is individually validated.
7. **Confirmation required** - After validation passes, user must press PF5 to commit.
8. **Optimistic locking** - Before REWRITE, the program re-reads the record with UPDATE option and verifies no one else changed it.
9. **Date validation** - Dates are validated using CSUTLDTC (calendar date utility).
10. **Name validation** - Names must contain only alphabets and spaces.

---

## Error Messages

| Condition | Message |
|---|---|
| Account not provided | "Account number not provided" |
| Account not numeric | "Account number must be a non zero 11 digit number" |
| Not in xref | "Did not find this account in account card xref file" |
| Not in master | "Did not find this account in account master file" |
| Customer not found | "Did not find associated customer in master file" |
| Status invalid | "Account Active Status must be Y or N" |
| Credit limit blank | "Credit Limit must be supplied" |
| Credit limit invalid | "Credit Limit is not valid" |
| No changes | "No change detected with respect to values fetched." |
| Lock error | "Could not lock account record for update" |
| Concurrent change | "Record changed by some one else. Please review" |
| Update failed | "Update of record failed" |

---

## Screen Navigation

| Key | Action |
|---|---|
| Enter | Submit account ID or field edits |
| PF3 | Return to calling program or main menu |
| PF5 | Confirm and save changes (only when changes validated) |
| PF12 | Cancel edits and re-fetch data |
