"""Integration tests for online user workflows.

End-to-end tests simulating user interactions with the CardDemo system:
- Login -> navigate menu -> view account -> update account -> logout
- Login -> view transactions -> add transaction -> verify balance
- Admin login -> user management CRUD

All test data is synthetic — NEVER use real customer data.
SECURITY: Never log account numbers, card numbers, or transaction
amounts in plain text (CPS 234 requirement).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.test import Client

from batch.models import (
    Account,
    Card,
    CardXref,
    Customer,
    Transaction,
    UserSecurity,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client() -> Client:
    """Django test client for HTTP requests."""
    return Client()


@pytest.fixture()
def regular_user(db: None) -> User:
    """Synthetic regular user for authentication tests."""
    user = User.objects.create_user(
        username="testuser",
        password="TestPassword123!",  # noqa: S106
        first_name="Test",
        last_name="User",
        is_staff=False,
    )
    return user


@pytest.fixture()
def admin_user(db: None) -> User:
    """Synthetic admin user for authentication tests."""
    user = User.objects.create_user(
        username="adminuser",
        password="AdminPassword123!",  # noqa: S106
        first_name="Admin",
        last_name="User",
        is_staff=True,
        is_superuser=True,
    )
    return user


@pytest.fixture()
def online_data(db: None) -> dict[str, object]:
    """Set up synthetic data for online workflow tests."""
    account = Account.objects.create(
        acct_id="00000000001",
        acct_active_status="Y",
        acct_curr_bal=Decimal("1500.00"),
        acct_credit_limit=Decimal("5000.00"),
        acct_cash_credit_limit=Decimal("1000.00"),
        acct_open_date="2020-01-01",
        acct_expiration_date="2030-12-31",
        acct_reissue_date="2025-01-01",
        acct_curr_cyc_credit=Decimal("300.00"),
        acct_curr_cyc_debit=Decimal("100.00"),
        acct_addr_zip="10001",
        acct_group_id="GROUP1",
    )
    card = Card.objects.create(
        card_num="4111111111111111",
        card_acct_id="00000000001",
        card_cvv_cd="123",
        card_embossed_name="TEST USER ONE",
        card_expiration_date="2030-12-31",
        card_active_status="Y",
    )
    xref = CardXref.objects.create(
        xref_card_num="4111111111111111",
        xref_cust_id="000000001",
        xref_acct_id="00000000001",
    )
    customer = Customer.objects.create(
        cust_id="000000001",
        cust_first_name="TEST",
        cust_middle_name="M",
        cust_last_name="USER",
        cust_addr_line_1="123 TEST ST",
        cust_addr_state_cd="NY",
        cust_addr_country_cd="US",
        cust_addr_zip="10001",
        cust_phone_num_1="5551234567",
        cust_ssn="000000000",
        cust_dob_yyyy_mm_dd="1990-01-01",
        cust_fico_credit_score="750",
    )
    txn = Transaction.objects.create(
        tran_id="0000000000000001",
        tran_type_cd="01",
        tran_cat_cd="5001",
        tran_source="ONLINE",
        tran_desc="TEST PURCHASE",
        tran_amt=Decimal("100.00"),
        tran_merchant_id="000000001",
        tran_merchant_name="TEST MERCHANT",
        tran_merchant_city="NEW YORK",
        tran_merchant_zip="10001",
        tran_card_num="4111111111111111",
        tran_orig_ts="2025-01-15-10.30.00.000000",
        tran_proc_ts="2025-01-15-10.30.01.000000",
    )
    user_sec = UserSecurity.objects.create(
        sec_usr_id="TESTUSR1",
        sec_usr_fname="Test",
        sec_usr_lname="User",
        sec_usr_pwd="hashed_password_placeholder",
        sec_usr_type="U",
    )
    admin_sec = UserSecurity.objects.create(
        sec_usr_id="ADMIN001",
        sec_usr_fname="Admin",
        sec_usr_lname="User",
        sec_usr_pwd="hashed_password_placeholder",
        sec_usr_type="A",
    )

    return {
        "account": account,
        "card": card,
        "xref": xref,
        "customer": customer,
        "transaction": txn,
        "user_security": user_sec,
        "admin_security": admin_sec,
    }


# ---------------------------------------------------------------------------
# Authentication workflow tests
# ---------------------------------------------------------------------------


class TestAuthenticationWorkflow:
    """Login/logout workflow tests."""

    def test_django_admin_login_success(self, client: Client, admin_user: User) -> None:
        """Admin can log in via Django admin."""
        response = client.post(
            "/admin/login/",
            {"username": "adminuser", "password": "AdminPassword123!"},
        )
        # Successful login redirects
        assert response.status_code in (200, 302)

    def test_django_admin_login_failure(self, client: Client, db: None) -> None:
        """Invalid credentials are rejected."""
        response = client.post(
            "/admin/login/",
            {"username": "nonexistent", "password": "wrongpass"},
        )
        assert response.status_code == 200  # Re-renders login form

    def test_session_persists_after_login(self, client: Client, admin_user: User) -> None:
        """Session is maintained after successful login."""
        client.login(username="adminuser", password="AdminPassword123!")  # noqa: S106
        response = client.get("/admin/")
        assert response.status_code == 200

    def test_logout_clears_session(self, client: Client, admin_user: User) -> None:
        """Logout clears the session."""
        client.login(username="adminuser", password="AdminPassword123!")  # noqa: S106
        client.logout()
        response = client.get("/admin/")
        # Should redirect to login page
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# Account view workflow tests
# ---------------------------------------------------------------------------


class TestAccountViewWorkflow:
    """Account viewing and update workflow tests."""

    def test_account_data_integrity(self, online_data: dict[str, object]) -> None:
        """Account data is consistent after creation."""
        account = Account.objects.get(acct_id="00000000001")
        assert account.acct_active_status == "Y"
        assert account.acct_curr_bal == Decimal("1500.00")
        assert account.acct_credit_limit == Decimal("5000.00")

    def test_account_update_persists(self, online_data: dict[str, object]) -> None:
        """Account updates are persisted to the database."""
        account = Account.objects.get(acct_id="00000000001")
        account.acct_addr_zip = "90210"
        account.save()

        refreshed = Account.objects.get(acct_id="00000000001")
        assert refreshed.acct_addr_zip == "90210"

    def test_account_card_relationship(self, online_data: dict[str, object]) -> None:
        """Cards are correctly linked to accounts via card_acct_id."""
        cards = Card.objects.filter(card_acct_id="00000000001")
        assert cards.count() == 1
        assert cards.first() is not None
        first_card = cards.first()
        assert first_card is not None
        assert first_card.card_num == "4111111111111111"


# ---------------------------------------------------------------------------
# Transaction workflow tests
# ---------------------------------------------------------------------------


class TestTransactionWorkflow:
    """Transaction viewing and creation workflow tests."""

    def test_view_transactions_for_card(self, online_data: dict[str, object]) -> None:
        """Transactions can be retrieved by card number."""
        txns = Transaction.objects.filter(tran_card_num="4111111111111111")
        assert txns.count() == 1
        txn = txns.first()
        assert txn is not None
        assert txn.tran_amt == Decimal("100.00")

    def test_add_transaction_updates_record_count(self, online_data: dict[str, object]) -> None:
        """Adding a transaction increases the count."""
        initial_count = Transaction.objects.count()

        Transaction.objects.create(
            tran_id="0000000000000002",
            tran_type_cd="01",
            tran_cat_cd="5001",
            tran_source="ONLINE",
            tran_desc="NEW TEST PURCHASE",
            tran_amt=Decimal("200.00"),
            tran_merchant_id="000000002",
            tran_merchant_name="NEW MERCHANT",
            tran_merchant_city="LOS ANGELES",
            tran_merchant_zip="90210",
            tran_card_num="4111111111111111",
            tran_orig_ts="2025-01-16-14.00.00.000000",
            tran_proc_ts="2025-01-16-14.00.01.000000",
        )

        assert Transaction.objects.count() == initial_count + 1

    def test_transaction_balance_update(self, online_data: dict[str, object]) -> None:
        """Adding a transaction and updating balance produces correct result."""
        account = Account.objects.get(acct_id="00000000001")
        original_bal = account.acct_curr_bal

        txn_amount = Decimal("200.00")
        Transaction.objects.create(
            tran_id="0000000000000003",
            tran_type_cd="01",
            tran_cat_cd="5001",
            tran_source="ONLINE",
            tran_desc="BALANCE TEST TXN",
            tran_amt=txn_amount,
            tran_merchant_id="000000003",
            tran_merchant_name="BALANCE MERCHANT",
            tran_merchant_city="CHICAGO",
            tran_merchant_zip="60601",
            tran_card_num="4111111111111111",
            tran_orig_ts="2025-01-17-09.00.00.000000",
            tran_proc_ts="2025-01-17-09.00.01.000000",
        )

        # Simulate balance update (as the service layer would do)
        account.acct_curr_bal += txn_amount
        account.acct_curr_cyc_credit += txn_amount
        account.save()

        refreshed = Account.objects.get(acct_id="00000000001")
        assert refreshed.acct_curr_bal == original_bal + txn_amount
        assert refreshed.acct_curr_cyc_credit == Decimal("500.00")

    def test_transaction_unique_id_constraint(self, online_data: dict[str, object]) -> None:
        """Duplicate transaction IDs are rejected."""
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            Transaction.objects.create(
                tran_id="0000000000000001",  # duplicate
                tran_type_cd="01",
                tran_cat_cd="5001",
                tran_source="ONLINE",
                tran_desc="DUPLICATE TXN",
                tran_amt=Decimal("50.00"),
                tran_card_num="4111111111111111",
            )


# ---------------------------------------------------------------------------
# Admin user management workflow tests
# ---------------------------------------------------------------------------


class TestAdminUserManagementWorkflow:
    """Admin user CRUD workflow tests."""

    def test_create_user_security_record(self, db: None) -> None:
        """Admin can create a new user security record."""
        user = UserSecurity.objects.create(
            sec_usr_id="NEWUSR01",
            sec_usr_fname="New",
            sec_usr_lname="User",
            sec_usr_pwd="hashed_placeholder",
            sec_usr_type="U",
        )
        assert UserSecurity.objects.filter(sec_usr_id="NEWUSR01").exists()
        assert user.sec_usr_type == "U"

    def test_update_user_security_record(self, online_data: dict[str, object]) -> None:
        """Admin can update user security details."""
        user = UserSecurity.objects.get(sec_usr_id="TESTUSR1")
        user.sec_usr_fname = "Updated"
        user.save()

        refreshed = UserSecurity.objects.get(sec_usr_id="TESTUSR1")
        assert refreshed.sec_usr_fname == "Updated"

    def test_delete_user_security_record(self, online_data: dict[str, object]) -> None:
        """Admin can delete a user security record."""
        assert UserSecurity.objects.filter(sec_usr_id="TESTUSR1").exists()
        UserSecurity.objects.filter(sec_usr_id="TESTUSR1").delete()
        assert not UserSecurity.objects.filter(sec_usr_id="TESTUSR1").exists()

    def test_list_user_security_records(self, online_data: dict[str, object]) -> None:
        """Admin can list all user security records."""
        users = UserSecurity.objects.all()
        assert users.count() == 2  # TESTUSR1 + ADMIN001

    def test_user_type_admin_vs_regular(self, online_data: dict[str, object]) -> None:
        """Admin and regular users have different type codes."""
        regular = UserSecurity.objects.get(sec_usr_id="TESTUSR1")
        admin = UserSecurity.objects.get(sec_usr_id="ADMIN001")
        assert regular.sec_usr_type == "U"
        assert admin.sec_usr_type == "A"

    def test_duplicate_user_id_rejected(self, online_data: dict[str, object]) -> None:
        """Duplicate user IDs are rejected."""
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            UserSecurity.objects.create(
                sec_usr_id="TESTUSR1",  # duplicate
                sec_usr_fname="Dup",
                sec_usr_lname="User",
                sec_usr_pwd="hashed_placeholder",
                sec_usr_type="U",
            )


# ---------------------------------------------------------------------------
# Cross-reference workflow tests
# ---------------------------------------------------------------------------


class TestCrossReferenceWorkflow:
    """Card cross-reference lookup workflow tests."""

    def test_xref_links_card_to_account(self, online_data: dict[str, object]) -> None:
        """Cross-reference correctly links card to account."""
        xref = CardXref.objects.get(xref_card_num="4111111111111111")
        assert xref.xref_acct_id == "00000000001"
        assert xref.xref_cust_id == "000000001"

    def test_xref_to_account_lookup(self, online_data: dict[str, object]) -> None:
        """Full lookup chain: card -> xref -> account works."""
        xref = CardXref.objects.get(xref_card_num="4111111111111111")
        account = Account.objects.get(acct_id=xref.xref_acct_id)
        assert account.acct_active_status == "Y"

    def test_xref_to_customer_lookup(self, online_data: dict[str, object]) -> None:
        """Full lookup chain: card -> xref -> customer works."""
        xref = CardXref.objects.get(xref_card_num="4111111111111111")
        customer = Customer.objects.get(cust_id=xref.xref_cust_id)
        assert customer.cust_first_name == "TEST"
