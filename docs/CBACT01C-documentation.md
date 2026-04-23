# CBACT01C — Read Accounts & Write Output

## Overview

**Program ID:** CBACT01C  
**Type:** Batch  
**Original Language:** COBOL  
**Function:** Reads account records from a VSAM file and produces multiple formatted output representations: a standard reformatted account record, an array record with balance/debit repetitions, and variable-length records.

The original program calls the COBDATFT assembler routine for date formatting. This Python translation replaces it with `datetime` formatting.

## Program Structure

| Component | Description |
|-----------|-------------|
| `AccountRecord` | Data class for input account data (from CVACT01Y) |
| `OutputAccountRecord` | Reformatted output record with date conversion |
| `ArrayAccountRecord` | Array-format record with 5 balance/debit slots |
| `VbrcRecord1` | Variable-length record type 1 (ID + status) |
| `VbrcRecord2` | Variable-length record type 2 (ID + balance + limit + year) |
| `AccountRepository` | Abstract interface for account data access |
| `BatchResult` | Container for all output collections |
| `format_date_cobdatft()` | Date formatting (replaces COBDATFT assembler) |
| `process_accounts()` | Main entry point — processes all accounts |

## Program Flow

1. **Read accounts** — Iterate through all accounts sequentially
2. **For each account:**
   a. Format display lines (1100-DISPLAY-ACCT-RECORD)
   b. Build output record with reformatted dates (1300-POPUL-ACCT-RECORD)
   c. Build array record with balance/debit slots (1400-POPUL-ARRAY-RECORD)
   d. Build variable-length record pair (1500-POPUL-VBRC-RECORD)
3. **Return** — `BatchResult` containing all output collections

## Date Formatting (COBDATFT Replacement)

The `format_date_cobdatft()` function replaces the COBDATFT assembler call:

| Input Type | Format | Output Type | Format |
|-----------|---------|-------------|---------|
| "1" | YYYYMMDD | "1" | YYYY-MM-DD |
| "2" | YYYY-MM-DD | "2" | YYYYMMDD |

Invalid dates are returned unchanged.

## Input Data

| Field | Source | Description |
|-------|--------|-------------|
| Account records | CVACT01Y | Full account data including balances, dates, status |

## Outputs

### BatchResult contains:

| Output | Description |
|--------|-------------|
| `display_lines` | Formatted text for console display with start/end banners |
| `output_records` | Reformatted `OutputAccountRecord` list (date converted, default debit) |
| `array_records` | `ArrayAccountRecord` list with 5 balance/debit slots |
| `vbrc_records_1` | `VbrcRecord1` list (ID + status) |
| `vbrc_records_2` | `VbrcRecord2` list (ID + balance + limit + reissue year) |

## Business Rules

1. **Date reformatting**: The reissue date is converted from YYYY-MM-DD to YYYYMMDD format in the output record.
2. **Default debit**: If `acct_curr_cyc_debit` is zero, it defaults to 2525.00 in the output record.
3. **Array record slots**: Slots 0-2 are populated with specific values; slots 3-4 remain zero.
   - Slot 0: current balance / 1005.00
   - Slot 1: current balance / 1525.00
   - Slot 2: -1025.00 / -2500.00
4. **Variable-length records**: Two record types are produced per account — a short (ID+status) and a longer (ID+balance+limit+year) record.
5. **Reissue year**: First 4 characters of the reissue date string.

## Error Handling

- Invalid date format: `format_date_cobdatft` returns the original string unchanged
- Empty date string: Returned unchanged
- Short date string: Returned unchanged

## Copybooks Used

| Copybook | Purpose |
|----------|---------|
| CVACT01Y | Account record layout (300 bytes) |
| CODATECN | Date formatting parameters (replaced by `format_date_cobdatft`) |
