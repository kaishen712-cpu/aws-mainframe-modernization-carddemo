# CardDemo Data Model — Data Dictionary

This document describes every VSAM record type used by the CardDemo application,
their fields, data types, relationships, and original COBOL copybook sources.

---

## 1. Account Record

| Property | Value |
|---|---|
| **Copybook** | `CVACT01Y.cpy` |
| **Record Length** | 300 bytes |
| **Primary Key** | `ACCT-ID` |
| **Python Class** | `AccountRecord` |

| COBOL Field | PIC | Python Field | Python Type | Description |
|---|---|---|---|---|
| ACCT-ID | 9(11) | `acct_id` | `str` | 11-digit account identifier |
| ACCT-ACTIVE-STATUS | X(01) | `acct_active_status` | `str` | Active status flag |
| ACCT-CURR-BAL | S9(10)V99 | `acct_curr_bal` | `float` | Current balance |
| ACCT-CREDIT-LIMIT | S9(10)V99 | `acct_credit_limit` | `float` | Credit limit |
| ACCT-CASH-CREDIT-LIMIT | S9(10)V99 | `acct_cash_credit_limit` | `float` | Cash credit limit |
| ACCT-OPEN-DATE | X(10) | `acct_open_date` | `str` | Account open date |
| ACCT-EXPIRAION-DATE | X(10) | `acct_expiration_date` | `str` | Expiration date |
| ACCT-REISSUE-DATE | X(10) | `acct_reissue_date` | `str` | Reissue date |
| ACCT-CURR-CYC-CREDIT | S9(10)V99 | `acct_curr_cyc_credit` | `float` | Current cycle credits |
| ACCT-CURR-CYC-DEBIT | S9(10)V99 | `acct_curr_cyc_debit` | `float` | Current cycle debits |
| ACCT-ADDR-ZIP | X(10) | `acct_addr_zip` | `str` | ZIP code |
| ACCT-GROUP-ID | X(10) | `acct_group_id` | `str` | Disclosure group ID |
| FILLER | X(178) | — | — | Padding to 300 bytes |

**Relationships:**
- Referenced by `CardRecord` via `CARD-ACCT-ID`
- Referenced by `CardXrefRecord` via `XREF-ACCT-ID`
- Linked to `DisclosureGroupRecord` via `ACCT-GROUP-ID`

---

## 2. Card Record

| Property | Value |
|---|---|
| **Copybook** | `CVACT02Y.cpy` |
| **Record Length** | 150 bytes |
| **Primary Key** | `CARD-NUM` |
| **Python Class** | `CardRecord` |

| COBOL Field | PIC | Python Field | Python Type | Description |
|---|---|---|---|---|
| CARD-NUM | X(16) | `card_num` | `str` | 16-character card number |
| CARD-ACCT-ID | 9(11) | `card_acct_id` | `str` | Associated account ID |
| CARD-CVV-CD | 9(03) | `card_cvv_cd` | `str` | CVV security code |
| CARD-EMBOSSED-NAME | X(50) | `card_embossed_name` | `str` | Name on card |
| CARD-EXPIRAION-DATE | X(10) | `card_expiration_date` | `str` | Card expiration date |
| CARD-ACTIVE-STATUS | X(01) | `card_active_status` | `str` | Active status flag |
| FILLER | X(59) | — | — | Padding to 150 bytes |

**Relationships:**
- Belongs to `AccountRecord` via `CARD-ACCT-ID`
- Referenced by `TransactionRecord` via `TRAN-CARD-NUM`

---

## 3. Card Cross-Reference Record

| Property | Value |
|---|---|
| **Copybook** | `CVACT03Y.cpy` |
| **Record Length** | 50 bytes |
| **Primary Key** | `XREF-CARD-NUM` |
| **Alternate Index** | `XREF-ACCT-ID` |
| **Python Class** | `CardXrefRecord` |

| COBOL Field | PIC | Python Field | Python Type | Description |
|---|---|---|---|---|
| XREF-CARD-NUM | X(16) | `xref_card_num` | `str` | Card number |
| XREF-CUST-ID | 9(09) | `xref_cust_id` | `str` | Customer ID |
| XREF-ACCT-ID | 9(11) | `xref_acct_id` | `str` | Account ID |
| FILLER | X(14) | — | — | Padding to 50 bytes |

