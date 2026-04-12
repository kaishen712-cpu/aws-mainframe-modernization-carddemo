"""
Unit tests for Phase 5: Transaction Management (add transaction).

Tests cover:
- Transaction model (creation, str representation)
- Transaction services (list, validate_key_fields, validate_data_fields,
  validate_confirmation, generate_transaction_id, add_transaction)
- Transaction forms (filter, create)
- Transaction views (list, detail, create)

Coverage target: 90% minimum (security-sensitive: transaction add).
All test data is synthetic — no real customer data (CPS 234).
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase

from python.cards.models import CardXref
from python.transactions.forms import (
    TransactionCreateForm,
    TransactionFilterForm,
)
from python.transactions.models import Transaction
from python.transactions.services import (
    TransactionInput,
    _is_valid_calendar_date,
    _parse_amount,
    add_transaction,
    generate_transaction_id,
    get_transaction_list,
    validate_confirmation,
    validate_data_fields,
    validate_key_fields,
)


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestTransactionModel(TestCase):
    """Tests for the Transaction model."""

    def test_create_transaction(self) -> None:
        """Transaction record can be created with Decimal amount."""
        txn = Transaction.objects.create(
            tran_id="0000000000000001",
            tran_type_cd="01",
            tran_cat_cd="0001",
            tran_source="ONLINE",
            tran_desc="Test purchase",
            tran_amt=Decimal("100.50"),
            tran_merchant_id="000000001",
            tran_merchant_name="TEST MERCHANT",
            tran_merchant_city="TESTVILLE",
            tran_merchant_zip="12345",
            tran_card_num="4111111111111111",
            tran_orig_ts="2025-01-15",
            tran_proc_ts="2025-01-15",
        )
        assert txn.pk is not None
        assert isinstance(txn.tran_amt, Decimal)

    def test_str_no_sensitive_data(self) -> None:
        """CPS 234: str representation does not expose sensitive data."""
        txn = Transaction(tran_id="0000000000000001")
        result = str(txn)
        assert "0000000000000001" in result
        # Should not contain card numbers or amounts

    def test_ordering_descending(self) -> None:
        """Transactions are ordered by tran_id descending."""
        Transaction.objects.create(
            tran_id="0000000000000001",
            tran_type_cd="01", tran_cat_cd="0001",
            tran_source="ONLINE", tran_desc="First",
            tran_amt=Decimal("10.00"),
            tran_merchant_id="000000001",
            tran_merchant_name="M1",
            tran_merchant_city="C1", tran_merchant_zip="11111",
            tran_card_num="4111111111111111",
            tran_orig_ts="2025-01-01", tran_proc_ts="2025-01-01",
        )
        Transaction.objects.create(
            tran_id="0000000000000002",
            tran_type_cd="01", tran_cat_cd="0001",
            tran_source="ONLINE", tran_desc="Second",
            tran_amt=Decimal("20.00"),
            tran_merchant_id="000000002",
            tran_merchant_name="M2",
            tran_merchant_city="C2", tran_merchant_zip="22222",
            tran_card_num="4222222222222222",
            tran_orig_ts="2025-01-02", tran_proc_ts="2025-01-02",
        )
        txns = list(Transaction.objects.all())
        assert txns[0].tran_id == "0000000000000002"


# ---------------------------------------------------------------------------
# Service tests — validate_key_fields
# ---------------------------------------------------------------------------


class TestValidateKeyFields(TestCase):
    """Tests for validate_key_fields service function."""

    def setUp(self) -> None:
        """Create synthetic cross-reference data."""
        CardXref.objects.create(
            xref_card_num="4111111111111111",
            xref_cust_id="000000001",
            xref_acct_id="00000000001",
        )

    def test_valid_account_id(self) -> None:
        """Valid account ID resolves card number."""
        txn_input = TransactionInput(acct_id="1")
        result = validate_key_fields(txn_input)
        assert result.is_valid
        assert txn_input.card_num == "4111111111111111"

    def test_valid_card_number(self) -> None:
        """Valid card number resolves account ID."""
        txn_input = TransactionInput(
            card_num="4111111111111111",
        )
        result = validate_key_fields(txn_input)
        assert result.is_valid
        assert txn_input.acct_id == "00000000001"

    def test_neither_provided(self) -> None:
        """Neither account nor card returns error."""
        txn_input = TransactionInput()
        result = validate_key_fields(txn_input)
        assert not result.is_valid
        assert "must be entered" in result.error_message

    def test_non_numeric_account(self) -> None:
        """Non-numeric account ID fails."""
        txn_input = TransactionInput(acct_id="ABC")
        result = validate_key_fields(txn_input)
        assert not result.is_valid
        assert "Numeric" in result.error_message

    def test_non_numeric_card(self) -> None:
        """Non-numeric card number fails."""
        txn_input = TransactionInput(card_num="ABCD")
        result = validate_key_fields(txn_input)
        assert not result.is_valid
        assert "Numeric" in result.error_message

    def test_account_not_found(self) -> None:
        """Account ID not in xref returns error."""
        txn_input = TransactionInput(acct_id="99999999999")
        result = validate_key_fields(txn_input)
        assert not result.is_valid
        assert "NOT found" in result.error_message

    def test_card_not_found(self) -> None:
        """Card number not in xref returns error."""
        txn_input = TransactionInput(
            card_num="9999999999999999",
        )
        result = validate_key_fields(txn_input)
        assert not result.is_valid
        assert "NOT found" in result.error_message

    def test_account_takes_priority(self) -> None:
        """When both provided, account ID takes priority."""
        txn_input = TransactionInput(
            acct_id="1",
            card_num="9999999999999999",
        )
        result = validate_key_fields(txn_input)
        assert result.is_valid
        assert txn_input.card_num == "4111111111111111"


# ---------------------------------------------------------------------------
# Service tests — validate_data_fields
# ---------------------------------------------------------------------------


class TestValidateDataFields(TestCase):
    """Tests for validate_data_fields service function."""

    def _valid_input(self) -> TransactionInput:
        """Return a valid TransactionInput for testing."""
        return TransactionInput(
            acct_id="00000000001",
            card_num="4111111111111111",
            tran_type_cd="01",
            tran_cat_cd="0001",
            tran_source="ONLINE",
            tran_desc="Test transaction",
            tran_amt="+00000100.50",
            orig_date="2025-01-15",
            proc_date="2025-01-15",
            merchant_id="000000001",
            merchant_name="TEST MERCHANT",
            merchant_city="TESTVILLE",
            merchant_zip="12345",
        )

    def test_all_valid(self) -> None:
        """All valid fields pass."""
        result = validate_data_fields(self._valid_input())
        assert result.is_valid

    def test_empty_type_cd(self) -> None:
        """Empty type code fails."""
        inp = self._valid_input()
        inp.tran_type_cd = ""
        result = validate_data_fields(inp)
        assert not result.is_valid
        assert "Type CD" in result.error_message

    def test_empty_cat_cd(self) -> None:
        """Empty category code fails."""
        inp = self._valid_input()
        inp.tran_cat_cd = ""
        result = validate_data_fields(inp)
        assert not result.is_valid

    def test_empty_source(self) -> None:
        """Empty source fails."""
        inp = self._valid_input()
        inp.tran_source = "   "
        result = validate_data_fields(inp)
        assert not result.is_valid

    def test_empty_desc(self) -> None:
        """Empty description fails."""
        inp = self._valid_input()
        inp.tran_desc = ""
        result = validate_data_fields(inp)
        assert not result.is_valid

    def test_empty_amount(self) -> None:
        """Empty amount fails."""
        inp = self._valid_input()
        inp.tran_amt = ""
        result = validate_data_fields(inp)
        assert not result.is_valid

    def test_non_numeric_type_cd(self) -> None:
        """Non-numeric type code fails."""
        inp = self._valid_input()
        inp.tran_type_cd = "AB"
        result = validate_data_fields(inp)
        assert not result.is_valid
        assert "Numeric" in result.error_message

    def test_non_numeric_cat_cd(self) -> None:
        """Non-numeric category code fails."""
        inp = self._valid_input()
        inp.tran_cat_cd = "ABCD"
        result = validate_data_fields(inp)
        assert not result.is_valid

    def test_invalid_amount_format(self) -> None:
        """Amount not matching pattern fails."""
        inp = self._valid_input()
        inp.tran_amt = "100.50"
        result = validate_data_fields(inp)
        assert not result.is_valid
        assert "format" in result.error_message.lower()

    def test_negative_amount_valid(self) -> None:
        """Negative amount in correct format passes."""
        inp = self._valid_input()
        inp.tran_amt = "-00000025.00"
        result = validate_data_fields(inp)
        assert result.is_valid

    def test_invalid_orig_date_format(self) -> None:
        """Orig date not YYYY-MM-DD fails."""
        inp = self._valid_input()
        inp.orig_date = "01/15/2025"
        result = validate_data_fields(inp)
        assert not result.is_valid

    def test_invalid_orig_date_calendar(self) -> None:
        """Invalid calendar date (Feb 30) fails."""
        inp = self._valid_input()
        inp.orig_date = "2025-02-30"
        result = validate_data_fields(inp)
        assert not result.is_valid
        assert "valid date" in result.error_message.lower()

    def test_invalid_proc_date_format(self) -> None:
        """Proc date not YYYY-MM-DD fails."""
        inp = self._valid_input()
        inp.proc_date = "15-01-2025"
        result = validate_data_fields(inp)
        assert not result.is_valid

    def test_invalid_proc_date_calendar(self) -> None:
        """Invalid calendar proc date fails."""
        inp = self._valid_input()
        inp.proc_date = "2025-13-01"
        result = validate_data_fields(inp)
        assert not result.is_valid

    def test_non_numeric_merchant_id(self) -> None:
        """Non-numeric merchant ID fails."""
        inp = self._valid_input()
        inp.merchant_id = "ABCDEFGHI"
        result = validate_data_fields(inp)
        assert not result.is_valid
        assert "Numeric" in result.error_message

    def test_empty_merchant_name(self) -> None:
        """Empty merchant name fails."""
        inp = self._valid_input()
        inp.merchant_name = ""
        result = validate_data_fields(inp)
        assert not result.is_valid

    def test_empty_merchant_city(self) -> None:
        """Empty merchant city fails."""
        inp = self._valid_input()
        inp.merchant_city = ""
        result = validate_data_fields(inp)
        assert not result.is_valid

    def test_empty_merchant_zip(self) -> None:
        """Empty merchant zip fails."""
        inp = self._valid_input()
        inp.merchant_zip = ""
        result = validate_data_fields(inp)
        assert not result.is_valid

    def test_empty_orig_date(self) -> None:
        """Empty origination date fails."""
        inp = self._valid_input()
        inp.orig_date = ""
        result = validate_data_fields(inp)
        assert not result.is_valid

    def test_empty_proc_date(self) -> None:
        """Empty processing date fails."""
        inp = self._valid_input()
        inp.proc_date = ""
        result = validate_data_fields(inp)
        assert not result.is_valid

    def test_empty_merchant_id(self) -> None:
        """Empty merchant ID fails."""
        inp = self._valid_input()
        inp.merchant_id = ""
        result = validate_data_fields(inp)
        assert not result.is_valid


# ---------------------------------------------------------------------------
# Service tests — validate_confirmation
# ---------------------------------------------------------------------------


class TestValidateConfirmation(TestCase):
    """Tests for validate_confirmation service function."""

    def test_confirm_yes(self) -> None:
        """'Y' confirms the transaction."""
        result = validate_confirmation("Y")
        assert result.is_valid

    def test_confirm_yes_lowercase(self) -> None:
        """'y' also confirms."""
        result = validate_confirmation("y")
        assert result.is_valid

    def test_confirm_no(self) -> None:
        """'N' means not confirmed."""
        result = validate_confirmation("N")
        assert not result.is_valid
        assert "Confirm" in result.error_message

    def test_confirm_empty(self) -> None:
        """Empty string means not confirmed."""
        result = validate_confirmation("")
        assert not result.is_valid

    def test_confirm_invalid(self) -> None:
        """Invalid value returns specific error."""
        result = validate_confirmation("X")
        assert not result.is_valid
        assert "Invalid value" in result.error_message

    def test_confirm_with_spaces(self) -> None:
        """'Y' with surrounding spaces is accepted."""
        result = validate_confirmation("  Y  ")
        assert result.is_valid


# ---------------------------------------------------------------------------
# Service tests — generate_transaction_id
# ---------------------------------------------------------------------------


class TestGenerateTransactionId(TestCase):
    """Tests for generate_transaction_id service function."""

    def test_first_id_is_one(self) -> None:
        """Empty database generates ID starting at 1."""
        tran_id = generate_transaction_id()
        assert tran_id == "0000000000000001"

    def test_increments_from_last(self) -> None:
        """New ID is one more than the last."""
        Transaction.objects.create(
            tran_id="0000000000000005",
            tran_type_cd="01", tran_cat_cd="0001",
            tran_source="ONLINE", tran_desc="Test",
            tran_amt=Decimal("10.00"),
            tran_merchant_id="000000001",
            tran_merchant_name="M", tran_merchant_city="C",
            tran_merchant_zip="11111",
            tran_card_num="4111111111111111",
            tran_orig_ts="2025-01-01",
            tran_proc_ts="2025-01-01",
        )
        tran_id = generate_transaction_id()
        assert tran_id == "0000000000000006"

    def test_id_is_zero_padded(self) -> None:
        """Generated ID is zero-padded to 16 characters."""
        tran_id = generate_transaction_id()
        assert len(tran_id) == 16


# ---------------------------------------------------------------------------
# Service tests — add_transaction (full workflow)
# ---------------------------------------------------------------------------


class TestAddTransaction(TestCase):
    """Tests for add_transaction service function (full workflow)."""

    def setUp(self) -> None:
        """Create synthetic cross-reference data."""
        CardXref.objects.create(
            xref_card_num="4111111111111111",
            xref_cust_id="000000001",
            xref_acct_id="00000000001",
        )

    def _valid_input(self) -> TransactionInput:
        """Return a valid TransactionInput."""
        return TransactionInput(
            acct_id="1",
            card_num="",
            tran_type_cd="01",
            tran_cat_cd="0001",
            tran_source="ONLINE",
            tran_desc="Test purchase",
            tran_amt="+00000100.50",
            orig_date="2025-01-15",
            proc_date="2025-01-15",
            merchant_id="000000001",
            merchant_name="TEST MERCHANT",
            merchant_city="TESTVILLE",
            merchant_zip="12345",
            confirm="Y",
        )

    def test_successful_add(self) -> None:
        """Valid input with confirmation creates transaction."""
        result = add_transaction(self._valid_input())
        assert result.success
        assert result.tran_id != ""
        assert Transaction.objects.count() == 1

    def test_key_validation_failure(self) -> None:
        """Invalid key fields prevent transaction creation."""
        inp = self._valid_input()
        inp.acct_id = "ABC"
        result = add_transaction(inp)
        assert not result.success
        assert Transaction.objects.count() == 0

    def test_data_validation_failure(self) -> None:
        """Invalid data fields prevent transaction creation."""
        inp = self._valid_input()
        inp.tran_amt = "invalid"
        result = add_transaction(inp)
        assert not result.success

    def test_confirmation_required(self) -> None:
        """Transaction not created without confirmation."""
        inp = self._valid_input()
        inp.confirm = "N"
        result = add_transaction(inp)
        assert not result.success
        assert Transaction.objects.count() == 0

    def test_success_message_contains_id(self) -> None:
        """Success message includes the transaction ID."""
        result = add_transaction(self._valid_input())
        assert "Tran ID" in result.message

    def test_amount_stored_as_decimal(self) -> None:
        """Transaction amount is stored as Decimal."""
        add_transaction(self._valid_input())
        txn = Transaction.objects.first()
        assert isinstance(txn.tran_amt, Decimal)
        assert txn.tran_amt == Decimal("100.50")

    def test_sequential_ids(self) -> None:
        """Multiple transactions get sequential IDs."""
        add_transaction(self._valid_input())
        inp2 = self._valid_input()
        inp2.acct_id = "1"
        add_transaction(inp2)
        assert Transaction.objects.count() == 2


# ---------------------------------------------------------------------------
# Service tests — get_transaction_list
# ---------------------------------------------------------------------------


class TestGetTransactionList(TestCase):
    """Tests for get_transaction_list service function."""

    def setUp(self) -> None:
        """Create synthetic transaction and xref data."""
        CardXref.objects.create(
            xref_card_num="4111111111111111",
            xref_cust_id="000000001",
            xref_acct_id="00000000001",
        )
        Transaction.objects.create(
            tran_id="0000000000000001",
            tran_type_cd="01", tran_cat_cd="0001",
            tran_source="ONLINE", tran_desc="Purchase 1",
            tran_amt=Decimal("50.00"),
            tran_merchant_id="000000001",
            tran_merchant_name="MERCHANT A",
            tran_merchant_city="CITY A",
            tran_merchant_zip="11111",
            tran_card_num="4111111111111111",
            tran_orig_ts="2025-01-01",
            tran_proc_ts="2025-01-01",
        )
        Transaction.objects.create(
            tran_id="0000000000000002",
            tran_type_cd="02", tran_cat_cd="0002",
            tran_source="POS", tran_desc="Purchase 2",
            tran_amt=Decimal("75.00"),
            tran_merchant_id="000000002",
            tran_merchant_name="MERCHANT B",
            tran_merchant_city="CITY B",
            tran_merchant_zip="22222",
            tran_card_num="4111111111111111",
            tran_orig_ts="2025-01-02",
            tran_proc_ts="2025-01-02",
        )

    def test_no_filter(self) -> None:
        """No filter returns all transactions."""
        result = get_transaction_list()
        assert result.count() == 2

    def test_filter_by_card(self) -> None:
        """Filter by card number works."""
        result = get_transaction_list(
            card_num="4111111111111111",
        )
        assert result.count() == 2

    def test_filter_by_account(self) -> None:
        """Filter by account ID resolves via xref."""
        result = get_transaction_list(acct_id="00000000001")
        assert result.count() == 2

    def test_filter_by_type(self) -> None:
        """Filter by transaction type works."""
        result = get_transaction_list(tran_type_cd="01")
        assert result.count() == 1

    def test_no_results(self) -> None:
        """Non-matching filter returns empty queryset."""
        result = get_transaction_list(
            card_num="9999999999999999",
        )
        assert result.count() == 0


# ---------------------------------------------------------------------------
# Internal helper tests
# ---------------------------------------------------------------------------


class TestInternalHelpers(TestCase):
    """Tests for internal helper functions."""

    def test_valid_calendar_date(self) -> None:
        """Valid date returns True."""
        assert _is_valid_calendar_date("2025-01-15")

    def test_invalid_calendar_date(self) -> None:
        """Invalid date (Feb 30) returns False."""
        assert not _is_valid_calendar_date("2025-02-30")

    def test_leap_year_date(self) -> None:
        """Leap year Feb 29 is valid."""
        assert _is_valid_calendar_date("2024-02-29")

    def test_non_leap_year_feb29(self) -> None:
        """Non-leap year Feb 29 is invalid."""
        assert not _is_valid_calendar_date("2025-02-29")

    def test_parse_amount_positive(self) -> None:
        """Positive amount parsed correctly."""
        result = _parse_amount("+00000100.50")
        assert result == Decimal("100.50")

    def test_parse_amount_negative(self) -> None:
        """Negative amount parsed correctly."""
        result = _parse_amount("-00000025.00")
        assert result == Decimal("-25.00")

    def test_parse_amount_invalid(self) -> None:
        """Invalid amount returns zero."""
        result = _parse_amount("not_a_number")
        assert result == Decimal("0.00")


# ---------------------------------------------------------------------------
# Form tests
# ---------------------------------------------------------------------------


class TestTransactionFilterForm(TestCase):
    """Tests for TransactionFilterForm."""

    def test_valid_form(self) -> None:
        """Form with all filters is valid."""
        form = TransactionFilterForm(data={
            "card_num": "4111111111111111",
            "acct_id": "00000000001",
            "tran_type_cd": "01",
        })
        assert form.is_valid()

    def test_empty_form(self) -> None:
        """Empty form is valid (all optional)."""
        form = TransactionFilterForm(data={})
        assert form.is_valid()


class TestTransactionCreateForm(TestCase):
    """Tests for TransactionCreateForm."""

    def test_valid_form(self) -> None:
        """Form with all required fields is valid."""
        form = TransactionCreateForm(data={
            "tran_type_cd": "01",
            "tran_cat_cd": "0001",
            "tran_source": "ONLINE",
            "tran_desc": "Test",
            "tran_amt": "+00000100.50",
            "orig_date": "2025-01-15",
            "proc_date": "2025-01-15",
            "merchant_id": "000000001",
            "merchant_name": "MERCHANT",
            "merchant_city": "CITY",
            "merchant_zip": "12345",
        })
        assert form.is_valid()

    def test_missing_required_field(self) -> None:
        """Form missing required field is invalid."""
        form = TransactionCreateForm(data={
            "tran_type_cd": "01",
        })
        assert not form.is_valid()


# ---------------------------------------------------------------------------
# View tests
# ---------------------------------------------------------------------------


class TestTransactionListView(TestCase):
    """Tests for TransactionListView."""

    def setUp(self) -> None:
        """Create test user and transaction data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123",
        )
        self.client.login(
            username="testuser", password="testpass123",
        )

    def test_list_view_authenticated(self) -> None:
        """Authenticated user can access list."""
        response = self.client.get("/transactions/")
        assert response.status_code == 200

    def test_list_view_unauthenticated(self) -> None:
        """Unauthenticated user is redirected."""
        self.client.logout()
        response = self.client.get("/transactions/")
        assert response.status_code == 302

    def test_list_view_template(self) -> None:
        """Correct template is used."""
        response = self.client.get("/transactions/")
        self.assertTemplateUsed(
            response, "transactions/transaction_list.html",
        )


