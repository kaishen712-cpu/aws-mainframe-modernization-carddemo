# CSUTLDTC - Date Validation Utility

## Overview

**Program ID:** CSUTLDTC  
**Application:** CardDemo (AWS Mainframe Modernization)  
**Type:** COBOL Subroutine (called by other programs)  
**Function:** Validate a date string against a specified date format  

CSUTLDTC is a utility subroutine that validates whether a given date string
represents a valid calendar date. It is called by several CardDemo programs
including COTRN02C (Add Transaction), CORPT00C (Transaction Reports), and
COACTUPC (Account Update) to verify user-entered dates.

---

## Program Structure

### Division Layout

| Division | Purpose |
|---|---|
| Identification | Declares program name (`CSUTLDTC`) |
| Data | Working-Storage for CEEDAYS API structures, Linkage Section for parameters |
| Procedure | Main validation logic using IBM LE CEEDAYS service |

### Key Dependencies

| Service | Purpose |
|---|---|
| `CEEDAYS` | IBM Language Environment callable service that converts a date string to a Lilian day number. If conversion succeeds, the date is valid. |

---

## Interface

### Input Parameters (Linkage Section)

| Parameter | PIC | Length | Description |
|---|---|---|---|
| `LS-DATE` | X(10) | 10 | Date string to validate (e.g., `2024-06-15`) |
| `LS-DATE-FORMAT` | X(10) | 10 | Format mask (e.g., `YYYY-MM-DD`, `YYYYMMDD`) |

### Output

| Parameter | PIC | Length | Description |
|---|---|---|---|
| `LS-RESULT` | X(80) | 80 | Result message containing severity, message code, result text, test date, and mask |
| `RETURN-CODE` | 9(4) | 4 | Severity code: `0000` = valid date, non-zero = invalid |

### Result Message Structure (WS-MESSAGE)

| Field | PIC | Description |
|---|---|---|
| `WS-SEVERITY` | X(04) | Severity code from CEEDAYS feedback |
| `WS-MSG-NO` | X(04) | Message number from CEEDAYS feedback |
| `WS-RESULT` | X(15) | Human-readable result description |
| `WS-DATE` | X(10) | The date that was tested |
| `WS-DATE-FMT` | X(10) | The format mask that was used |

---

## Validation Logic

1. Copy the input date and format into CEEDAYS-compatible variable-length strings
2. Call `CEEDAYS` to attempt conversion to a Lilian day number
3. Extract severity and message number from the feedback code
4. Map the feedback code to a human-readable result:

| Feedback Condition | Result Text |
|---|---|
| `FC-INVALID-DATE` (all zeros) | `Date is valid` |
| `FC-INSUFFICIENT-DATA` | `Insufficient` |
| `FC-BAD-DATE-VALUE` | `Datevalue error` |
| `FC-INVALID-ERA` | `Invalid Era` |
| `FC-UNSUPP-RANGE` | `Unsupp. Range` |
| `FC-INVALID-MONTH` | `Invalid month` |
| `FC-BAD-PIC-STRING` | `Bad Pic String` |
| `FC-NON-NUMERIC-DATA` | `Nonnumeric data` |
| `FC-YEAR-IN-ERA-ZERO` | `YearInEra is 0` |
| Other | `Date is invalid` |

5. Return the severity code as `RETURN-CODE`

---

## Usage in CardDemo

Programs that call CSUTLDTC:
- **COTRN02C** — validates origination and processing dates when adding transactions
- **CORPT00C** — validates date range for transaction reports
- **COACTUPC** — validates dates when updating account information

### Calling Convention

```cobol
CALL 'CSUTLDTC' USING WS-DATE WS-DATE-FORMAT WS-RESULT
```

After the call, the program checks `WS-SEVERITY-N`:
- If `0000` → date is valid
- If non-zero and `WS-MSG-NO-N` ≠ `2513` → date is invalid

---

## Python Translation Notes

In the Python translation, the CEEDAYS service is replaced by Python's
`datetime.strptime()`. The function accepts a date string and format string,
attempts to parse it, and returns a result dataclass with severity code,
message number, result text, and the tested date/format.

The format mapping converts COBOL-style masks (e.g., `YYYYMMDD`, `YYYY-MM-DD`)
to Python strftime/strptime format codes (e.g., `%Y%m%d`, `%Y-%m-%d`).
