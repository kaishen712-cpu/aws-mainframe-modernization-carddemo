# COUSR01C - Add User Program

## Overview

**Program ID:** COUSR01C  
**Application:** CardDemo (AWS Mainframe Modernization)  
**Type:** CICS COBOL Online Program  
**Transaction ID:** CU01  
**Function:** Add a new Regular/Admin user to the USRSEC file  

COUSR01C is an interactive CICS program that allows an admin user to add a new
user record to the USRSEC VSAM file. It presents a BMS map-based screen where
the admin fills in user details, validates all fields, and writes the new record.
The program is part of the CardDemo credit card management system and is invoked
from the Admin Menu (COADM01C).

---

## Program Structure

### Division Layout

| Division | Purpose |
|---|---|
| Identification | Declares program name (`COUSR01C`) and author (`AWS`) |
| Environment | Configuration section (no special environment settings) |
| Data | Working-Storage variables, copybook includes, Linkage Section |
| Procedure | All business logic paragraphs |

### Key Copybooks Used

| Copybook | Purpose |
|---|---|
| `COCOM01Y` | Communication area (COMMAREA) shared across CardDemo programs |
| `COUSR01` | BMS map I/O areas for the Add User screen (COUSR1AI / COUSR1AO) |
| `COTTL01Y` | Screen title constants |
| `CSDAT01Y` | Date/time formatting working storage |
| `CSMSG01Y` | Common message constants (e.g., invalid key message) |
| `CSUSR01Y` | User security record layout (SEC-USER-DATA, 80 bytes) |
| `DFHAID` | CICS attention identifier constants (Enter, PF keys) |
| `DFHBMSCA` | BMS attribute constants |

### VSAM Files Accessed

| Logical Name | Variable | Purpose |
|---|---|---|
| USRSEC | `WS-USRSEC-FILE` | User security master file (write) |

---

## Program Flow

```
MAIN-PARA
  |
  |-- If no COMMAREA (EIBCALEN = 0) --> return to sign-on screen (COSGN00C)
  |
  |-- First entry (PGM-ENTER):
  |     |-- Initialize screen to LOW-VALUES
  |     |-- SEND-USRADD-SCREEN
  |
  |-- Re-entry (PGM-REENTER):
        |-- RECEIVE-USRADD-SCREEN
        |-- Evaluate key pressed:
              |-- ENTER  --> PROCESS-ENTER-KEY
              |-- PF3    --> RETURN-TO-PREV-SCREEN (Admin Menu)
              |-- PF4    --> CLEAR-CURRENT-SCREEN
              |-- Other  --> Display "Invalid key" message
```

### PROCESS-ENTER-KEY

1. Validate all fields in order (stops at first error):
   - First Name must not be empty
   - Last Name must not be empty
   - User ID must not be empty
   - Password must not be empty
   - User Type must not be empty
2. If all valid, move screen fields to SEC-USER-DATA record
3. Call WRITE-USER-SEC-FILE

### WRITE-USER-SEC-FILE

1. Write the SEC-USER-DATA record to USRSEC with SEC-USR-ID as key
2. On NORMAL response: clear all fields, display success message
3. On DUPKEY/DUPREC: display "User ID already exist..."
4. On other errors: display "Unable to Add User..."

---

## Input Fields

| Screen Field | COBOL Field | Type | Length | Description |
|---|---|---|---|---|
| First Name | `FNAMEI` | Alphanumeric | 20 | User's first name |
| Last Name | `LNAMEI` | Alphanumeric | 20 | User's last name |
| User ID | `USERIDI` | Alphanumeric | 8 | Unique user identifier |
| Password | `PASSWDI` | Alphanumeric | 8 | User's password |
| User Type | `USRTYPEI` | Character | 1 | 'A' (Admin) or 'U' (Regular) |

---

## Outputs

### Screen Output

The program sends the `COUSR1A` map back to the terminal, which includes:
- Header information: application title, transaction name, program name, current date and time
- All input fields (pre-populated or echoed back)
- An error/info message line (`ERRMSGO`)
- On success: a green message reading `"User <ID> has been added ..."`

### Data Output

A new record is written to the USRSEC VSAM file with this layout:

| Field | PIC | Length | Source |
|---|---|---|---|
| `SEC-USR-ID` | X(08) | 8 | User ID input (primary key) |
| `SEC-USR-FNAME` | X(20) | 20 | First Name input |
| `SEC-USR-LNAME` | X(20) | 20 | Last Name input |
| `SEC-USR-PWD` | X(08) | 8 | Password input |
| `SEC-USR-TYPE` | X(01) | 1 | User Type input |
| `SEC-USR-FILLER` | X(23) | 23 | Unused padding |

**Total record length: 80 bytes**

---

## Business Rules

### 1. Authentication / Session Check
- If no COMMAREA is passed (EIBCALEN = 0), the program redirects to the
  sign-on screen (`COSGN00C`). This prevents unauthenticated access.

### 2. Required Fields (validated in order)
All of the following fields are mandatory (cannot be blank):
1. First Name
2. Last Name
3. User ID
4. Password
5. User Type

Validation stops at the first empty field and positions the cursor there.

### 3. Duplicate Detection
- If the User ID already exists in the USRSEC file (DUPKEY/DUPREC response
  from CICS WRITE), the program displays "User ID already exist..."

### 4. Screen Navigation

| Key | Action |
|---|---|
| Enter | Validate and add the user |
| PF3 | Return to Admin Menu (COADM01C) |
| PF4 | Clear all input fields |
| Any other | Display "Invalid key pressed" message |

---

## Error Handling

- Validation errors display specific field-level messages and position the
  cursor at the offending field.
- VSAM WRITE errors:
  - DUPKEY/DUPREC: "User ID already exist..."
  - Other: "Unable to Add User..."
- All errors are displayed in the `ERRMSGO` field of the output map.
