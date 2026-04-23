# COUSR02C - Update User Program

## Overview

**Program ID:** COUSR02C  
**Application:** CardDemo (AWS Mainframe Modernization)  
**Type:** CICS COBOL Online Program  
**Transaction ID:** CU02  
**Function:** Update an existing user in the USRSEC file  

COUSR02C is an interactive CICS program that allows an admin user to update
an existing user record in the USRSEC VSAM file. It reads the current user
data, displays it for editing, detects which fields have changed, and writes
the update. The program is part of the CardDemo credit card management system
and is invoked from the User List screen (COUSR00C) when 'U' is selected.

---

## Program Structure

### Division Layout

| Division | Purpose |
|---|---|
| Identification | Declares program name (`COUSR02C`) and author (`AWS`) |
| Environment | Configuration section (no special environment settings) |
| Data | Working-Storage variables, copybook includes, Linkage Section |
| Procedure | All business logic paragraphs |

### Key Copybooks Used

| Copybook | Purpose |
|---|---|
| `COCOM01Y` | Communication area (COMMAREA) shared across CardDemo programs |
| `COUSR02` | BMS map I/O areas for the Update User screen (COUSR2AI / COUSR2AO) |
| `COTTL01Y` | Screen title constants |
| `CSDAT01Y` | Date/time formatting working storage |
| `CSMSG01Y` | Common message constants (e.g., invalid key message) |
| `CSUSR01Y` | User security record layout (SEC-USER-DATA, 80 bytes) |
| `DFHAID` | CICS attention identifier constants (Enter, PF keys) |
| `DFHBMSCA` | BMS attribute constants |

### VSAM Files Accessed

| Logical Name | Variable | Purpose |
|---|---|---|
| USRSEC | `WS-USRSEC-FILE` | User security master file (read-update / rewrite) |

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
  |     |-- SEND-USRUPD-SCREEN
  |
  |-- Re-entry (PGM-REENTER):
        |-- RECEIVE-USRUPD-SCREEN
        |-- Evaluate key pressed:
              |-- ENTER  --> PROCESS-ENTER-KEY (look up user)
              |-- PF3    --> UPDATE-USER-INFO then RETURN-TO-PREV-SCREEN
              |-- PF4    --> CLEAR-CURRENT-SCREEN
              |-- PF5    --> UPDATE-USER-INFO (save changes)
              |-- PF12   --> RETURN-TO-PREV-SCREEN (Admin Menu)
              |-- Other  --> Display "Invalid key" message
```

### PROCESS-ENTER-KEY

1. Validate User ID is not empty
2. Clear display fields (First Name, Last Name, Password, User Type)
3. Read the user record from USRSEC (with UPDATE lock)
4. If found, populate display fields from the record
5. Display message: "Press PF5 key to save your updates ..."

### UPDATE-USER-INFO (PF5 / PF3)

1. Validate all fields:
   - User ID must not be empty
   - First Name must not be empty
   - Last Name must not be empty
   - Password must not be empty
   - User Type must not be empty
2. Read the existing record from USRSEC (with UPDATE lock)
3. Compare each field to detect changes:
   - First Name changed? → update, set modified flag
   - Last Name changed? → update, set modified flag
   - Password changed? → update, set modified flag
   - User Type changed? → update, set modified flag
4. If no modifications detected, display "Please modify to update ..."
5. If modified, REWRITE the record

---

## Input Fields

| Screen Field | COBOL Field | Type | Length | Description |
|---|---|---|---|---|
| User ID | `USRIDINI` | Alphanumeric | 8 | User identifier (read-only key) |
| First Name | `FNAMEI` | Alphanumeric | 20 | User's first name |
| Last Name | `LNAMEI` | Alphanumeric | 20 | User's last name |
| Password | `PASSWDI` | Alphanumeric | 8 | User's password |
| User Type | `USRTYPEI` | Character | 1 | 'A' (Admin) or 'U' (Regular) |

---

## Business Rules

### 1. Authentication / Session Check
- If no COMMAREA is passed (EIBCALEN = 0), the program redirects to the
  sign-on screen (`COSGN00C`).

### 2. User ID is Read-Only
- The User ID field is the primary key and cannot be changed. It is used
  to look up the existing record.

### 3. Required Fields (validated in order)
All fields must be non-empty:
1. User ID
2. First Name
3. Last Name
4. Password
5. User Type

### 4. Change Detection
- The program compares each editable field against the existing record.
- Only modified fields are applied to the record.
- If no fields were changed, the program displays "Please modify to update ..."
  and does NOT write to the file.

### 5. Confirmation via PF5
- Changes are only saved when the user presses PF5 (or PF3 which also
  triggers an update before returning).
- Simply pressing Enter only loads/refreshes the user record.

### 6. Screen Navigation

| Key | Action |
|---|---|
| Enter | Look up and display the user record |
| PF3 | Save changes and return to previous screen |
| PF4 | Clear all fields |
| PF5 | Save changes |
| PF12 | Return to Admin Menu without saving |
| Any other | Display "Invalid key pressed" message |

---

## Error Handling

- Validation errors display specific field-level messages and position the
  cursor at the offending field.
- VSAM READ errors:
  - NOTFND: "User ID NOT found..."
  - Other: "Unable to lookup User..."
- VSAM REWRITE errors:
  - NOTFND: "User ID NOT found..."
  - Other: "Unable to Update User..."
- All errors are displayed in the `ERRMSGO` field of the output map.