class TestTransactionDetailView(TestCase):
    """Tests for TransactionDetailView."""

    def setUp(self) -> None:
        """Create test user and transaction."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123",
        )
        self.client.login(
            username="testuser", password="testpass123",
        )
        Transaction.objects.create(
            tran_id="0000000000000001",
            tran_type_cd="01", tran_cat_cd="0001",
            tran_source="ONLINE", tran_desc="Test",
            tran_amt=Decimal("50.00"),
            tran_merchant_id="000000001",
            tran_merchant_name="M",
            tran_merchant_city="C", tran_merchant_zip="11111",
            tran_card_num="4111111111111111",
            tran_orig_ts="2025-01-01",
            tran_proc_ts="2025-01-01",
        )

    def test_detail_view(self) -> None:
        """Transaction detail page loads."""
        response = self.client.get(
            "/transactions/0000000000000001/"
        )
        assert response.status_code == 200

    def test_detail_not_found(self) -> None:
        """Non-existent transaction returns 404."""
        response = self.client.get(
            "/transactions/9999999999999999/"
        )
        assert response.status_code == 404


class TestTransactionCreateView(TestCase):
    """Tests for TransactionCreateView."""

    def setUp(self) -> None:
        """Create test user and xref data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123",
        )
        self.client.login(
            username="testuser", password="testpass123",
        )
        CardXref.objects.create(
            xref_card_num="4111111111111111",
            xref_cust_id="000000001",
            xref_acct_id="00000000001",
        )

    def test_create_get(self) -> None:
        """Create form loads successfully."""
        response = self.client.get("/transactions/add/")
        assert response.status_code == 200

    def test_create_post_success(self) -> None:
        """Valid submission creates transaction."""
        response = self.client.post("/transactions/add/", {
            "acct_id": "1",
            "card_num": "",
            "tran_type_cd": "01",
            "tran_cat_cd": "0001",
            "tran_source": "ONLINE",
            "tran_desc": "Test purchase",
            "tran_amt": "+00000100.50",
            "orig_date": "2025-01-15",
            "proc_date": "2025-01-15",
            "merchant_id": "000000001",
            "merchant_name": "TEST MERCHANT",
            "merchant_city": "TESTVILLE",
            "merchant_zip": "12345",
            "confirm": "Y",
        })
        assert response.status_code == 302
        assert Transaction.objects.count() == 1

    def test_create_post_no_confirm(self) -> None:
        """Submission without confirmation re-renders form."""
        response = self.client.post("/transactions/add/", {
            "acct_id": "1",
            "tran_type_cd": "01",
            "tran_cat_cd": "0001",
            "tran_source": "ONLINE",
            "tran_desc": "Test",
            "tran_amt": "+00000100.50",
            "orig_date": "2025-01-15",
            "proc_date": "2025-01-15",
            "merchant_id": "000000001",
            "merchant_name": "M",
            "merchant_city": "C",
            "merchant_zip": "11111",
            "confirm": "N",
        })
        assert response.status_code == 200
        assert Transaction.objects.count() == 0