**Relationships:**
- Links `CustomerRecord`, `AccountRecord`, and `CardRecord`

---

## 4. Customer Record

| Property | Value |
|---|---|
| **Copybook** | `CVCUS01Y.cpy` |
| **Record Length** | 500 bytes |
| **Primary Key** | `CUST-ID` |
| **Python Class** | `CustomerRecord` |

| COBOL Field | PIC | Python Field | Python Type | Description |
|---|---|---|---|---|
| CUST-ID | 9(09) | `cust_id` | `str` | 9-digit customer ID |
| CUST-FIRST-NAME | X(25) | `cust_first_name` | `str` | First name |
| CUST-MIDDLE-NAME | X(25) | `cust_middle_name` | `str` | Middle name |
| CUST-LAST-NAME | X(25) | `cust_last_name` | `str` | Last name |
| CUST-ADDR-LINE-1 | X(50) | `cust_addr_line_1` | `str` | Address line 1 |
| CUST-ADDR-LINE-2 | X(50) | `cust_addr_line_2` | `str` | Address line 2 |
| CUST-ADDR-LINE-3 | X(50) | `cust_addr_line_3` | `str` | Address line 3 |
| CUST-ADDR-STATE-CD | X(02) | `cust_addr_state_cd` | `str` | State code |
| CUST-ADDR-COUNTRY-CD | X(03) | `cust_addr_country_cd` | `str` | Country code |
| CUST-ADDR-ZIP | X(10) | `cust_addr_zip` | `str` | ZIP code |
| CUST-PHONE-NUM-1 | X(15) | `cust_phone_num_1` | `str` | Primary phone |
| CUST-PHONE-NUM-2 | X(15) | `cust_phone_num_2` | `str` | Secondary phone |
| CUST-SSN | 9(09) | `cust_ssn` | `str` | Social Security Number |
| CUST-GOVT-ISSUED-ID | X(20) | `cust_govt_issued_id` | `str` | Government-issued ID |
| CUST-DOB-YYYY-MM-DD | X(10) | `cust_dob_yyyy_mm_dd` | `str` | Date of birth |
| CUST-EFT-ACCOUNT-ID | X(10) | `cust_eft_account_id` | `str` | EFT account ID |
| CUST-PRI-CARD-HOLDER-IND | X(01) | `cust_pri_card_holder_ind` | `str` | Primary cardholder? |
| CUST-FICO-CREDIT-SCORE | 9(03) | `cust_fico_credit_score` | `str` | FICO score |
| FILLER | X(168) | — | — | Padding to 500 bytes |

**Relationships:**
- Referenced by `CardXrefRecord` via `XREF-CUST-ID`

---

## 5. Transaction Record

| Property | Value |
|---|---|
| **Copybook** | `CVTRA05Y.cpy` |
| **Record Length** | 350 bytes |
| **Primary Key** | `TRAN-ID` |
| **Python Class** | `TransactionRecord` |

| COBOL Field | PIC | Python Field | Python Type | Description |
|---|---|---|---|---|
| TRAN-ID | X(16) | `tran_id` | `str` | Transaction ID |
| TRAN-TYPE-CD | X(02) | `tran_type_cd` | `str` | Transaction type code |
| TRAN-CAT-CD | 9(04) | `tran_cat_cd` | `str` | Category code |
| TRAN-SOURCE | X(10) | `tran_source` | `str` | Transaction source |
| TRAN-DESC | X(100) | `tran_desc` | `str` | Description |
| TRAN-AMT | S9(09)V99 | `tran_amt` | `float` | Transaction amount |
| TRAN-MERCHANT-ID | 9(09) | `tran_merchant_id` | `str` | Merchant ID |
| TRAN-MERCHANT-NAME | X(50) | `tran_merchant_name` | `str` | Merchant name |
| TRAN-MERCHANT-CITY | X(50) | `tran_merchant_city` | `str` | Merchant city |
| TRAN-MERCHANT-ZIP | X(10) | `tran_merchant_zip` | `str` | Merchant ZIP |
| TRAN-CARD-NUM | X(16) | `tran_card_num` | `str` | Card number |
| TRAN-ORIG-TS | X(26) | `tran_orig_ts` | `str` | Origination timestamp |
| TRAN-PROC-TS | X(26) | `tran_proc_ts` | `str` | Processing timestamp |
| FILLER | X(20) | — | — | Padding to 350 bytes |

