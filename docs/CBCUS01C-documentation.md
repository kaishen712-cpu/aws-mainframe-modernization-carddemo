# CBCUS01C — Print Customer Data

## Overview

**Program ID:** CBCUS01C  
**Type:** Batch  
**Original Language:** COBOL  
**Function:** Reads all customer records sequentially and produces formatted output lines for each customer.

This is a simple sequential read-and-display program.

## Program Structure

| Component | Description |
|-----------|-------------|
| `CustomerRecord` | Data class for customer data (from CVCUS01Y) |
| `CustomerRepository` | Abstract interface for customer data access |
| `InMemoryCustomerRepository` | In-memory implementation for testing |
| `format_customer_record()` | Formats a single customer record as a display line |
| `print_customer_data()` | Main entry point — reads and formats all customers |

## Program Flow

1. Emit start banner
2. Read all customer records from repository
3. Format each record as a display line
4. Emit end banner
5. Return list of all lines

## Input Data

| Field | Source | Description |
|-------|--------|-------------|
| cust_id | CVCUS01Y | 9-digit customer ID |
| cust_first_name | CVCUS01Y | 25-character first name |
| cust_middle_name | CVCUS01Y | 25-character middle name |
| cust_last_name | CVCUS01Y | 25-character last name |
| cust_addr_line_1/2/3 | CVCUS01Y | Address lines (50 chars each) |
| cust_addr_state_cd | CVCUS01Y | 2-character state code |
| cust_addr_country_cd | CVCUS01Y | 3-character country code |
| cust_addr_zip | CVCUS01Y | 10-character ZIP code |
| cust_phone_num_1/2 | CVCUS01Y | Phone numbers (15 chars each) |
| cust_ssn | CVCUS01Y | 9-digit SSN |
| cust_govt_issued_id | CVCUS01Y | 20-character government ID |
| cust_dob_yyyy_mm_dd | CVCUS01Y | 10-character date of birth |
| cust_eft_account_id | CVCUS01Y | 10-character EFT account |
| cust_pri_card_holder_ind | CVCUS01Y | 1-character primary indicator |
| cust_fico_credit_score | CVCUS01Y | 3-digit FICO score |

## Outputs

A list of formatted strings containing:
- Start-of-execution banner
- One line per customer with key fields (ID, name, SSN, DOB, FICO, address)
- End-of-execution banner

## Business Rules

1. All customer records are read sequentially and displayed.
2. Customer names are trimmed of trailing whitespace before display.
3. The display line includes: customer ID, full name, SSN, DOB, FICO score, and primary address with state/ZIP.
4. No filtering or sorting is applied.

## Copybooks Used

| Copybook | Purpose |
|----------|---------|
| CVCUS01Y | Customer record layout (500 bytes) |
