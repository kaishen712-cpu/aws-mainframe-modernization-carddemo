# COCRDUPC - Credit Card Update Program

## Overview

**Program ID:** COCRDUPC
**Application:** CardDemo (AWS Mainframe Modernization)
**Type:** CICS COBOL Online Program
**Transaction ID:** CCUP
**Function:** Update credit card details with confirmation

COCRDUPC is an interactive CICS program that allows users to update
credit card details including the embossed name, expiration date, and
active status. It implements a confirmation workflow requiring the user
to press PF5 to commit changes, and performs optimistic locking to
prevent concurrent update conflicts.

---

## Program Structure

### Key Copybooks Used

| Copybook | Purpose |
|---|---|
| `COCOM01Y` | Communication area (COMMAREA) |
| `COCRDUP` | BMS map I/O areas for the Card Update screen |
| `COTTL01Y` | Screen title constants |
| `CSDAT01Y` | Date/time formatting |
| `CSMSG01Y` | Common message constants |
| `CSMSG02Y` | Abend message variables |
| `CSUSR01Y` | Signed-on user data |
| `CVACT02Y` | Card record layout (150 bytes) |
| `CVCUS01Y` | Customer record layout (500 bytes) |
| `CVCRD01Y` | Card work area |
| `CSSTRPFY` | PF key storage/mapping |

### VSAM Files Accessed

| Logical Name | Purpose |
|---|---|
| CARDDAT | Card master file (read/update) |
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
  |     |-- 9000-READ-DATA (fetch card details)
  |     |-- 3000-SEND-MAP (display card for editing)
  |
  |-- Direct entry:
  |     |-- 3000-SEND-MAP (prompt for account ID / card number)
  |
  |-- Re-entry with edits:
        |-- 1000-PROCESS-INPUTS
        |     |-- 1100-RECEIVE-MAP
        |     |-- 1200-EDIT-MAP-INPUTS
        |           |-- 1210-EDIT-ACCOUNT (validate account ID)
        |           |-- 1220-EDIT-CARD (validate card number)
        |           |-- 1230-EDIT-NAME (validate embossed name)
        |           |-- 1240-EDIT-CARDSTATUS (validate Y/N)
        |           |-- 1250-EDIT-EXPIRY-MON (validate 01-12)
        |           |-- 1260-EDIT-EXPIRY-YEAR (validate 4-digit)
        |
        |-- 2000-DECIDE-ACTION
        |     |-- No changes --> show "No changes detected"
        |     |-- Changes valid --> prompt for PF5 confirmation
        |     |-- PF5 confirmed:
        |           |-- 9500-UPDATE-CARD
        |           |     |-- READ-UPDATE (lock record)
        |           |     |-- Verify no concurrent change
        |           |     |-- REWRITE card record
        |           |-- Show success/failure message
        |
        |-- Changes after completion:
              |-- Reset and prompt for new search
```

---

## Updatable Fields

| Field | Validation |
|---|---|
| Embossed Name | Required; cannot be blank |
| Active Status | Must be 'Y' (active) or 'N' (inactive) |
| Expiry Month | Numeric, 01-12 |
| Expiry Year | Numeric, 4-digit year |

---

## Business Rules

1. **Account ID required** — must be 11-digit numeric, non-zero.
2. **Card number required** — must be 16-digit numeric, non-zero.
3. **Card lookup** — card must exist in CARDDAT file.
4. **Change detection** — old values (from COMMAREA) compared with new input using case-insensitive comparison (UPPER-CASE).
5. **No changes** — if old and new values are identical, "No changes detected" is reported.
6. **Field validation** — each changed field is individually validated before confirmation prompt.
7. **Confirmation required** — after validation passes, user must press PF5 to commit.
8. **Optimistic locking** — before REWRITE, re-reads with UPDATE option and verifies no concurrent changes.
9. **From card list** — when invoked from COCRDLIC, search fields are pre-populated and protected.
10. **PF12 cancel** — cancels edits and re-fetches original data.

---

## Error Messages

| Condition | Message |
|---|---|
| Account ID not provided | "Account ID not provided" |
| Account ID non-numeric | "Account filter, if supplied must be a 11 digit number" |
| Card number not provided | "Card number not provided" |
| Card number non-numeric | "Card ID filter, if supplied must be a 16 digit number" |
| Card not found | "Did not find acct+card combination in card file" |
| Name blank | "Card holder name is required" |
| Status invalid | "Card status must be Y or N" |
| Month blank/invalid | "Expiry month is required" / "Card expiry month must be between 1 and 12" |
| Year blank/invalid | "Expiry year is required" / "Expiry year must be a 4-digit year" |
| No changes | "No changes detected" |
| Lock error | "Could not lock card record for update" |
| Update failed | "Update of card record failed" |

---

## Screen Navigation

| Key | Action |
|---|---|
| Enter | Submit search criteria or field edits |
| PF3 | Return to calling program or main menu |
| PF5 | Confirm and save changes (only when changes validated) |
| PF12 | Cancel edits and re-fetch data |