**Relationships:**
- References `CardRecord` via `TRAN-CARD-NUM`
- Categorised by `TransactionTypeRecord` and `TransactionCategoryRecord`

---

## 6. Daily Transaction Record

| Property | Value |
|---|---|
| **Copybook** | `CVTRA06Y.cpy` |
| **Record Length** | 350 bytes |
| **Python Class** | `DailyTransactionRecord` |

Same layout as Transaction Record but uses `DALYTRAN-` prefix.
Used as the daily batch input file for transaction posting.

---

## 7. Transaction Category Balance Record

| Property | Value |
|---|---|
| **Copybook** | `CVTRA01Y.cpy` |
| **Record Length** | 50 bytes |
| **Composite Key** | `TRANCAT-ACCT-ID` + `TRANCAT-TYPE-CD` + `TRANCAT-CD` |
| **Python Class** | `TranCatBalRecord` |

| COBOL Field | PIC | Python Field | Python Type | Description |
|---|---|---|---|---|
| TRANCAT-ACCT-ID | 9(11) | `trancat_acct_id` | `str` | Account ID |
| TRANCAT-TYPE-CD | X(02) | `trancat_type_cd` | `str` | Transaction type code |
| TRANCAT-CD | 9(04) | `trancat_cd` | `str` | Category code |
| TRAN-CAT-BAL | S9(09)V99 | `tran_cat_bal` | `float` | Category balance |
| FILLER | X(22) | — | — | Padding to 50 bytes |

---

## 8. Disclosure Group Record

| Property | Value |
|---|---|
| **Copybook** | `CVTRA02Y.cpy` |
| **Record Length** | 50 bytes |
| **Composite Key** | `DIS-ACCT-GROUP-ID` + `DIS-TRAN-TYPE-CD` + `DIS-TRAN-CAT-CD` |
| **Python Class** | `DisclosureGroupRecord` |

| COBOL Field | PIC | Python Field | Python Type | Description |
|---|---|---|---|---|
| DIS-ACCT-GROUP-ID | X(10) | `dis_acct_group_id` | `str` | Account group ID |
| DIS-TRAN-TYPE-CD | X(02) | `dis_tran_type_cd` | `str` | Transaction type code |
| DIS-TRAN-CAT-CD | 9(04) | `dis_tran_cat_cd` | `str` | Category code |
| DIS-INT-RATE | S9(04)V99 | `dis_int_rate` | `float` | Interest rate |
| FILLER | X(28) | — | — | Padding to 50 bytes |

**Relationships:**
- Linked to `AccountRecord` via `ACCT-GROUP-ID` → `DIS-ACCT-GROUP-ID`

---

## 9. Transaction Type Record

| Property | Value |
|---|---|
| **Copybook** | `CVTRA03Y.cpy` |
| **Record Length** | 60 bytes |
| **Primary Key** | `TRAN-TYPE` |
| **Python Class** | `TransactionTypeRecord` |

| COBOL Field | PIC | Python Field | Python Type | Description |
|---|---|---|---|---|
| TRAN-TYPE | X(02) | `tran_type` | `str` | 2-character type code |
| TRAN-TYPE-DESC | X(50) | `tran_type_desc` | `str` | Type description |
| FILLER | X(08) | — | — | Padding to 60 bytes |

---

## 10. Transaction Category Record

| Property | Value |
|---|---|
| **Copybook** | `CVTRA04Y.cpy` |
| **Record Length** | 60 bytes |
| **Composite Key** | `TRAN-TYPE-CD` + `TRAN-CAT-CD` |
| **Python Class** | `TransactionCategoryRecord` |

