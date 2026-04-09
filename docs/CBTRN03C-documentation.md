# CBTRN03C — Transaction Detail Report

## Overview

**Program ID:** CBTRN03C  
**Type:** Batch  
**Original Language:** COBOL  
**Function:** Generates a formatted transaction detail report grouped by account, with page totals, account totals, and a grand total.

The program reads transactions sequentially, looks up cross-reference data to determine the account for each card, resolves transaction type and category descriptions, and produces a paginated report.

## Program Structure

| Component | Description |
|-----------|-------------|
| `TransactionRecord` | Data class for transaction data (from CVTRA05Y) |
| `CardXrefRecord` | Data class for card-to-account cross-reference (from CVACT03Y) |
| `TranTypeRecord` | Data class for transaction type lookup (from CVTRA03Y) |
| `TranCatRecord` | Data class for transaction category lookup (from CVTRA04Y) |
| `TransactionFileRepository` | Abstract interface for sequential transaction access |
| `XrefLookupRepository` | Abstract interface for card cross-reference lookup |
| `TranTypeLookupRepository` | Abstract interface for transaction type lookup |
| `TranCatLookupRepository` | Abstract interface for transaction category lookup |
| `generate_transaction_detail_report()` | Main entry point — generates the full report |

## Program Flow

1. **Initialization** — Accept date range parameters (start_date, end_date)
2. **Read transactions** — Iterate through all transactions sequentially
3. **Date filtering** — Include only transactions with proc_ts within the date range
4. **Account grouping** — Detect card number changes to group by account
5. **Lookup enrichment** — Look up cross-reference (card → account), transaction type description, and category description
6. **Report formatting** — Build header, detail lines, page totals, account totals, and grand total
7. **Page breaks** — Insert page headers and page totals every `page_size` detail lines

## Input Data

| Field | Source | Description |
|-------|--------|-------------|
| Transactions | CVTRA05Y | Sequential transaction records with card num, amounts, timestamps |
| Cross-references | CVACT03Y | Maps card numbers to account IDs |
| Transaction types | CVTRA03Y | Maps type codes to descriptions |
| Transaction categories | CVTRA04Y | Maps type+category codes to descriptions |
| Start date | Parameter | Report date range start (YYYY-MM-DD) |
| End date | Parameter | Report date range end (YYYY-MM-DD) |

## Outputs

The function returns a list of formatted strings representing report lines:

| Line Type | Description |
|-----------|-------------|
| Report Name Header | Short name, long name, date range |
| Column Headers | Transaction ID, Account ID, Type, Category, Source, Amount |
| Separator | Dashes across the full line width |
| Detail Line | One per transaction with all fields formatted |
| Page Totals | Sum of amounts on the current page |
| Account Totals | Sum of amounts for the current account group |
| Grand Total | Sum of all page totals across the entire report |

## Business Rules

1. **Date filtering**: Only transactions with `tran_proc_ts` between `start_date` and `end_date` (inclusive) are included.
2. **Account grouping**: Transactions are grouped by `tran_card_num`. When the card number changes, account totals are emitted for the previous group.
3. **Page breaks**: After every `page_size` detail lines, page totals are printed followed by new page headers.
4. **Total accumulation**: Page totals feed into the grand total. Account totals are independent running sums per account group.
5. **Missing lookups**: If a cross-reference, type, or category lookup fails, the corresponding field is left empty (no error).
6. **Amount formatting**: Amounts use sign prefix (+/-), comma-separated thousands, and two decimal places, right-justified to 15 characters.

## Error Handling

- Missing cross-reference record: Account ID displayed as empty string
- Missing transaction type: Type description displayed as empty string
- Missing transaction category: Category description displayed as empty string
- No transactions in date range: Returns an empty list (no report generated)

## Copybooks Used

| Copybook | Purpose |
|----------|---------|
| CVTRA05Y | Transaction record layout (350 bytes) |
| CVACT03Y | Card cross-reference record (50 bytes) |
| CVTRA03Y | Transaction type record (60 bytes) |
| CVTRA04Y | Transaction category record (60 bytes) |
| CVTRA07Y | Report formatting structures |
