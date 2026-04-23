# CBACT03C — Print Card Cross-Reference Data

## Overview

**Program ID:** CBACT03C  
**Type:** Batch  
**Original Language:** COBOL  
**Function:** Reads all card cross-reference records sequentially and produces formatted output lines for each record.

This is a simple sequential read-and-display program.

## Program Structure

| Component | Description |
|-----------|-------------|
| `CardXrefRecord` | Data class for cross-reference data (from CVACT03Y) |
| `XrefRepository` | Abstract interface for xref data access |
| `InMemoryXrefRepository` | In-memory implementation for testing |
| `format_xref_record()` | Formats a single xref record as a display line |
| `print_card_xref_data()` | Main entry point — reads and formats all xrefs |

## Program Flow

1. Emit start banner
2. Read all cross-reference records from repository
3. Format each record as a display line
4. Emit end banner
5. Return list of all lines

## Input Data

| Field | Source | Description |
|-------|--------|-------------|
| xref_card_num | CVACT03Y | 16-character card number |
| xref_cust_id | CVACT03Y | 9-digit customer ID |
| xref_acct_id | CVACT03Y | 11-digit account ID |

## Outputs

A list of formatted strings containing:
- Start-of-execution banner
- One line per cross-reference with all fields formatted
- End-of-execution banner

## Business Rules

1. All cross-reference records are read sequentially and displayed.
2. No filtering or sorting is applied.

## Copybooks Used

| Copybook | Purpose |
|----------|---------|
| CVACT03Y | Card cross-reference record layout (50 bytes) |
