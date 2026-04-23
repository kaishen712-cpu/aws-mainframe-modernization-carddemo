# COMEN01C — Main Menu (Regular Users)

## Overview

COMEN01C is the CICS COBOL program that displays the main menu for regular (non-admin) users in the CardDemo application. It is invoked via CICS transaction **CM00** after a successful login. The program presents a list of available functions, validates the user's selection, and transfers control to the corresponding program.

## Program Identification

| Attribute       | Value      |
|-----------------|------------|
| Program ID      | COMEN01C   |
| Transaction ID  | CM00       |
| Application     | CardDemo   |
| Type            | CICS COBOL |
| BMS Map         | COMEN1A (mapset COMEN01) |

## Menu Options

Defined in copybook COMEN02Y. There are 11 options:

| # | Option Name                    | Program  | User Type |
|---|--------------------------------|----------|-----------|
| 1 | Account View                   | COACTVWC | U         |
| 2 | Account Update                 | COACTUPC | U         |
| 3 | Credit Card List               | COCRDLIC | U         |
| 4 | Credit Card View               | COCRDSLC | U         |
| 5 | Credit Card Update             | COCRDUPC | U         |
| 6 | Transaction List               | COTRN00C | U         |
| 7 | Transaction View               | COTRN01C | U         |
| 8 | Transaction Add                | COTRN02C | U         |
| 9 | Transaction Reports            | CORPT00C | U         |
| 10| Bill Payment                   | COBIL00C | U         |
| 11| Pending Authorization View     | COPAUS0C | U         |

## Input Fields

| Field  | Source           | COBOL Variable        | Description                |
|--------|------------------|-----------------------|----------------------------|
| Option | BMS map COMEN1A  | OPTIONI OF COMEN1AI   | 2-digit menu option number |

## Output / Behaviour

### Successful Selection
On a valid option selection, the program:
1. Sets COMMAREA fields:
   - `CDEMO-FROM-TRANID` ← CM00
   - `CDEMO-FROM-PROGRAM` ← COMEN01C
   - `CDEMO-PGM-CONTEXT` ← 0 (initial entry)
2. Transfers control (XCTL) to the selected program.

### Special Cases
- **COPAUS0C (Pending Auth View)**: The program first checks whether the program is installed via CICS INQUIRE PROGRAM. If not installed, it shows an error message instead of transferring.
- **DUMMY* programs**: If the program name starts with `DUMMY`, a "coming soon" message is displayed.

### Error Conditions

| Condition                        | Error Message                                    |
|----------------------------------|--------------------------------------------------|
| Option is not numeric            | `Please enter a valid option number...`          |
| Option is zero                   | `Please enter a valid option number...`          |
| Option exceeds max (>11)         | `Please enter a valid option number...`          |
| Admin-only option selected by user | `No access - Admin Only option...`             |
| Program not installed (COPAUS0C) | `This option <name> is not installed...`         |
| DUMMY program                    | `This option <name> is coming soon ...`          |
| Invalid key pressed              | `Invalid key pressed. Please see below...`       |

### Special Keys
- **ENTER**: Process menu selection
- **PF3**: Sign off — return to sign-on screen (COSGN00C)

## Data Structures

### Menu Option Record (COMEN02Y)

Each of the 12 option slots (11 used) contains:

| Field                   | PIC     | Description              |
|-------------------------|---------|--------------------------|
| CDEMO-MENU-OPT-NUM     | 9(02)   | Option number            |
| CDEMO-MENU-OPT-NAME    | X(35)   | Display name             |
| CDEMO-MENU-OPT-PGMNAME | X(08)   | Target program name      |
| CDEMO-MENU-OPT-USRTYPE | X(01)   | Required user type (U/A) |

### COMMAREA (COCOM01Y)
Key fields: `CDEMO-FROM-TRANID`, `CDEMO-FROM-PROGRAM`, `CDEMO-TO-PROGRAM`, `CDEMO-USER-TYPE`, `CDEMO-PGM-CONTEXT`

## Copybooks Used

| Copybook | Purpose                                    |
|----------|--------------------------------------------|
| COCOM01Y | COMMAREA layout                            |
| COMEN02Y | Menu option definitions (11 options)       |
| COMEN01  | BMS map for main menu screen               |
| COTTL01Y | Screen title constants                     |
| CSDAT01Y | Date/time working storage                  |
| CSMSG01Y | Common messages                            |
| CSUSR01Y | User security record layout                |
| DFHAID   | CICS attention identifier constants        |
| DFHBMSCA | BMS attribute constants                    |

## Program Flow

```
MAIN-PARA
├── No COMMAREA (EIBCALEN=0): Return to sign-on screen
└── Has COMMAREA:
    ├── First entry (PGM-CONTEXT=0): Send menu screen
    └── Re-entry (PGM-CONTEXT=1):
        ├── ENTER key → PROCESS-ENTER-KEY
        │   ├── Parse and validate option number
        │   ├── Check user-type access
        │   └── Transfer to selected program (XCTL)
        │       ├── COPAUS0C: check if installed first
        │       ├── DUMMY*: show "coming soon" message
        │       └── Other: direct XCTL
        ├── PF3 → Return to sign-on (COSGN00C)
        └── Other key → Invalid key error
```
