"""
Unit tests for Phase 5: Bill Payment.

Tests cover:
- Bill payment validation (validate_bill_payment)
- Bill payment processing (process_bill_payment)
- Bill payment form (BillPaymentForm)
- Bill payment view (BillPaymentView)

Coverage target: 90% minimum (security-sensitive: bill payment).
All test data is synthetic — no real customer data (CPS 234).
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase

from python.cards.models import Account, CardXref
from python.transactions.forms import BillPaymentForm
from python.transactions.models import Transaction
from python.transactions.services import (
    process_bill_payment,
    validate_bill_payment,
)


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------


class TestValidateBillPayment(TestCase):
    """Tests for validate_bill_payment service function."""

    def test_valid_input(self) -> None:
        """All valid inputs pass validation."""
        result = validate_bill_payment(
            acct_id="00000000001",
            card_num="4111111111111111",
            payment_amount="100.00",
        )
        assert result.is_valid

    def test_empty_account_id(self) -> None:
        """Empty account ID fails."""
        result = validate_bill_payment(
            acct_id="",
            card_num="4111111111111111",
            payment_amount="100.00",
        )
        assert not result.is_valid
        assert "Account ID" in result.error_message

    def test_non_numeric_account_id(self) -> None:
        """Non-numeric account ID fails."""
        result = validate_bill_payment(
            acct_id="ABCDEFGHIJK",
            card_num="4111111111111111",
            payment_amount="100.00",
        )
        assert not result.is_valid
        assert "Numeric" in result.error_message

    def test_empty_card_number(self) -> None:
        """Empty card number fails."""
        result = validate_bill_payment(
            acct_id="00000000001",
            card_num="",
            payment_amount="100.00",
        )
        assert not result.is_valid
        assert "Card Number" in result.error_message

    def test_non_numeric_card_number(self) -> None:
        """Non-numeric card number fails."""
        result = validate_bill_payment(
            acct_id="00000000001",
            card_num="ABCDEFGHIJKLMNOP",
            payment_amount="100.00",
        )
        assert not result.is_valid
        assert "Numeric" in result.error_message

    def test_empty_payment_amount(self) -> None:
        """Empty payment amount fails."""
        result = validate_bill_payment(
            acct_id="00000000001",
            card_num="4111111111111111",
            payment_amount="",
        )
        assert not result.is_valid
        assert "amount" in result.error_message.lower()

    def test_zero_payment_amount(self) -> None:
        """Zero payment amount fails."""
        result = validate_bill_payment(
            acct_id="00000000001",
            card_num="4111111111111111",
            payment_amount="0.00",
        )
        assert not result.is_valid
        assert "positive" in result.error_message.lower()

    def test_negative_payment_amount(self) -> None:
        """Negative payment amount fails."""
        result = validate_bill_payment(
            acct_id="00000000001",
            card_num="4111111111111111",
            payment_amount="-50.00",
        )
        assert not result.is_valid
        assert "positive" in result.error_message.lower()

    def test_non_numeric_payment_amount(self) -> None:
        """Non-numeric payment amount fails."""
        result = validate_bill_payment(
            acct_id="00000000001",
            card_num="4111111111111111",
            payment_amount="not_a_number",
        )
        assert not result.is_valid
        assert "valid number" in result.error_message.lower()

    def test_whitespace_account_id(self) -> None:
        """Whitespace-only account ID fails."""
        result = validate_bill_payment(
            acct_id="   ",
            card_num="4111111111111111",
            payment_amount="100.00",
        )
        assert not result.is_valid

    def test_whitespace_card_number(self) -> None:
        """Whitespace-only card number fails."""
        result = validate_bill_payment(
            acct_id="00000000001",
            card_num="   ",
            payment_amount="100.00",
        )
        assert not result.is_valid

    def test_large_payment_amount(self) -> None:
        """Large but valid payment amount passes."""
        result = validate_bill_payment(
            acct_id="00000000001",
            card_num="4111111111111111",
            payment_amount="999999999.99",
        )
        assert result.is_valid

    def test_small_payment_amount(self) -> None:
        """Small positive payment amount passes."""
        result = validate_bill_payment(
            acct_id="00000000001",
            card_num="4111111111111111",
            payment_amount="0.01",
        )
        assert result.is_valid


# ---------------------------------------------------------------------------
# Process bill payment tests
# ---------------------------------------------------------------------------


class TestProcessBillPayment(TestCase):
    """Tests for process_bill_payment service function."""

    def setUp(self) -> None:
        """Create synthetic account, card, and xref data."""
        Account.objects.create(
            acct_id="00000000001",
            acct_active_status="Y",
            acct_curr_bal=Decimal("5000.00"),
            acct_credit_limit=Decimal("10000.00"),
            acct_curr_cyc_credit=Decimal("0.00"),
        )
        CardXref.objects.create(
            xref_card_num="4111111111111111",
            xref_cust_id="000000001",
            xref_acct_id="00000000001",
        )

    def test_successful_payment(self) -> None:
        """Valid payment creates transaction and updates balance."""
        result = process_bill_payment(
            acct_id="1",
            card_num="4111111111111111",
            payment_amount="100.00",
        )
        assert result.success
        assert Transaction.objects.count() == 1

        # Verify balance updated
        account = Account.objects.get(acct_id="00000000001")
        assert account.acct_curr_bal == Decimal("4900.00")
        assert account.acct_curr_cyc_credit == Decimal("100.00")

    def test_payment_transaction_type(self) -> None:
        """Payment creates transaction with BP type code."""
        process_bill_payment(
            acct_id="1",
            card_num="4111111111111111",
            payment_amount="50.00",
        )
        txn = Transaction.objects.first()
        assert txn.tran_type_cd == "BP"
        assert txn.tran_cat_cd == "0001"
        assert txn.tran_source == "ONLINE"

    def test_payment_amount_as_decimal(self) -> None:
        """Payment amount stored as Decimal (not float)."""
        process_bill_payment(
            acct_id="1",
            card_num="4111111111111111",
            payment_amount="100.50",
        )
        txn = Transaction.objects.first()
        assert isinstance(txn.tran_amt, Decimal)
        assert txn.tran_amt == Decimal("100.50")

    def test_card_not_belonging_to_account(self) -> None:
        """Card not linked to account returns error."""
        CardXref.objects.create(
            xref_card_num="5222222222222222",
            xref_cust_id="000000002",
            xref_acct_id="00000000002",
        )
        result = process_bill_payment(
            acct_id="1",
            card_num="5222222222222222",
            payment_amount="100.00",
        )
        assert not result.success
        assert "does not belong" in result.message.lower()

    def test_account_not_found(self) -> None:
        """Non-existent account returns error."""
        CardXref.objects.create(
            xref_card_num="5333333333333333",
            xref_cust_id="000000003",
            xref_acct_id="00000000099",
        )
        result = process_bill_payment(
            acct_id="99",
            card_num="5333333333333333",
            payment_amount="100.00",
        )
        assert not result.success
        assert "not found" in result.message.lower()

    def test_validation_failure_propagates(self) -> None:
        """Validation errors prevent payment processing."""
        result = process_bill_payment(
            acct_id="",
            card_num="4111111111111111",
            payment_amount="100.00",
        )
        assert not result.success
        assert Transaction.objects.count() == 0

    def test_success_message_has_confirmation(self) -> None:
        """Success message includes confirmation number."""
        result = process_bill_payment(
            acct_id="1",
            card_num="4111111111111111",
            payment_amount="100.00",
        )
        assert "Confirmation" in result.message

    def test_multiple_payments(self) -> None:
        """Multiple payments accumulate correctly."""
        process_bill_payment(
            acct_id="1",
            card_num="4111111111111111",
            payment_amount="100.00",
        )
        process_bill_payment(
            acct_id="1",
            card_num="4111111111111111",
            payment_amount="200.00",
        )
        account = Account.objects.get(acct_id="00000000001")
        assert account.acct_curr_bal == Decimal("4700.00")
        assert account.acct_curr_cyc_credit == Decimal("300.00")
        assert Transaction.objects.count() == 2

    def test_payment_with_spaces_in_inputs(self) -> None:
        """Inputs with extra spaces are handled correctly."""
        result = process_bill_payment(
            acct_id=" 1 ",
            card_num=" 4111111111111111 ",
            payment_amount=" 100.00 ",
        )
        assert result.success


# ---------------------------------------------------------------------------
# Form tests
# ---------------------------------------------------------------------------


class TestBillPaymentForm(TestCase):
    """Tests for BillPaymentForm."""

    def test_valid_form(self) -> None:
        """Form with valid data is valid."""
        form = BillPaymentForm(data={
            "acct_id": "00000000001",
            "card_num": "4111111111111111",
            "payment_amount": "100.00",
        })
        assert form.is_valid()

    def test_zero_amount(self) -> None:
        """Zero amount is invalid."""
        form = BillPaymentForm(data={
            "acct_id": "00000000001",
            "card_num": "4111111111111111",
            "payment_amount": "0",
        })
        assert not form.is_valid()

    def test_negative_amount(self) -> None:
        """Negative amount is invalid."""
        form = BillPaymentForm(data={
            "acct_id": "00000000001",
            "card_num": "4111111111111111",
            "payment_amount": "-50.00",
        })
        assert not form.is_valid()

    def test_non_numeric_amount(self) -> None:
        """Non-numeric amount is invalid."""
        form = BillPaymentForm(data={
            "acct_id": "00000000001",
            "card_num": "4111111111111111",
            "payment_amount": "abc",
        })
        assert not form.is_valid()

    def test_missing_account(self) -> None:
        """Missing account ID is invalid."""
        form = BillPaymentForm(data={
            "card_num": "4111111111111111",
            "payment_amount": "100.00",
        })
        assert not form.is_valid()

    def test_missing_card(self) -> None:
        """Missing card number is invalid."""
        form = BillPaymentForm(data={
            "acct_id": "00000000001",
            "payment_amount": "100.00",
        })
        assert not form.is_valid()


# ---------------------------------------------------------------------------
# View tests
# ---------------------------------------------------------------------------


class TestBillPaymentView(TestCase):
    """Tests for BillPaymentView."""

    def setUp(self) -> None:
        """Create test user and supporting data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123",
        )
        self.client.login(
            username="testuser", password="testpass123",
        )
        Account.objects.create(
            acct_id="00000000001",
            acct_active_status="Y",
            acct_curr_bal=Decimal("5000.00"),
            acct_credit_limit=Decimal("10000.00"),
            acct_curr_cyc_credit=Decimal("0.00"),
        )
        CardXref.objects.create(
            xref_card_num="4111111111111111",
            xref_cust_id="000000001",
            xref_acct_id="00000000001",
        )

    def test_get_form(self) -> None:
        """Bill payment form loads."""
        response = self.client.get("/transactions/billpay/")
        assert response.status_code == 200

    def test_get_unauthenticated(self) -> None:
        """Unauthenticated user is redirected."""
        self.client.logout()
        response = self.client.get("/transactions/billpay/")
        assert response.status_code == 302

    def test_post_success(self) -> None:
        """Valid payment redirects to transaction list."""
        response = self.client.post(
            "/transactions/billpay/",
            {
                "acct_id": "1",
                "card_num": "4111111111111111",
                "payment_amount": "100.00",
            },
        )
        assert response.status_code == 302

    def test_post_invalid(self) -> None:
        """Invalid payment re-renders form."""
        response = self.client.post(
            "/transactions/billpay/",
            {
                "acct_id": "1",
                "card_num": "4111111111111111",
                "payment_amount": "-50.00",
            },
        )
        assert response.status_code == 200

    def test_post_card_mismatch(self) -> None:
        """Card not matching account shows error."""
        response = self.client.post(
            "/transactions/billpay/",
            {
                "acct_id": "1",
                "card_num": "9999999999999999",
                "payment_amount": "100.00",
            },
        )
        assert response.status_code == 200

    def test_template_used(self) -> None:
        """Correct template is used."""
        response = self.client.get("/transactions/billpay/")
        self.assertTemplateUsed(
            response, "transactions/bill_payment.html",
        )
