"""Unit tests for account utility commands — 70% coverage target.

Tests seed_accounts, list_accounts, and validate_accounts commands.
"""

from __future__ import annotations

import json
from decimal import Decimal
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command

from batch.models import Account, Card, CardXref


@pytest.fixture()
def _account_data(db: None) -> None:
    """Create synthetic test data for account utilities."""
    Account.objects.create(
        acct_id="00000000001",
        acct_active_status="Y",
        acct_curr_bal=Decimal("1000.00"),
        acct_credit_limit=Decimal("5000.00"),
        acct_group_id="GROUP1",
    )
    Account.objects.create(
        acct_id="00000000002",
        acct_active_status="Y",
        acct_curr_bal=Decimal("2000.00"),
        acct_credit_limit=Decimal("10000.00"),
        acct_group_id="GROUP2",
    )
    CardXref.objects.create(
        xref_card_num="4111111111111111",
        xref_cust_id="000000001",
        xref_acct_id="00000000001",
    )
    Card.objects.create(
        card_num="4111111111111111",
        card_acct_id="00000000001",
        card_active_status="Y",
    )


class TestSeedAccounts:
    """Tests for seed_accounts command."""

    def test_seed_from_csv(self, tmp_path: Path, db: None) -> None:
        """Accounts seeded from CSV file."""
        csv_file = tmp_path / "accounts.csv"
        csv_file.write_text(
            "acct_id,acct_active_status,acct_curr_bal,acct_credit_limit\n"
            "00000000099,Y,500.00,2000.00\n"
        )
        out = StringIO()
        call_command("seed_accounts", str(csv_file), format="csv", stdout=out)
        assert Account.objects.filter(acct_id="00000000099").exists()
        assert "Created: 1" in out.getvalue()

    def test_seed_from_json(self, tmp_path: Path, db: None) -> None:
        """Accounts seeded from JSON file."""
        json_file = tmp_path / "accounts.json"
        json_file.write_text(
            json.dumps(
                [
                    {
                        "acct_id": "00000000098",
                        "acct_active_status": "Y",
                        "acct_curr_bal": "750.00",
                        "acct_credit_limit": "3000.00",
                    }
                ]
            )
        )
        out = StringIO()
        call_command("seed_accounts", str(json_file), format="json", stdout=out)
        assert Account.objects.filter(acct_id="00000000098").exists()
        assert "Created: 1" in out.getvalue()

    def test_seed_updates_existing(self, tmp_path: Path, db: None) -> None:
        """Existing accounts are updated, not duplicated."""
        Account.objects.create(
            acct_id="00000000099",
            acct_active_status="N",
        )
        csv_file = tmp_path / "accounts.csv"
        csv_file.write_text("acct_id,acct_active_status\n00000000099,Y\n")
        out = StringIO()
        call_command("seed_accounts", str(csv_file), format="csv", stdout=out)
        assert "Updated: 1" in out.getvalue()
        account = Account.objects.get(acct_id="00000000099")
        assert account.acct_active_status == "Y"

    def test_seed_missing_file(self, db: None) -> None:
        """Error message when file not found."""
        err = StringIO()
        call_command("seed_accounts", "/nonexistent/file.csv", stderr=err)
        assert "not found" in err.getvalue()


@pytest.mark.usefixtures("_account_data")
class TestListAccounts:
    """Tests for list_accounts command."""

    def test_list_all_accounts(self) -> None:
        """All accounts listed."""
        out = StringIO()
        call_command("list_accounts", stdout=out)
        output = out.getvalue()
        assert "00000000001" in output
        assert "00000000002" in output
        assert "Total accounts: 2" in output

    def test_filter_by_account(self) -> None:
        """Listing filtered to specific account."""
        out = StringIO()
        call_command("list_accounts", acct_id="00000000001", stdout=out)
        output = out.getvalue()
        assert "00000000001" in output
        assert "Total accounts: 1" in output

    def test_show_cards(self) -> None:
        """Card info shown when --show-cards flag used."""
        out = StringIO()
        call_command("list_accounts", show_cards=True, stdout=out)
        assert "****1111" in out.getvalue()

    def test_show_xref(self) -> None:
        """Cross-ref info shown when --show-xref flag used."""
        out = StringIO()
        call_command("list_accounts", show_xref=True, stdout=out)
        assert "Cust:" in out.getvalue()


class TestListAccountsEmpty:
    """Tests for list_accounts on empty database."""

    def test_empty_database(self, db: None) -> None:
        """Empty listing on empty database."""
        out = StringIO()
        call_command("list_accounts", stdout=out)
        assert "Total accounts: 0" in out.getvalue()


@pytest.mark.usefixtures("_account_data")
class TestValidateAccounts:
    """Tests for validate_accounts command."""

    def test_valid_data_no_errors(self) -> None:
        """Valid data produces no errors."""
        out = StringIO()
        call_command("validate_accounts", stdout=out)
        assert "0 errors" in out.getvalue()

    def test_orphan_xref_detected(self, db: None) -> None:
        """Xref pointing to missing account flagged as error."""
        CardXref.objects.create(
            xref_card_num="5555555555555555",
            xref_cust_id="000000099",
            xref_acct_id="99999999999",
        )
        err = StringIO()
        out = StringIO()
        call_command("validate_accounts", stdout=out, stderr=err)
        assert "not found" in err.getvalue()

    def test_orphan_card_detected(self, db: None) -> None:
        """Card referencing missing account flagged as error."""
        Card.objects.create(
            card_num="5555555555555555",
            card_acct_id="99999999999",
            card_active_status="Y",
        )
        err = StringIO()
        out = StringIO()
        call_command("validate_accounts", stdout=out, stderr=err)
        assert "not found" in err.getvalue()

    def test_negative_credit_limit_error(self, db: None) -> None:
        """Negative credit limit flagged as error."""
        Account.objects.create(
            acct_id="00000000099",
            acct_credit_limit=Decimal("-100.00"),
        )
        err = StringIO()
        out = StringIO()
        call_command("validate_accounts", stdout=out, stderr=err)
        assert "negative credit limit" in err.getvalue()

    def test_high_balance_warning(self, db: None) -> None:
        """Balance exceeding 2x credit limit generates warning."""
        Account.objects.create(
            acct_id="00000000099",
            acct_curr_bal=Decimal("15000.00"),
            acct_credit_limit=Decimal("5000.00"),
            acct_active_status="Y",
        )
        out = StringIO()
        call_command("validate_accounts", stdout=out)
        assert "2x credit limit" in out.getvalue()
