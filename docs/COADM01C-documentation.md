# COADM01C — Admin Menu

## Overview

COADM01C is the CICS COBOL program that displays the admin menu for admin users in the CardDemo application. It is invoked via CICS transaction **CA00** after a successful admin login. The program presents admin-specific functions, validates the user's selection, and transfers control to the corresponding program.

## Program Identification

| Attribute       | Value      |
|-----------------|------------|
| Program ID      | COADM01C   |
| Transaction ID  | CA00       |
| Application     | CardDemo   |
| Type            | CICS COBOL |
| BMS Map         | COADM1A (mapset COADM01) |

## Menu Options

Defined in copybook COADM02Y. There are 6 options:

| # | Option Name                           | Program  |
|---|---------------------------------------|----------|
| 1 | User List (Security)                  | COUSR00C |
| 2 | User Add (Security)                   | COUSR01C |
| 3 | User Update (Security)                | COUSR02C |
| 4 | User Delete (Security)                | COUSR03C |
| 5 | Transaction Type List/Update (Db2)    | COTRTLIC |
| 6 | Transaction Type Maintenance (Db2)    | COTRTUPC |

## Input Fields

| Field  | Source           | COBOL Variable        | Description                |
|--------|------------------|-----------------------|----------------------------|
| Option | BMS map COADM1A  | OPTIONI OF COADM1AI   | 2-digit menu option number |

## Output / Behaviour

### Successful Selection
On a valid option selection with a non-DUMMY program name:
1. Sets COMMAREA fields:
   - `CDEMO-FROM-TRANID` ← CA00
   - `CDEMO-FROM-PROGRAM` ← COADM01C
   - `CDEMO-PGM-CONTEXT` ← 0 (initial entry)
2. Transfers control (XCTL) to the selected program.

### Special Cases
- **DUMMY* programs**: If the program name starts with `DUMMY`, the XCTL is skipped and a "not installed" message is shown.
- **PGMIDERR handler**: If the target program is not installed (CICS PGMIDERR condition), a "not installed" message is shown and control returns to the menu.

### Error Conditions

| Condition                    | Error Message                                    |
|------------------------------|--------------------------------------------------|
| Option is not numeric        | `Please enter a valid option number...`          |
| Option is zero               | `Please enter a valid option number...`          |
| Option exceeds max (>6)      | `Please enter a valid option number...`          |
| Program not installed        | `This option is not installed ...`               |
| Invalid key pressed          | `Invalid key pressed. Please see below...`       |

### Special Keys
- **ENTER**: Process menu selection
- **PF3**: Return to sign-on screen (COSGN00C)

## Data Structures

### Admin Menu Option Record (COADM02Y)

Each of the 9 option slots (6 used) contains:

| Field                    | PIC     | Description              |
|--------------------------|---------|--------------------------|
| CDEMO-ADMIN-OPT-NUM     | 9(02)   | Option number            |
| CDEMO-ADMIN-OPT-NAME    | X(35)   | Display name             |
| CDEMO-ADMIN-OPT-PGMNAME | X(08)   | Target program name      |

Note: Unlike the user menu, admin options do not have a user-type field since all options are admin-only.

### COMMAREA (COCOM01Y)
Key fields: `CDEMO-FROM-TRANID`, `CDEMO-FROM-PROGRAM`, `CDEMO-TO-PROGRAM`, `CDEMO-PGM-CONTEXT`

## Copybooks Used

| Copybook | Purpose                                    |
|----------|--------------------------------------------|
| COCOM01Y | COMMAREA layout                            |
| COADM02Y | Admin menu option definitions (6 options)  |
| COADM01  | BMS map for admin menu screen              |
| COTTL01Y | Screen title constants                     |
| CSDAT01Y | Date/time working storage                  |
| CSMSG01Y | Common messages                            |
| CSUSR01Y | User security record layout                |
| DFHAID   | CICS attention identifier constants        |
| DFHBMSCA | BMS attribute constants                    |

## Program Flow

```
MAIN-PARA
├── HANDLE CONDITION PGMIDERR → PGMIDERR-ERR-PARA
├── No COMMAREA (EIBCALEN=0): Return to sign-on screen
└── Has COMMAREA:
    ├── First entry (PGM-CONTEXT=0): Send admin menu screen
    └── Re-entry (PGM-CONTEXT=1):
        ├── ENTER key → PROCESS-ENTER-KEY
        │   ├── Parse and validate option number
        │   └── If not DUMMY*: set COMMAREA, XCTL to program
        │   └── If DUMMY*: show "not installed" message
        ├── PF3 → Return to sign-on (COSGN00C)
        └── Other key → Invalid key error
```
