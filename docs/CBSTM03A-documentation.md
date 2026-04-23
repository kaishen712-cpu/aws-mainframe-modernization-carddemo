# CBSTM03A — Account Statements

## Overview

**Program ID:** CBSTM03A  
**Type:** Batch  
**Original Language:** COBOL  
**Function:** Generates formatted account statements including customer header, account summary, transaction list, and running balance. Produces both plain text and HTML output.

The original COBOL program uses ALTER/GO TO control flow and 2-dimensional arrays. This Python translation uses structured loops and dictionaries.

## Program Structure

| Component | Description |
|-----------|-------------|
| `StatementTransaction` | Data class for a single transaction on a statement |
| `CardTransactions` | Data class grouping transactions by card number |
| `AccountStatement` | Data class for a complete account statement |
| `format_statement_text()` | Formats a statement as plain text lines |
| `format_statement_html()` | Formats a statement as HTML lines |
| `generate_account_statements()` | Main entry point — generates statement data |
| `generate_statement_report()` | Convenience — generates all statements as text |
| `generate_statement_html()` | Convenience — generates all statements as HTML |

## Program Flow

1. **Open files** — Via `StatementFileHandler` (CBSTM03B)
2. **Read cross-references** — Sequentially read all xref records, grouping by account ID
3. **For each account:**
   a. Read customer record by key (from first xref's customer ID)
   b. Read account record by key
   c. Read all transactions, matching to cards belonging to the account
   d. Build `AccountStatement` object
4. **Close files**
5. **Format output** — Plain text or HTML

### Relationship with CBSTM03B

In the COBOL version, CBSTM03A calls CBSTM03B via `CALL 'CBSTM03B' USING WS-M03B-AREA` for each file operation. In the Python translation, `StatementFileHandler` from `cbstm03b.py` provides the same operations as methods.

## Input Data

| Source | Access | Description |
|--------|--------|-------------|
| Transaction file (COSTM01) | Sequential via handler | Transactions keyed by card+tran-id |
| Cross-reference file (CVACT03Y) | Sequential via handler | Maps cards to customers and accounts |
| Customer file (CUSTREC) | Keyed via handler | Customer demographics |
| Account file (CVACT01Y) | Keyed via handler | Account financial data |

## Outputs

### Plain Text Statement

| Section | Content |
|---------|---------|
| Header | "ACCOUNT STATEMENT" separator |
| Customer Info | Name, ID, address |
| Account Summary | ID, status, balance, limits, dates |
| Transactions | Grouped by card — ID, type, category, description, amount |
| Footer | Running balance |

### HTML Statement

Full HTML document with CSS styling, tables for customer info, account summary, and transactions grouped by card.

## Business Rules

1. **Account grouping**: Cross-reference records with the same `xref_acct_id` are grouped into one statement.
2. **Transaction assignment**: Transactions are matched to cards by `trnx_card_num`. Only transactions for cards belonging to the current account are included.
3. **Customer lookup**: Uses the customer ID from the first cross-reference record for the account.
4. **Missing data**: If customer or account records are not found, corresponding fields default to empty strings or zero.
5. **Multiple cards**: An account may have multiple cards, each with its own transaction section.
6. **Running balance**: Displayed as the account's current balance (not computed from transactions).

## Error Handling

- Missing customer record: Statement generated with empty customer fields
- Missing account record: Statement generated with zero balance and empty date fields
- No transactions for a card: Card section omitted from statement
- No cross-reference records: Empty list returned (no statements generated)

## Copybooks Used

| Copybook | Purpose |
|----------|---------|
| COSTM01 | Transaction record (via CBSTM03B) |
| CVACT03Y | Card cross-reference record (via CBSTM03B) |
| CUSTREC | Customer record (via CBSTM03B) |
| CVACT01Y | Account record (via CBSTM03B) |
