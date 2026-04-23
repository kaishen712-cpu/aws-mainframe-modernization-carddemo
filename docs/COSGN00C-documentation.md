# COSGN00C — Sign-on Screen

## Overview

COSGN00C is the CICS COBOL program that implements the sign-on (login) screen for the CardDemo application. It is the entry point for all users and is invoked via CICS transaction **CC00**. The program authenticates users by validating their credentials against the USRSEC VSAM file and routes them to the appropriate menu based on their user type.

## Program Identification

| Attribute       | Value      |
|-----------------|------------|
| Program ID      | COSGN00C   |
| Transaction ID  | CC00       |
| Application     | CardDemo   |
| Type            | CICS COBOL |
| BMS Map         | COSGN0A (mapset COSGN00) |

## Input Fields

| Field    | Source              | COBOL Variable           | Description                        |
|----------|---------------------|--------------------------|------------------------------------|
| User ID  | BMS map COSGN0A     | USERIDI OF COSGN0AI      | 8-character user identifier        |
| Password | BMS map COSGN0A     | PASSWDI OF COSGN0AI      | 8-character password               |

Both fields are uppercased before processing.

## Output / Behaviour

### Successful Login
On successful authentication the program:
1. Populates the COMMAREA (COCOM01Y) with:
   - `CDEMO-FROM-TRANID` ← CC00
   - `CDEMO-FROM-PROGRAM` ← COSGN00C
   - `CDEMO-USER-ID` ← authenticated user ID
   - `CDEMO-USER-TYPE` ← user type from USRSEC record
   - `CDEMO-PGM-CONTEXT` ← 0 (initial entry)
2. Transfers control (XCTL) to:
   - **COADM01C** if user type is `'A'` (admin)
   - **COMEN01C** if user type is `'U'` (regular user)

### Error Conditions

| Condition                | Error Message                              | Cursor Position |
|--------------------------|--------------------------------------------|-----------------|
| User ID is empty/blank   | `Please enter User ID ...`                | User ID field   |
| Password is empty/blank  | `Please enter Password ...`               | Password field  |
| User ID not found (RESP=13) | `User not found. Try again ...`        | User ID field   |
| Wrong password           | `Wrong Password. Try again ...`           | Password field  |
| VSAM read error (other)  | `Unable to verify the User ...`           | User ID field   |
| Invalid key pressed      | `Invalid key pressed. Please see below...`| —               |

### Special Keys
- **ENTER**: Process login credentials
- **PF3**: Exit the application with a thank-you message

## Data Structures

### USRSEC Record (CSUSR01Y)

| Field          | PIC       | Length | Description         |
|----------------|-----------|--------|---------------------|
| SEC-USR-ID     | X(08)     | 8      | User identifier     |
| SEC-USR-FNAME  | X(20)     | 20     | First name          |
| SEC-USR-LNAME  | X(20)     | 20     | Last name           |
| SEC-USR-PWD    | X(08)     | 8      | Password            |
| SEC-USR-TYPE   | X(01)     | 1      | A=Admin, U=Regular  |
| SEC-USR-FILLER | X(23)     | 23     | Filler              |

### COMMAREA (COCOM01Y)
See COCOM01Y copybook. Key fields used by this program:
- `CDEMO-FROM-TRANID`, `CDEMO-FROM-PROGRAM`, `CDEMO-USER-ID`, `CDEMO-USER-TYPE`, `CDEMO-PGM-CONTEXT`

## Copybooks Used

| Copybook | Purpose                                    |
|----------|--------------------------------------------|
| COCOM01Y | COMMAREA layout                            |
| COSGN00  | BMS map for sign-on screen                 |
| COTTL01Y | Screen title constants                     |
| CSDAT01Y | Date/time working storage                  |
| CSMSG01Y | Common messages (thank-you, invalid key)   |
| CSUSR01Y | User security record layout                |
| DFHAID   | CICS attention identifier constants        |
| DFHBMSCA | BMS attribute constants                    |

## Program Flow

```
MAIN-PARA
├── First time (EIBCALEN=0): Send blank sign-on screen
└── Subsequent (EIBCALEN>0):
    ├── ENTER key → PROCESS-ENTER-KEY
    │   ├── Validate User ID not empty
    │   ├── Validate Password not empty
    │   ├── Uppercase both fields
    │   └── READ-USER-SEC-FILE
    │       ├── RESP=0 (found):
    │       │   ├── Password matches → set COMMAREA, XCTL to menu
    │       │   └── Password wrong → error message
    │       ├── RESP=13 (not found) → error message
    │       └── Other → error message
    ├── PF3 → Send thank-you text, RETURN (exit)
    └── Other key → Invalid key error
```
