"""
Unit tests for Phase 4: Credit Card Management.

Tests cover:
- Card model (creation, str representation, CPS 234 masking)
- CardXref model
- Account model
- Card services (list, detail, validate, update)
- Card forms (filter, update validation)
- Card views (list, detail, update)

Coverage target: 70% minimum.
All test data is synthetic — no real customer data (CPS 234).
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase

from python.cards.forms import CardFilterForm, CardUpdateForm
from python.cards.models import Account, Card, CardXref
from python.cards.services import (
    get_card_detail,
    get_card_list,
    update_card,
    validate_card_update,
)


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestCardModel(TestCase):
    """Tests for the Card model."""

    def test_create_card(self) -> None:
        """Card record can be created with all fields."""
        card = Card.objects.create(
            card_num="4111111111111111",
            card_acct_id="00000000001",
            card_cvv_cd="123",
            card_embossed_name="JOHN DOE",
            card_expiration_date="2027-12-01",
            card_active_status="Y",
        )
        assert card.pk is not None
        assert card.card_num == "4111111111111111"

    def test_str_masks_card_number(self) -> None:
        """CPS 234: Card str representation masks all but last 4."""
        card = Card(card_num="4111111111111111")
        assert str(card) == "****-****-****-1111"

    def test_str_short_card_number(self) -> None:
        """Short card numbers display as masked."""
        card = Card(card_num="12")
        assert str(card) == "****"

    def test_ordering(self) -> None:
        """Cards are ordered by card_num."""
        Card.objects.create(
            card_num="9999999999999999",
            card_acct_id="00000000001",
            card_cvv_cd="123",
            card_embossed_name="BETA USER",
            card_expiration_date="2027-01-01",
        )
        Card.objects.create(
            card_num="1111111111111111",
            card_acct_id="00000000002",
            card_cvv_cd="456",
            card_embossed_name="ALPHA USER",
            card_expiration_date="2027-06-01",
        )
        cards = list(Card.objects.all())
        assert cards[0].card_num == "1111111111111111"
        assert cards[1].card_num == "9999999999999999"


class TestCardXrefModel(TestCase):
    """Tests for the CardXref model."""

    def test_create_xref(self) -> None:
        """CardXref record can be created."""
        xref = CardXref.objects.create(
            xref_card_num="4111111111111111",
            xref_cust_id="000000001",
            xref_acct_id="00000000001",
        )
        assert xref.pk is not None

    def test_str_masks_card(self) -> None:
        """CPS 234: Xref str masks card number."""
        xref = CardXref(xref_card_num="4111111111111111")
        assert "1111" in str(xref)
        assert "4111111111111111" not in str(xref)


class TestAccountModel(TestCase):
    """Tests for the Account model."""

    def test_create_account(self) -> None:
        """Account record uses Decimal for monetary fields."""
        acct = Account.objects.create(
            acct_id="00000000001",
            acct_active_status="Y",
            acct_curr_bal=Decimal("5000.00"),
            acct_credit_limit=Decimal("10000.00"),
        )
        assert acct.acct_curr_bal == Decimal("5000.00")
        assert isinstance(acct.acct_curr_bal, Decimal)

    def test_str_representation(self) -> None:
        """Account str shows account ID."""
        acct = Account(acct_id="00000000001")
        assert str(acct) == "Account 00000000001"


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


class TestGetCardList(TestCase):
    """Tests for get_card_list service function."""

    def setUp(self) -> None:
        """Create synthetic test data."""
        Card.objects.create(
            card_num="4111111111111111",
            card_acct_id="00000000001",
            card_cvv_cd="123",
            card_embossed_name="TEST USER ONE",
            card_expiration_date="2027-12-01",
        )
        Card.objects.create(
            card_num="4222222222222222",
            card_acct_id="00000000001",
            card_cvv_cd="456",
            card_embossed_name="TEST USER TWO",
            card_expiration_date="2028-06-01",
        )
        Card.objects.create(
            card_num="5333333333333333",
            card_acct_id="00000000002",
            card_cvv_cd="789",
            card_embossed_name="TEST USER THREE",
            card_expiration_date="2029-01-01",
        )

    def test_admin_sees_all_cards(self) -> None:
        """Admin user with no filter sees all cards."""
        result = get_card_list(is_admin=True)
        assert result.count() == 3

    def test_filter_by_account_id(self) -> None:
        """Filter by account ID returns matching cards."""
        result = get_card_list(acct_id="00000000001")
        assert result.count() == 2

    def test_filter_by_card_prefix(self) -> None:
        """Filter by card number prefix works."""
        result = get_card_list(
            card_num_filter="42", is_admin=True,
        )
        assert result.count() == 1

    def test_non_admin_no_filter_returns_empty(self) -> None:
        """Non-admin with no account filter gets empty result."""
        result = get_card_list(is_admin=False)
        assert result.count() == 0

    def test_combined_filters(self) -> None:
        """Account ID and card prefix can be combined."""
        result = get_card_list(
            acct_id="00000000001",
            card_num_filter="41",
        )
        assert result.count() == 1


class TestGetCardDetail(TestCase):
    """Tests for get_card_detail service function."""

    def setUp(self) -> None:
        """Create synthetic test card."""
        Card.objects.create(
            card_num="4111111111111111",
            card_acct_id="00000000001",
            card_cvv_cd="123",
            card_embossed_name="TEST USER",
            card_expiration_date="2027-12-01",
        )

    def test_found(self) -> None:
        """Returns card when both acct and card match."""
        card = get_card_detail("00000000001", "4111111111111111")
        assert card is not None
        assert card.card_embossed_name == "TEST USER"

    def test_not_found(self) -> None:
        """Returns None when card not found."""
        card = get_card_detail("99999999999", "0000000000000000")
        assert card is None


class TestValidateCardUpdate(TestCase):
    """Tests for validate_card_update service function."""

    def test_valid_input(self) -> None:
        """All valid inputs pass validation."""
        result = validate_card_update(
            card_name="JOHN DOE",
            card_status="Y",
            expiry_month="12",
            expiry_year="2027",
        )
        assert result.success is True

    def test_empty_name(self) -> None:
        """Empty card name fails validation."""
        result = validate_card_update(
            card_name="   ",
            card_status="Y",
            expiry_month="12",
            expiry_year="2027",
        )
        assert result.success is False
        assert "name" in result.message.lower()

    def test_invalid_name_characters(self) -> None:
        """Name with non-alpha characters fails."""
        result = validate_card_update(
            card_name="JOHN123",
            card_status="Y",
            expiry_month="12",
            expiry_year="2027",
        )
        assert result.success is False

    def test_invalid_status(self) -> None:
        """Status other than Y/N fails."""
        result = validate_card_update(
            card_name="JOHN DOE",
            card_status="X",
            expiry_month="12",
            expiry_year="2027",
        )
        assert result.success is False

    def test_invalid_month_zero(self) -> None:
        """Month 0 fails validation."""
        result = validate_card_update(
            card_name="JOHN DOE",
            card_status="Y",
            expiry_month="0",
            expiry_year="2027",
        )
        assert result.success is False

    def test_invalid_month_thirteen(self) -> None:
        """Month 13 fails validation."""
        result = validate_card_update(
            card_name="JOHN DOE",
            card_status="Y",
            expiry_month="13",
            expiry_year="2027",
        )
        assert result.success is False

    def test_invalid_year_too_low(self) -> None:
        """Year below 1950 fails."""
        result = validate_card_update(
            card_name="JOHN DOE",
            card_status="Y",
            expiry_month="12",
            expiry_year="1900",
        )
        assert result.success is False

    def test_invalid_year_too_high(self) -> None:
        """Year above 2099 fails."""
        result = validate_card_update(
            card_name="JOHN DOE",
            card_status="Y",
            expiry_month="12",
            expiry_year="2100",
        )
        assert result.success is False

    def test_non_numeric_month(self) -> None:
        """Non-numeric month fails."""
        result = validate_card_update(
            card_name="JOHN DOE",
            card_status="Y",
            expiry_month="AB",
            expiry_year="2027",
        )
        assert result.success is False


class TestUpdateCard(TestCase):
    """Tests for update_card service function."""

    def setUp(self) -> None:
        """Create synthetic test card."""
        Card.objects.create(
            card_num="4111111111111111",
            card_acct_id="00000000001",
            card_cvv_cd="123",
            card_embossed_name="ORIGINAL NAME",
            card_expiration_date="2027-12-01",
            card_active_status="Y",
        )

    def test_successful_update(self) -> None:
        """Card is updated with valid new values."""
        result = update_card(
            card_num="4111111111111111",
            card_name="NEW NAME",
            card_status="N",
            expiry_month="06",
            expiry_year="2028",
        )
        assert result.success is True
        card = Card.objects.get(card_num="4111111111111111")
        assert card.card_embossed_name == "NEW NAME"
        assert card.card_active_status == "N"

    def test_no_change_detected(self) -> None:
        """No-change scenario returns appropriate message."""
        result = update_card(
            card_num="4111111111111111",
            card_name="ORIGINAL NAME",
            card_status="Y",
            expiry_month="12",
            expiry_year="2027",
        )
        assert result.success is False
        assert "no change" in result.message.lower()

    def test_card_not_found(self) -> None:
        """Non-existent card returns error."""
        result = update_card(
            card_num="0000000000000000",
            card_name="TEST",
            card_status="Y",
            expiry_month="12",
            expiry_year="2027",
        )
        assert result.success is False

    def test_validation_failure(self) -> None:
        """Invalid input returns validation error."""
        result = update_card(
            card_num="4111111111111111",
            card_name="JOHN123",
            card_status="Y",
            expiry_month="12",
            expiry_year="2027",
        )
        assert result.success is False


# ---------------------------------------------------------------------------
# Form tests
# ---------------------------------------------------------------------------


class TestCardFilterForm(TestCase):
    """Tests for CardFilterForm."""

    def test_valid_form(self) -> None:
        """Form with valid data is valid."""
        form = CardFilterForm(data={
            "acct_id": "00000000001",
            "card_num": "4111",
        })
        assert form.is_valid()

    def test_empty_form_valid(self) -> None:
        """Empty form is valid (all fields optional)."""
        form = CardFilterForm(data={})
        assert form.is_valid()


class TestCardUpdateForm(TestCase):
    """Tests for CardUpdateForm."""

    def test_valid_form(self) -> None:
        """Form with valid data passes all validation."""
        form = CardUpdateForm(data={
            "card_name": "JOHN DOE",
            "card_status": "Y",
            "expiry_month": "12",
            "expiry_year": "2027",
        })
        assert form.is_valid()

    def test_invalid_name_characters(self) -> None:
        """Name with numbers fails form validation."""
        form = CardUpdateForm(data={
            "card_name": "JOHN123",
            "card_status": "Y",
            "expiry_month": "12",
            "expiry_year": "2027",
        })
        assert not form.is_valid()

    def test_invalid_month(self) -> None:
        """Month outside 1-12 fails."""
        form = CardUpdateForm(data={
            "card_name": "JOHN DOE",
            "card_status": "Y",
            "expiry_month": "13",
            "expiry_year": "2027",
        })
        assert not form.is_valid()

    def test_invalid_year(self) -> None:
        """Year outside 1950-2099 fails."""
        form = CardUpdateForm(data={
            "card_name": "JOHN DOE",
            "card_status": "Y",
            "expiry_month": "12",
            "expiry_year": "2100",
        })
        assert not form.is_valid()


# ---------------------------------------------------------------------------
# View tests
# ---------------------------------------------------------------------------


class TestCardListView(TestCase):
    """Tests for CardListView."""

    def setUp(self) -> None:
        """Create test user and card data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            is_staff=True,
        )
        self.client.login(
            username="testuser", password="testpass123",
        )
        Card.objects.create(
            card_num="4111111111111111",
            card_acct_id="00000000001",
            card_cvv_cd="123",
            card_embossed_name="TEST USER",
            card_expiration_date="2027-12-01",
        )

    def test_list_view_authenticated(self) -> None:
        """Authenticated admin can access card list."""
        response = self.client.get("/cards/")
        assert response.status_code == 200

    def test_list_view_unauthenticated(self) -> None:
        """Unauthenticated user is redirected."""
        self.client.logout()
        response = self.client.get("/cards/")
        assert response.status_code == 302

    def test_list_view_with_filter(self) -> None:
        """Filter parameter is applied."""
        response = self.client.get(
            "/cards/?acct_id=00000000001"
        )
        assert response.status_code == 200

    def test_list_view_template(self) -> None:
        """Correct template is used."""
        response = self.client.get("/cards/")
        self.assertTemplateUsed(
            response, "cards/card_list.html",
        )


