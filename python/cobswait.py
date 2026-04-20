"""
COBSWAIT - Wait Utility (Python Translation)

Translated from the COBOL program COBSWAIT.CBL in the AWS CardDemo
mainframe modernization project. This module provides a simple wait
function that pauses execution for a specified duration.

Original: BATCH COBOL program that calls MVSWAIT with centiseconds.
This translation uses Python's time.sleep().
"""

from __future__ import annotations

import time


def wait_centiseconds(centiseconds: int) -> None:
    """
    Pause execution for the specified number of centiseconds.

    This is the Python equivalent of the COBSWAIT COBOL program which
    accepts a parameter in centiseconds (hundredths of a second) and
    calls the MVSWAIT assembler routine.

    Args:
        centiseconds: Wait duration in hundredths of a second.
            Must be a non-negative integer.
            Examples: 100 = 1 second, 6000 = 60 seconds.

    Raises:
        ValueError: If centiseconds is negative.
    """
    if centiseconds < 0:
        raise ValueError(
            f"centiseconds must be non-negative, got {centiseconds}"
        )

    seconds = centiseconds / 100.0
    time.sleep(seconds)


def main() -> None:
    """
    Entry point matching the COBOL PROCEDURE DIVISION.

    Reads the wait time parameter from standard input (SYSIN),
    converts it to centiseconds, and waits.
    """
    parm_value = input().strip()

    if not parm_value:
        print("COBSWAIT: No parameter provided")
        return

    try:
        centiseconds = int(parm_value)
    except ValueError:
        print(f"COBSWAIT: Invalid parameter: {parm_value!r}")
        return

    print(f"COBSWAIT: Waiting {centiseconds} centiseconds "
          f"({centiseconds / 100.0:.2f} seconds)")
    wait_centiseconds(centiseconds)
    print("COBSWAIT: Wait complete")


if __name__ == "__main__":
    main()
