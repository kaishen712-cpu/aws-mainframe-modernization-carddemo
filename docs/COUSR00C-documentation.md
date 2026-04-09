# COUSR00C - User List Program

## Overview

**Program ID:** COUSR00C  
**Application:** CardDemo (AWS Mainframe Modernization)  
**Type:** CICS COBOL Online Program  
**Transaction ID:** CU00  
**Function:** List all users from the USRSEC file with paginated browsing  

COUSR00C is an interactive CICS program that displays a paginated list of all
users stored in the USRSEC VSAM file. It presents a BMS map-based screen where
an admin user can browse through users page by page (10 per page), and select
a user for update or delete operations. The program is part of the CardDemo
credit card management system and is invoked from the Admin Menu (COADM01C).

---

## Program Structure

### Division Layout

| Division | Purpose |
|---|---|
| Identification | Declares program name (`COUSR00C`) and author (`AWS`) |
| Environment | Configuration section (no special environment settings) |
| Data | Working-Storage variables, copybook includes, Linkage Section |
| Procedure | All business logic paragraphs |

### Key Copybooks Used

| Copybook | Purpose |
|---|---|
| `COCOM01Y` | Communication area (COMMAREA) shared across CardDemo programs |
| `COUSR00` | BMS map I/O areas for the User List screen (COUSR0AI / COUSR0AO) |
| `COTTL01Y` | Screen title constants |
| `CSDAT01Y` | Date/time formatting working storage |
| `CSMSG01Y` | Common message constants (e.g., invalid key message) |
| `CSUSR01Y` | User security record layout (SEC-USER-DATA, 80 bytes) |
| `DFHAID` | CICS attention identifier constants (Enter, PF keys) |
| `DFHBMSCA` | BMS attribute constants |

### VSAM Files Accessed

| Logical Name | Variable | Purpose |
|---|---|---|
| USRSEC | `WS-USRSEC-FILE` | User security master file (browse/read) |

---

## Program Flow

```
MAIN-PARA
  |
  |-- If no COMMAREA (EIBCALEN = 0) --> return to sign-on screen (COSGN00C)
  |
  |-- First entry (PGM-ENTER):
  |     |-- Initialize screen to LOW-VALUES
  |     |-- PROCESS-ENTER-KEY → PROCESS-PAGE-FORWARD
  |     |-- SEND-USRLST-SCREEN
  |
  |-- Re-entry (PGM-REENTER):
        |-- RECEIVE-USRLST-SCREEN
        |-- Evaluate key pressed:
              |-- ENTER  --> PROCESS-ENTER-KEY (check selection, browse forward)
              |-- PF3    --> RETURN-TO-PREV-SCREEN (Admin Menu)
              |-- PF7    --> PROCESS-PF7-KEY (page backward)
              |-- PF8    --> PROCESS-PF8-KEY (page forward)
              |-- Other  --> Display "Invalid key" message
```

### PROCESS-ENTER-KEY

1. Check all 10 selection fields (SEL0001I through SEL0010I) for a non-blank value
2. If a selection is found:
   - 'U'/'u' → transfer to Update User (COUSR02C) via XCTL
   - 'D'/'d' → transfer to Delete User (COUSR03C) via XCTL
   - Other → display "Invalid selection" error
3. Read the starting User ID from the input field
4. Reset page number to 0
5. Call PROCESS-PAGE-FORWARD to populate the list

### PROCESS-PAGE-FORWARD

1. STARTBR on USRSEC at the starting user ID
2. Skip the starting record if navigating by key (READNEXT)
3. Initialize all 10 display rows to spaces
4. Loop READNEXT up to 10 times, populating rows with user data
5. After filling the page, do one more READNEXT to check if more records exist
6. Increment page number; set has-next-page flag accordingly
7. ENDBR and send the screen

### PROCESS-PAGE-BACKWARD

1. STARTBR on USRSEC at the first displayed user ID
2. Skip the starting record (READPREV)
3. Initialize all 10 display rows to spaces
4. Loop READPREV up to 10 times (filling from row 10 down to row 1)
5. Decrement page number
6. ENDBR and send the screen

