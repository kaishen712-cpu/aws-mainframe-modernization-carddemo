# COCRDLIC - Credit Card List Program

## Overview

**Program ID:** COCRDLIC
**Application:** CardDemo (AWS Mainframe Modernization)
**Type:** CICS COBOL Online Program
**Transaction ID:** CCLI
**Function:** Browse and search credit cards with pagination

COCRDLIC is an interactive CICS program that provides a paginated list
display of credit card records. Users can search by account ID or card
number, navigate pages with PF7/PF8, and select a card to view details
(COCRDSLC) or update (COCRDUPC).

---

## Program Structure

### Key Copybooks Used

| Copybook | Purpose |
|---|---|
| `COCOM01Y` | Communication area (COMMAREA) |
| `COCRDLI` | BMS map I/O areas for the Card List screen |
| `COCRDSL` | BMS map I/O areas (shared with card detail screens) |
| `COTTL01Y` | Screen title constants |
| `CSDAT01Y` | Date/time formatting |
| `CSMSG01Y` | Common message constants |
| `CSMSG02Y` | Abend message variables |
| `CSUSR01Y` | Signed-on user data |
| `CVACT02Y` | Card record layout (150 bytes) |
| `CVCRD01Y` | Card work area |
| `CSSTRPFY` | PF key storage/mapping |
| `DFHBMSCA` | BMS screen attributes |
| `DFHAID` | AID key definitions |

### VSAM Files Accessed

| Logical Name | Purpose |
|---|---|
| CARDDAT | Card master file (browse) |
| CARDAIX | Card file alternate index by account |
| CXACAIX | Card cross-reference by account |

---

## Program Flow

```
0000-MAIN
  |
  |-- PF3 --> XCTL to calling program or main menu
  |
  |-- First entry (PGM-ENTER):
  |     |-- 1000-SEND-MAP (empty form, prompt for search criteria)
  |
  |-- Re-entry (PGM-REENTER):
        |-- 2000-PROCESS-INPUTS
        |     |-- 2100-RECEIVE-MAP
        |     |-- 2200-EDIT-MAP-INPUTS
        |           |-- 2210-EDIT-ACCOUNT (validate account filter)
        |           |-- 2220-EDIT-CARD (validate card filter)
        |
        |-- Evaluate input:
        |     |-- Enter: Execute search
        |     |-- PF7: Page backward
        |     |-- PF8: Page forward
        |     |-- Selection: XCTL to view or update program
        |
        |-- 9000-READ-DATA
        |     |-- 9100-STARTBR-CARDFILE (position cursor)
        |     |-- 9200-READNEXT-CARDFILE (read page of records)
        |     |-- 9300-ENDBR-CARDFILE (end browse)
        |
        |-- 1000-SEND-MAP (display results)
```

---

## Search Criteria

| Field | Validation |
|---|---|
| Account ID | Optional; if supplied, must be 11-digit numeric, non-zero |
| Card Number | Optional; if supplied, must be 16-digit numeric, non-zero |

When both filters are blank, all cards are displayed.

---

## Business Rules

1. **Optional filters** — both account ID and card number are optional search criteria.
2. **Account filter** — if supplied, must be a valid 11-digit numeric value.
3. **Card filter** — if supplied, must be a valid 16-digit numeric value.
4. **Pagination** — displays 7 card rows per page with PF7 (backward) and PF8 (forward) navigation.
5. **Card selection** — user can select a card by entering 'S' (view) or 'U' (update) next to a card row.
6. **View transfer** — selecting a card for view transfers control (XCTL) to COCRDSLC.
7. **Update transfer** — selecting a card for update transfers control (XCTL) to COCRDUPC.
8. **Browse ordering** — cards are displayed in ascending card number order.

---

## Error Messages

| Condition | Message |
|---|---|
| Account filter non-numeric | "Account filter, if supplied, must be a 11 digit number" |
| Card filter non-numeric | "Card filter, if supplied, must be a 16 digit number" |
| No cards found | "No cards found matching the criteria" |
| File read error | File-specific error message with RESP/RESP2 codes |

---

## Screen Navigation

| Key | Action |
|---|---|
| Enter | Execute search with current filters |
| PF3 | Return to calling program or main menu |
| PF7 | Page backward |
| PF8 | Page forward |
| S (selection) | View selected card (XCTL to COCRDSLC) |
| U (selection) | Update selected card (XCTL to COCRDUPC) |