| COBOL Field | PIC | Python Field | Python Type | Description |
|---|---|---|---|---|
| TRAN-TYPE-CD | X(02) | `tran_type_cd` | `str` | Transaction type code |
| TRAN-CAT-CD | 9(04) | `tran_cat_cd` | `str` | Category code |
| TRAN-CAT-TYPE-DESC | X(50) | `tran_cat_type_desc` | `str` | Category description |
| FILLER | X(04) | — | — | Padding to 60 bytes |

---

## 11. User Security Record

| Property | Value |
|---|---|
| **Copybook** | `CSUSR01Y.cpy` |
| **Record Length** | 80 bytes |
| **Primary Key** | `SEC-USR-ID` |
| **Python Class** | `UserSecurityRecord` |

| COBOL Field | PIC | Python Field | Python Type | Description |
|---|---|---|---|---|
| SEC-USR-ID | X(08) | `sec_usr_id` | `str` | User ID |
| SEC-USR-FNAME | X(20) | `sec_usr_fname` | `str` | First name |
| SEC-USR-LNAME | X(20) | `sec_usr_lname` | `str` | Last name |
| SEC-USR-PWD | X(08) | `sec_usr_pwd` | `str` | Password |
| SEC-USR-TYPE | X(01) | `sec_usr_type` | `str` | User type (A=Admin, U=User) |
| SEC-USR-FILLER | X(23) | — | — | Padding to 80 bytes |

---

## 12. Transaction Index Record

| Property | Value |
|---|---|
| **Copybook** | `COSTM01.CPY` |
| **Composite Key** | `TRNX-CARD-NUM` + `TRNX-ID` |
| **Python Class** | `TransactionIndexRecord` |

Alternate-index layout for transactions, keyed by card number + transaction ID.
Used by the batch report program. Same transaction fields as `TransactionRecord`
but reorganised under the `TRNX-` prefix.

| COBOL Field | PIC | Python Field | Python Type | Description |
|---|---|---|---|---|
| TRNX-CARD-NUM | X(16) | `trnx_card_num` | `str` | Card number (key part 1) |
| TRNX-ID | X(16) | `trnx_id` | `str` | Transaction ID (key part 2) |
| TRNX-TYPE-CD | X(02) | `trnx_type_cd` | `str` | Transaction type code |
| TRNX-CAT-CD | 9(04) | `trnx_cat_cd` | `str` | Category code |
| TRNX-SOURCE | X(10) | `trnx_source` | `str` | Transaction source |
| TRNX-DESC | X(100) | `trnx_desc` | `str` | Description |
| TRNX-AMT | S9(09)V99 | `trnx_amt` | `float` | Transaction amount |
| TRNX-MERCHANT-ID | 9(09) | `trnx_merchant_id` | `str` | Merchant ID |
| TRNX-MERCHANT-NAME | X(50) | `trnx_merchant_name` | `str` | Merchant name |
| TRNX-MERCHANT-CITY | X(50) | `trnx_merchant_city` | `str` | Merchant city |
| TRNX-MERCHANT-ZIP | X(10) | `trnx_merchant_zip` | `str` | Merchant ZIP |
| TRNX-ORIG-TS | X(26) | `trnx_orig_ts` | `str` | Origination timestamp |
| TRNX-PROC-TS | X(26) | `trnx_proc_ts` | `str` | Processing timestamp |
| FILLER | X(20) | — | — | Padding |

---

## Entity Relationship Summary

```
CustomerRecord (CUST-ID)
    │
    └──< CardXrefRecord (XREF-CUST-ID, XREF-ACCT-ID, XREF-CARD-NUM)
              │                │
              │                └──> AccountRecord (ACCT-ID)
              │                         │
              │                         ├──> DisclosureGroupRecord (via ACCT-GROUP-ID)
              │                         └──> TranCatBalRecord (via TRANCAT-ACCT-ID)
              │
              └──> CardRecord (CARD-NUM, CARD-ACCT-ID)
                       │
                       └──> TransactionRecord (TRAN-CARD-NUM)
                                │
                                ├──> TransactionTypeRecord (TRAN-TYPE-CD)
                                └──> TransactionCategoryRecord (TRAN-TYPE-CD + TRAN-CAT-CD)

UserSecurityRecord (SEC-USR-ID) — independent, used for authentication
```