---

## Display Fields

Each row in the user list shows:

| Screen Field | Source | Description |
|---|---|---|
| Selection | User input | Single character: U(pdate) or D(elete) |
| User ID | SEC-USR-ID | 8-character user identifier |
| First Name | SEC-USR-FNAME | User's first name (20 chars) |
| Last Name | SEC-USR-LNAME | User's last name (20 chars) |
| User Type | SEC-USR-TYPE | 'A' (Admin) or 'U' (Regular) |

The screen displays up to 10 rows per page, along with:
- Page number
- Header information (title, program name, transaction ID, date, time)
- Error/info message line

---

## Business Rules

### 1. Authentication / Session Check
- If no COMMAREA is passed (EIBCALEN = 0), the program redirects to the
  sign-on screen (`COSGN00C`). This prevents unauthenticated access.

### 2. User Selection
- Only one user can be selected at a time (first non-blank selection wins)
- Valid selection values: 'U'/'u' (Update) or 'D'/'d' (Delete)
- Any other non-blank selection value displays an error message

### 3. Pagination
- Page size is fixed at 10 records
- PF7 navigates backward; PF8 navigates forward
- At the first page, PF7 displays "You are already at the top of the page..."
- When no more records exist, PF8 displays "You are already at the bottom of the page..."
- Page number is tracked in the COMMAREA between interactions

### 4. Browsing
- The starting user ID for browsing can be entered in the User ID input field
- If blank, browsing starts from the beginning (LOW-VALUES)
- Records are retrieved in ascending user ID order

### 5. Screen Navigation

| Key | Action |
|---|---|
| Enter | Process selection and refresh list |
| PF3 | Return to Admin Menu (COADM01C) |
| PF7 | Page backward |
| PF8 | Page forward |
| Any other | Display "Invalid key pressed" message |

---

## Error Handling

- VSAM STARTBR errors:
  - NOTFND: Sets EOF flag, displays "You are at the top of the page..."
  - Other: Sets error flag, displays "Unable to lookup User..."
- VSAM READNEXT errors:
  - ENDFILE: Sets EOF flag, displays "You have reached the bottom of the page..."
  - Other: Sets error flag, displays "Unable to lookup User..."
- VSAM READPREV errors:
  - ENDFILE: Sets EOF flag, displays "You have reached the top of the page..."
  - Other: Sets error flag, displays "Unable to lookup User..."
- All errors are displayed in the `ERRMSGO` field of the output map.

---

## Working Storage Variables

| Variable | Type | Purpose |
|---|---|---|
| WS-PGMNAME | PIC X(08) | Program name constant ('COUSR00C') |
| WS-TRANID | PIC X(04) | Transaction ID constant ('CU00') |
| WS-MESSAGE | PIC X(80) | Message to display on screen |
| WS-USRSEC-FILE | PIC X(08) | VSAM file name ('USRSEC') |
| WS-ERR-FLG | PIC X(01) | Error flag ('Y'/'N') |
| WS-USER-SEC-EOF | PIC X(01) | End-of-file flag ('Y'/'N') |
| WS-SEND-ERASE-FLG | PIC X(01) | Whether to erase screen on send |
| WS-PAGE-NUM | PIC S9(04) | Current page number |
| WS-IDX | PIC S9(04) | Loop index for row population |
| CDEMO-CU00-USRID-FIRST | PIC X(08) | First user ID on current page |
| CDEMO-CU00-USRID-LAST | PIC X(08) | Last user ID on current page |
| CDEMO-CU00-PAGE-NUM | PIC 9(08) | Page number stored in COMMAREA |
| CDEMO-CU00-NEXT-PAGE-FLG | PIC X(01) | Has-next-page flag ('Y'/'N') |
| CDEMO-CU00-USR-SEL-FLG | PIC X(01) | Selected operation (U/D) |
| CDEMO-CU00-USR-SELECTED | PIC X(08) | Selected user ID |
