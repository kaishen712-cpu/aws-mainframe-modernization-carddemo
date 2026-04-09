# COUSR03C - Delete User Program

## Overview

**Program ID:** COUSR03C  
**Application:** CardDemo (AWS Mainframe Modernization)  
**Type:** CICS COBOL Online Program  
**Transaction ID:** CU03  
**Function:** Delete a user from the USRSEC file  

COUSR03C is an interactive CICS program that allows an admin user to delete
a user record from the USRSEC VSAM file. It reads and displays the user
record for confirmation, then deletes it upon the admin's explicit request.
The program is part of the CardDemo credit card management system and is
invoked from the User List screen (COUSR00C) when 'D' is selected.

---

## Program Structure

### Division Layout

| Division | Purpose |
|---|---|
| Identification | Declares program name (`COUSR03C`) and author (`AWS`) |
| Environment | Configuration section (no special environment settings) |
| Data | Working-Storage variables, copybook includes, Linkage Section |
| Procedure | All business logic paragraphs |

### Key Copybooks Used

| Copybook | Purpose |
|---|---|
| `COCOM01Y` | Communication area (COMMAREA) shared across CardDemo programs |
| `COUSR03` | BMS map I/O areas for the Delete User screen (COUSR3AI / COUSR3AO) |
| `COTTL01Y` | Screen title constants |
| `CSDAT01Y` | Date/time formatting working storage |
| `CSMSG01Y` | Common message constants (e.g., invalid key message) |
| `CSUSR01Y` | User security record layout (SEC-USER-DATA, 80 bytes) |
| `DFHAID` | CICS attention identifier constants (Enter, PF keys) |
| `DFHBMSCA` | BMS attribute constants |

### VSAM Files Accessed

| Logical Name | Variable | Purpose |
|---|---|---|
| USRSEC | `WS-USRSEC-FILE` | User security master file (read-update / delete) |

---

## Program Flow

```
MAIN-PARA
  |
  |-- If no COMMAREA (EIBCALEN = 0) --> return to sign-on screen (COSGN00C)
  |
  |-- First entry (PGM-ENTER):
  |     |-- Initialize screen to LOW-VALUES
  |     |-- If a user was pre-selected (from COUSR00C), populate user ID
  |     |     and run PROCESS-ENTER-KEY to load the record
  |     |-- SEND-USRDEL-SCREEN
  |
  |-- Re-entry (PGM-REENTER):
        |-- RECEIVE-USRDEL-SCREEN
        |-- Evaluate key pressed:
              |-- ENTER  --> PROCESS-ENTER-KEY (look up user)
              |-- PF3    --> RETURN-TO-PREV-SCREEN
              |-- PF4    --> CLEAR-CURRENT-SCREEN
              |-- PF5    --> DELETE-USER-INFO (confirm delete)
              |-- PF12   --> RETURN-TO-PREV-SCREEN (Admin Menu)
              |-- Other  --> Display "Invalid key" message
```

### PROCESS-ENTER-KEY

1. Validate User ID is not empty
2. Clear display fields (First Name, Last Name, User Type)
3. Read the user record from USRSEC (with UPDATE lock)
4. If found, populate display fields from the record
5. Display message: "Press PF5 key to delete this user ..."

### DELETE-USER-INFO (PF5)

1. Validate User ID is not empty
2. Read the user record from USRSEC (with UPDATE lock)
3. Delete the record from USRSEC
4. On success: clear all fields, display "User <ID> has been deleted ..."
5. On error: display appropriate error message

---

## Display Fields

| Screen Field | COBOL Field | Type | Length | Description |
|---|---|---|---|---|
| User ID | `USRIDINI` | Alphanumeric | 8 | User identifier (input for lookup) |
| First Name | `FNAMEI` | Alphanumeric | 20 | User's first name (display only) |
| Last Name | `LNAMEI` | Alphanumeric | 20 | User's last name (display only) |
| User Type | `USRTYPEI` | Character | 1 | 'A' (Admin) or 'U' (Regular) (display only) |

Note: Unlike the Update screen (COUSR02C), the Delete screen does NOT display
the Password field — it only shows the user's name and type for confirmation.

---

## Business Rules

### 1. Authentication / Session Check
- If no COMMAREA is passed (EIBCALEN = 0), the program redirects to the
  sign-on screen (`COSGN00C`).

### 2. Two-Step Deletion Process
The deletion requires two explicit steps:
1. **Enter** or initial load: Looks up the user and displays their details
   with the prompt "Press PF5 key to delete this user ..."
2. **PF5**: Actually performs the deletion

This prevents accidental deletions by requiring the admin to see the user
details before confirming.

### 3. Self-Deletion Prevention
- The program should prevent deleting the currently signed-in user to avoid
  locking the admin out of the system.

### 4. Required Fields
- User ID must not be empty (validated before both lookup and delete).

### 5. Screen Navigation

| Key | Action |
|---|---|
| Enter | Look up and display the user record for confirmation |
| PF3 | Return to previous screen |
| PF4 | Clear all fields |
| PF5 | Confirm and delete the user |
| PF12 | Return to Admin Menu |
| Any other | Display "Invalid key pressed" message |

---

## Error Handling

- Validation errors display specific messages and position the cursor at
  the User ID field.
- VSAM READ errors:
  - NOTFND: "User ID NOT found..."
  - Other: "Unable to lookup User..."
- VSAM DELETE errors:
  - NOTFND: "User ID NOT found..."
  - Other: "Unable to Update User..." (note: the COBOL program uses this
    message text even for delete errors)
- All errors are displayed in the `ERRMSGO` field of the output map.

---

## Working Storage Variables

| Variable | Type | Purpose |
|---|---|---|
| WS-PGMNAME | PIC X(08) | Program name constant ('COUSR03C') |
| WS-TRANID | PIC X(04) | Transaction ID constant ('CU03') |
| WS-MESSAGE | PIC X(80) | Message to display on screen |
| WS-USRSEC-FILE | PIC X(08) | VSAM file name ('USRSEC') |
| WS-ERR-FLG | PIC X(01) | Error flag ('Y'/'N') |
| WS-USR-MODIFIED | PIC X(01) | User modified flag (unused in delete) |
| CDEMO-CU03-USR-SELECTED | PIC X(08) | Pre-selected user ID from list screen |
