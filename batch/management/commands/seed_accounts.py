"""Seed account data — batch management command.

Translated from CBACT01C.cbl (431 lines).

Original COBOL program flow:
1. Open ACCTFILE (indexed VSAM) for input
2. Open output files (OUT-FILE, ARRY-FILE, VBRC-FILE)
3. Read accounts sequentially
4. For each account: display, populate output records, write to files
5. Close all files

In the Django translation, this command seeds the database with account
data from a CSV or JSON file, replacing the VSAM file input.
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

from django.core.management.base import BaseCommand, CommandParser

from batch.models import Account

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Seed account data — translated from CBACT01C.cbl."""

    help = "Seed account data from CSV or JSON file (CBACT01C.cbl)"

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command-line arguments."""
        parser.add_argument(
            "input_file",
            type=str,
            help="Path to CSV or JSON file with account data",
        )
        parser.add_argument(
            "--format",
            type=str,
            choices=["csv", "json"],
            default="csv",
            help="Input file format (default: csv)",
        )

    def handle(self, *args: object, **options: object) -> None:
        """Execute the account seeding process.

        Translated from PROCEDURE DIVISION of CBACT01C.cbl.
        Paragraph 1000-ACCTFILE-GET-NEXT reads records; we read from file.
        """
        input_file = Path(str(options["input_file"]))
        file_format = str(options.get("format", "csv") or "csv")

        if not input_file.is_file():
            self.stderr.write(f"Input file not found: {input_file}")
            return

        if file_format == "csv":
            records = self._read_csv(input_file)
        else:
            records = self._read_json(input_file)

        created_count = 0
        updated_count = 0

        for record in records:
            _, created = Account.objects.update_or_create(
                acct_id=record["acct_id"],
                defaults=record,
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            f"Created: {created_count}, Updated: {updated_count}"
        )

    def _read_csv(self, file_path: Path) -> list[dict[str, str]]:
        """Read account records from a CSV file."""
        records: list[dict[str, str]] = []
        with file_path.open() as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(dict(row))
        return records

    def _read_json(self, file_path: Path) -> list[dict[str, str]]:
        """Read account records from a JSON file."""
        data = json.loads(file_path.read_text())
        if isinstance(data, list):
            return data
        return []
