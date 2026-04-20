# COBSWAIT - Wait Utility

## Overview

**Program ID:** COBSWAIT  
**Application:** CardDemo (AWS Mainframe Modernization)  
**Type:** BATCH COBOL Program  
**Function:** Pause execution for a specified number of centiseconds  

COBSWAIT is a trivial batch utility program that introduces a timed delay in
batch job processing. It accepts a parameter specifying the wait duration in
centiseconds (hundredths of a second) and calls the MVSWAIT assembler routine
to pause execution.

---

## Program Structure

### Division Layout

| Division | Purpose |
|---|---|
| Identification | Declares program name (`COBSWAIT`) |
| Environment | Input-Output Section (minimal) |
| Data | Working-Storage for wait time and parameter value |
| Procedure | Accept parameter, call MVSWAIT |

### Working-Storage Variables

| Variable | PIC | Description |
|---|---|---|
| `MVSWAIT-TIME` | 9(8) COMP | Wait time in centiseconds (binary) |
| `PARM-VALUE` | X(8) | Raw parameter value from SYSIN |

---

## Program Flow

```
PROCEDURE DIVISION
  |
  |-- ACCEPT PARM-VALUE FROM SYSIN
  |-- MOVE PARM-VALUE TO MVSWAIT-TIME
  |-- CALL 'MVSWAIT' USING MVSWAIT-TIME
  |-- STOP RUN
```

1. Read the wait time parameter from SYSIN (standard input)
2. Move the alphanumeric parameter to the binary wait time field
3. Call the MVSWAIT assembler routine which suspends the program for the
   specified number of centiseconds
4. Terminate the program

---

## Input

| Source | Format | Description |
|---|---|---|
| SYSIN | PIC X(8) | Wait duration in centiseconds (e.g., `00000100` = 1 second) |

### Examples

| Parameter | Wait Duration |
|---|---|
| `00000001` | 0.01 seconds (10 milliseconds) |
| `00000100` | 1 second |
| `00006000` | 60 seconds (1 minute) |
| `00030000` | 5 minutes |

---

## Usage in CardDemo

COBSWAIT is used in JCL batch jobs (WAITSTEP) to introduce delays between
processing steps, for example to allow CICS to release file locks before
the next batch step opens the same files.

---

## Python Translation Notes

In the Python translation, the MVSWAIT system call is replaced by
`time.sleep(centiseconds / 100)`. The function accepts centiseconds as an
integer and sleeps for the equivalent duration in seconds.