class TestCardDetailView(TestCase):
    """Tests for CardDetailView."""

    def setUp(self) -> None:
        """Create test user and card."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
        )
        self.client.login(
            username="testuser", password="testpass123",
        )
        Card.objects.create(
            card_num="4111111111111111",
            card_acct_id="00000000001",
            card_cvv_cd="123",
            card_embossed_name="TEST USER",
            card_expiration_date="2027-12-01",
        )

    def test_detail_view(self) -> None:
        """Card detail page loads successfully."""
        response = self.client.get("/cards/4111111111111111/")
        assert response.status_code == 200

    def test_detail_view_not_found(self) -> None:
        """Non-existent card returns 404."""
        response = self.client.get("/cards/0000000000000000/")
        assert response.status_code == 404

    def test_detail_template(self) -> None:
        """Correct template is used."""
        response = self.client.get("/cards/4111111111111111/")
        self.assertTemplateUsed(
            response, "cards/card_detail.html",
        )


class TestCardUpdateView(TestCase):
    """Tests for CardUpdateView."""

    def setUp(self) -> None:
        """Create test user and card."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
        )
        self.client.login(
            username="testuser", password="testpass123",
        )
        Card.objects.create(
            card_num="4111111111111111",
            card_acct_id="00000000001",
            card_cvv_cd="123",
            card_embossed_name="ORIGINAL NAME",
            card_expiration_date="2027-12-01",
            card_active_status="Y",
        )

    def test_update_get(self) -> None:
        """Update form loads with current values."""
        response = self.client.get(
            "/cards/4111111111111111/update/"
        )
        assert response.status_code == 200

    def test_update_post_success(self) -> None:
        """Valid update redirects to detail page."""
        response = self.client.post(
            "/cards/4111111111111111/update/",
            {
                "card_name": "UPDATED NAME",
                "card_status": "N",
                "expiry_month": "06",
                "expiry_year": "2028",
            },
        )
        assert response.status_code == 302

    def test_update_post_invalid(self) -> None:
        """Invalid update re-renders form."""
        response = self.client.post(
            "/cards/4111111111111111/update/",
            {
                "card_name": "BAD123",
                "card_status": "Y",
                "expiry_month": "12",
                "expiry_year": "2027",
            },
        )
        assert response.status_code == 200

    def test_update_not_found(self) -> None:
        """Update on non-existent card returns 404."""
        response = self.client.get(
            "/cards/0000000000000000/update/"
        )
        assert response.status_code == 404
