# CORPT00C - Transaction Report Program

## Overview

**Program ID:** CORPT00C  
**Application:** CardDemo (AWS Mainframe Modernization)  
**Type:** CICS COBOL Online Program  
**Transaction ID:** CR00  
**Function:** Submit batch transaction report requests with date range validation  

CORPT00C is an interactive CICS program that allows users to request batch
transaction reports. The user selects a report type (Monthly, Yearly, or Custom)
and — for custom reports — enters start and end dates. The program validates the
dates using the CSUTLDTC subroutine, then (in the original COBOL) submits a
batch JCL job via a transient data queue. In this Python translation, the JCL
submission is replaced with a report request object that captures the validated
parameters.

---

## Program Structure

### Division Layout

| Division | Purpose |
|---|---|
| Identification | Declares program name (`CORPT00C`) and author (`AWS`) |
| Environment | Configuration section (no special environment settings) |
| Data | Working-Storage variables, copybook includes, Linkage Section |
| Procedure | All business logic paragraphs |

### Key Copybooks Used

| Copybook | Purpose |
|---|---|
| `COCOM01Y` | Communication area (COMMAREA) shared across CardDemo programs |
| `CORPT00` | BMS map I/O areas for the Transaction Report screen (CORPT0AI / CORPT0AO) |
| `COTTL01Y` | Screen title constants |
| `CSDAT01Y` | Date/time formatting working storage |
| `CSMSG01Y` | Common message constants |
| `CVTRA05Y` | Transaction record layout (referenced for report context) |
| `DFHAID` | CICS attention identifier constants (Enter, PF keys) |
| `DFHBMSCA` | BMS attribute constants |

### External Calls

| Program | Purpose |
|---|---|
| `CSUTLDTC` | Date validation subroutine |

---

## Program Flow

```
MAIN-PARA
  |
  |-- If no COMMAREA (EIBCALEN = 0) --> return to sign-on screen (COSGN00C)
  |
  |-- First entry (PGM-ENTER):
  |     |-- Initialize screen to LOW-VALUES
  |     |-- SEND-TRNRPT-SCREEN
  |
  |-- Re-entry (PGM-REENTER):
        |-- RECEIVE-TRNRPT-SCREEN
        |-- Evaluate key pressed:
              |-- ENTER  --> PROCESS-ENTER-KEY
              |-- PF3    --> RETURN-TO-PREV-SCREEN
              |-- PF4    --> CLEAR-CURRENT-SCREEN
              |-- Other  --> Display "Invalid key" message
```

### PROCESS-ENTER-KEY

Evaluates the report type selected:

1. **Monthly** (MONTHLYI = 'M' or 'm'):
   - Compute start date: first day of current month
   - Compute end date: current date
   - Report name: 'Monthly'
   - Submit job

2. **Yearly** (YEARLYI = 'Y' or 'y'):
   - Compute start date: January 1 of current year
   - Compute end date: current date
   - Report name: 'Yearly'
   - Submit job

3. **Custom** (CUSTOMI = 'C' or 'c'):
   - Read start date (YYYY, MM, DD) from input fields
   - Read end date (YYYY, MM, DD) from input fields
   - Validate start date via CSUTLDTC
   - Validate end date via CSUTLDTC
   - Report name: 'Custom'
   - Submit job

4. **Other / no selection**:
   - Display: `"Select a report type to print report..."`

### SUBMIT-JOB-TO-INTRDR (Original COBOL)

In the original COBOL:
1. If confirmation is blank, prompt: `"Please confirm to print the <type> report..."`
2. If confirmed (Y/y), write JCL lines to the JOBS transient data queue
3. If declined (N/n), cancel and clear screen
4. If other value, display error

In Python, this is translated as returning a `ReportRequest` object with
validated parameters.

---

## Input Fields

| Screen Field | COBOL Field | Description |
|---|---|---|
| Monthly | MONTHLYI | 'M'/'m' to select monthly report |
| Yearly | YEARLYI | 'Y'/'y' to select yearly report |
| Custom | CUSTOMI | 'C'/'c' to select custom date range |
| Start Year | SDTYYYYI | Custom start year (YYYY) |
| Start Month | SDTMMI | Custom start month (MM) |
| Start Day | SDTDDI | Custom start day (DD) |
| End Year | EDTYYYYI | Custom end year (YYYY) |
| End Month | EDTMMI | Custom end month (MM) |
| End Day | EDTDDI | Custom end day (DD) |
| Confirm | CONFIRMI | Confirmation flag (Y/N) |

---

## Business Rules

### 1. Authentication / Session Check
- If no COMMAREA is passed (EIBCALEN = 0), the program redirects to the
  sign-on screen (`COSGN00C`).

### 2. Report Type Selection
- Exactly one report type must be selected.
- No selection produces: `"Select a report type to print report..."`

### 3. Monthly Report
- Date range: first of current month through current date.
- No date input fields are required.

### 4. Yearly Report
- Date range: January 1 of current year through current date.
- No date input fields are required.

### 5. Custom Report
- User must enter start date (YYYY, MM, DD) and end date (YYYY, MM, DD).
- Each date is validated using the CSUTLDTC subroutine.
- Invalid start date: `"Start Date - Not a valid date..."`
- Invalid end date: `"End Date - Not a valid date..."`
- Start date must not be after end date.

### 6. Confirmation Workflow
- `Y`/`y`: Proceed with report submission
- `N`/`n`: Cancel and clear screen
- Blank: Prompt for confirmation
- Other: Display `'"<value>" is not a valid value to confirm...'`

### 7. Report Output
In Python, the result is a `ReportRequest` dataclass with:
- `report_type`: 'Monthly', 'Yearly', or 'Custom'
- `start_date`: YYYYMMDD
- `end_date`: YYYYMMDD
- `confirmed`: bool

---

## Screen Navigation

| Key | Action |
|---|---|
| Enter | Validate inputs and process report request |
| PF3 | Return to previous screen |
| PF4 | Clear all fields |
| Any other | Display "Invalid key pressed" message |

---

## Error Handling

- `"Select a report type to print report..."` — no report type selected
- `"Start Date - Not a valid date..."` — custom start date is invalid
- `"End Date - Not a valid date..."` — custom end date is invalid
- `"Start date must not be after end date..."` — date range is inverted
- `"Please confirm to print the <type> report..."` — confirmation required
- `'"<value>" is not a valid value to confirm...'` — invalid confirmation
- `"<type> report submitted for printing ..."` — success message
