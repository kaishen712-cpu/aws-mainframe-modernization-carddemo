"""Custom JSON log formatter for structured production logging.

Produces one JSON object per log line, suitable for ingestion by
log aggregation systems (ELK, CloudWatch Logs, Datadog, etc.).

SECURITY: Never log account numbers, card numbers, or transaction
amounts in plain text (CPS 234 sensitive data requirement).
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime


class JSONFormatter(logging.Formatter):
    """Serialize each log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, default=str)
