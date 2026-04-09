# CBACT02C — Print Card Data

## Overview

**Program ID:** CBACT02C  
**Type:** Batch  
**Original Language:** COBOL  
**Function:** Reads all card records sequentially and produces formatted output lines for each card.

This is a simple sequential read-and-display program.

## Program Structure

| Component | Description |
|-----------|-------------|
| `CardRecord` | Data class for card data (from CVACT02Y) |
| `CardRepository` | Abstract interface for card data access |
| `InMemoryCardRepository` | In-memory implementation for testing |
| `format_card_record()` | Formats a single card record as a display line |
| `print_card_data()` | Main entry point — reads and formats all cards |

## Program Flow

1. Emit start banner
2. Read all card records from repository
3. Format each record as a display line
4. Emit end banner
5. Return list of all lines

## Input Data

| Field | Source | Description |
|-------|--------|-------------|
| card_num | CVACT02Y | 16-character card number |
| card_acct_id | CVACT02Y | 11-digit account ID |
| card_cvv_cd | CVACT02Y | 3-digit CVV code |
| card_embossed_name | CVACT02Y | 50-character embossed name |
| card_expiration_date | CVACT02Y | 10-character expiration date |
| card_active_status | CVACT02Y | 1-character status (Y/N) |

## Outputs

A list of formatted strings containing:
- Start-of-execution banner
- One line per card with all fields formatted
- End-of-execution banner

## Business Rules

1. All card records are read sequentially and displayed.
2. The embossed name is trimmed of trailing whitespace.
3. No filtering or sorting is applied.

## Copybooks Used

| Copybook | Purpose |
|----------|---------|
| CVACT02Y | Card record layout (150 bytes) |
