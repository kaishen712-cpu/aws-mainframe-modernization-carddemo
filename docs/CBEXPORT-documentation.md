# CBEXPORT - Export Customer Data for Branch Migration

## Overview

**Program ID:** CBEXPORT  
**Application:** CardDemo (AWS Mainframe Modernization)  
**Type:** BATCH COBOL Program  
**Function:** Export customer data from multiple VSAM files into a single sequential export file for branch migration  

CBEXPORT is a batch program that reads all records from multiple CardDemo VSAM
files (customers, accounts, cross-references, transactions, and cards) and
writes them into a single multi-record export file. Each export record contains
a record type discriminator, a timestamp, a sequence number, branch/region
identifiers, and the actual data payload. This export file is consumed by
CBIMPORT to load data into a different branch or environment.

---

## Program Structure

### Division Layout

| Division | Purpose |
|---|---|
| Identification | Declares program name (`CBEXPORT`) and author (`CARDDEMO TEAM`) |
| Environment | File-Control for 5 input files + 1 output file |
| Data | File Section (copybook layouts), Working-Storage (export control, statistics) |
| Procedure | Sequential processing of each file type |

### Input Files

| Logical Name | Copybook | Record Length | Key Field | Description |
|---|---|---|---|---|
| CUSTFILE | CVCUS01Y | 500 | CUST-ID | Customer master file |
| ACCTFILE | CVACT01Y | 300 | ACCT-ID | Account master file |
| XREFFILE | CVACT03Y | 50 | XREF-CARD-NUM | Card cross-reference file |
| TRANSACT | CVTRA05Y | 350 | TRAN-ID | Transaction file |
| CARDFILE | CVACT02Y | 150 | CARD-NUM | Card master file |

### Output File

| Logical Name | Copybook | Record Length | Description |
|---|---|---|---|
| EXPFILE | CVEXPORT | 500 | Multi-record export file |

---

## Export Record Structure (CVEXPORT - 500 bytes)

### Common Header (40 bytes)

| Field | PIC | Offset | Description |
|---|---|---|---|
| EXPORT-REC-TYPE | X(1) | 1 | Record type: C/A/X/T/D |
| EXPORT-TIMESTAMP | X(26) | 2-27 | Export timestamp (YYYY-MM-DD HH:MM:SS.00) |
| EXPORT-SEQUENCE-NUM | 9(9) COMP | 28-31 | Sequential record number |
| EXPORT-BRANCH-ID | X(4) | 32-35 | Branch identifier (default '0001') |
| EXPORT-REGION-CODE | X(5) | 36-40 | Region code (default 'NORTH') |

### Data Payload (460 bytes) — varies by record type

Uses REDEFINES to overlay different record structures:

#### Type 'C' — Customer Record
Maps from CVCUS01Y with COMP/COMP-3 optimized fields for ID and credit score.

#### Type 'A' — Account Record
Maps from CVACT01Y with COMP-3 fields for balances and COMP for debit.

#### Type 'T' — Transaction Record
Maps from CVTRA05Y with COMP-3 for amount and COMP for merchant ID.

#### Type 'X' — Cross-Reference Record
Maps from CVACT03Y with COMP for account ID.

#### Type 'D' — Card Record
Maps from CVACT02Y with COMP for account ID and CVV code.

---

## Program Flow

```
0000-MAIN-PROCESSING
  |-- 1000-INITIALIZE
  |     |-- 1050-GENERATE-TIMESTAMP
  |     |-- 1100-OPEN-FILES
  |-- 2000-EXPORT-CUSTOMERS     (type 'C')
  |-- 3000-EXPORT-ACCOUNTS      (type 'A')
  |-- 4000-EXPORT-XREFS         (type 'X')
  |-- 5000-EXPORT-TRANSACTIONS  (type 'T')
  |-- 5500-EXPORT-CARDS         (type 'D')
  |-- 6000-FINALIZE
  |-- GOBACK
```

For each file type:
1. Read the first record
2. Loop until EOF:
   - Initialize the export record
   - Set the record type, timestamp, sequence number, branch, and region
   - Map source fields to the appropriate REDEFINES overlay
   - Write the export record
   - Increment counters
   - Read the next record

---

## Statistics

The program tracks and displays counts for:
- Customer records exported
- Account records exported
- Cross-reference records exported
- Transaction records exported
- Card records exported
- Total records exported

---

## Error Handling

- File open errors: display error with file status code and ABEND
- File read errors: display error with file status code and ABEND
- Export write errors: display error with file status code and ABEND
- All errors call `9999-ABEND-PROGRAM` which calls `CEE3ABD`

---

## Python Translation Notes

In the Python translation:
- VSAM file I/O is replaced by repository interfaces with in-memory implementations
- The CVEXPORT REDEFINES structure maps to Python dataclasses with a discriminator field
- The export function produces a list of ExportRecord objects
- The sequence counter and timestamp are managed internally
- Statistics are returned as an ExportStatistics dataclass
