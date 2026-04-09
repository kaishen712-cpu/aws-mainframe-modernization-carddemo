# CBIMPORT - Import Customer Data from Branch Migration Export

## Overview

**Program ID:** CBIMPORT  
**Application:** CardDemo (AWS Mainframe Modernization)  
**Type:** BATCH COBOL Program  
**Function:** Import customer data from a branch migration export file back into individual normalized files  

CBIMPORT is a batch program that reads the multi-record export file produced by
CBEXPORT and dispatches each record to the appropriate output file based on its
record type. It is the reverse complement of CBEXPORT — together they enable
data migration between CardDemo branches or environments.

---

## Program Structure

### Division Layout

| Division | Purpose |
|---|---|
| Identification | Declares program name (`CBIMPORT`) and author (`CARDDEMO TEAM`) |
| Environment | File-Control for 1 input + 5 output + 1 error file |
| Data | File Section (copybook layouts), Working-Storage (control, statistics, error layout) |
| Procedure | Sequential read and dispatch by record type |

### Input File

| Logical Name | Record Length | Description |
|---|---|---|
| EXPFILE | 500 | Multi-record export file (from CBEXPORT) |

### Output Files

| Logical Name | Copybook | Record Length | Description |
|---|---|---|---|
| CUSTOUT | CVCUS01Y | 500 | Customer records |
| ACCTOUT | CVACT01Y | 300 | Account records |
| XREFOUT | CVACT03Y | 50 | Cross-reference records |
| TRNXOUT | CVTRA05Y | 350 | Transaction records |
| CARDOUT | CVACT02Y | 150 | Card records |
| ERROUT | — | 132 | Error/unknown records |

---

## Program Flow

```
0000-MAIN-PROCESSING
  |-- 1000-INITIALIZE
  |     |-- 1100-OPEN-FILES
  |-- 2000-PROCESS-EXPORT-FILE
  |     |-- Loop: read each record
  |           |-- 2200-PROCESS-RECORD-BY-TYPE
  |                 |-- EVALUATE EXPORT-REC-TYPE
  |                       |-- 'C' → 2300-PROCESS-CUSTOMER-RECORD
  |                       |-- 'A' → 2400-PROCESS-ACCOUNT-RECORD
  |                       |-- 'X' → 2500-PROCESS-XREF-RECORD
  |                       |-- 'T' → 2600-PROCESS-TRAN-RECORD
  |                       |-- 'D' → 2650-PROCESS-CARD-RECORD
  |                       |-- OTHER → 2700-PROCESS-UNKNOWN-RECORD
  |-- 3000-VALIDATE-IMPORT
  |-- 4000-FINALIZE
  |-- GOBACK
```

### Record Processing

For each record type:
1. Initialize the target record structure
2. Map fields from the CVEXPORT overlay to the target copybook fields
3. Write the record to the appropriate output file
4. Increment the type-specific counter

### Unknown Records

Records with unrecognized type codes are:
1. Counted in `WS-UNKNOWN-RECORD-TYPE-COUNT`
2. Written to the error output file with timestamp, record type, sequence number, and error message

---

## Error Record Layout (132 bytes)

| Field | PIC | Description |
|---|---|---|
| ERR-TIMESTAMP | X(26) | Current date/time |
| Separator | X(1) | Pipe character |
| ERR-RECORD-TYPE | X(1) | The unrecognized record type |
| Separator | X(1) | Pipe character |
| ERR-SEQUENCE | 9(7) | Sequence number of the bad record |
| Separator | X(1) | Pipe character |
| ERR-MESSAGE | X(50) | Error description |
| FILLER | X(43) | Spaces |

---

## Statistics

The program tracks and displays counts for:
- Total records read
- Customer records imported
- Account records imported
- Cross-reference records imported
- Transaction records imported
- Card records imported
- Error records written
- Unknown record types encountered

---

## Error Handling

- File open errors: display error with file status code and ABEND
- File read errors: display error with file status code and ABEND
- Output write errors: display error with file status code and ABEND
- Unknown record types: logged to error file (non-fatal)
- All fatal errors call `9999-ABEND-PROGRAM` which calls `CEE3ABD`

---

## Python Translation Notes

In the Python translation:
- The import function accepts a list of ExportRecord objects (as produced by CBEXPORT)
- Records are dispatched to repository write methods by record type
- Unknown record types are collected in an error list
- Statistics are returned as an ImportStatistics dataclass
- The function is designed as the complement of the export function for round-trip testing
