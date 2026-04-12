"""
Batch wait/timer utility for the CardDemo application.

Translated from COBSWAIT.cbl — a utility program that pauses execution
for a specified duration.  The original COBOL program accepts a wait time
in centiseconds via SYSIN, converts it to a binary value, and calls the
ASSEMBLER routine MVSWAIT.  This Python translation replaces MVSWAIT with
``time.sleep()``.
"""

from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)


def wait_centiseconds(centiseconds: int) -> None:
    """Pause execution for the given number of centiseconds.

    Translated from COBSWAIT.cbl PROCEDURE DIVISION:
    ``CALL 'MVSWAIT' USING MVSWAIT-TIME``

    One centisecond equals 0.01 seconds.  The original COBOL program
    accepts an 8-digit packed-decimal value (PIC 9(8) COMP) representing
    centiseconds.

    Args:
        centiseconds: Number of centiseconds to wait (1 cs = 0.01 s).
            Must be non-negative.

    Raises:
        ValueError: If centiseconds is negative.
    """
    if centiseconds < 0:
        raise ValueError(f"Wait time must be non-negative, got {centiseconds}")

    seconds = centiseconds / 100.0
    logger.info("COBSWAIT: Waiting %.2f seconds (%d centiseconds)", seconds, centiseconds)
    time.sleep(seconds)
    logger.info("COBSWAIT: Wait complete")


def wait_seconds(seconds: float) -> None:
    """Pause execution for the given number of seconds.

    Convenience wrapper around ``wait_centiseconds`` for callers that
    prefer to specify the duration in seconds rather than centiseconds.

    Args:
        seconds: Number of seconds to wait.  Must be non-negative.

    Raises:
        ValueError: If seconds is negative.
    """
    if seconds < 0:
        raise ValueError(f"Wait time must be non-negative, got {seconds}")

    centiseconds = round(seconds * 100)
    wait_centiseconds(centiseconds)
