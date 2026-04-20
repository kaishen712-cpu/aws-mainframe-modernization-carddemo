"""
Unit tests for cocrdlic.py — the Python translation of COCRDLIC.CBL.

These tests verify the business rules for the Credit Card List function
including search, pagination, and card selection.
"""

import unittest

from coactvwc import (
    CardRecord,
    CardXrefRecord,
    InMemoryCardXrefRepository,
)
from cocrdlic import (
    InMemoryCardRepository,
    PAGE_SIZE,
    get_header_info,
    search_cards,
    select_card,
    validate_account_filter,
    validate_card_filter,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_card(num: int, acct_id: str = "00000000001") -> CardRecord:
    """Create a card record with a sequential card number."""
    return CardRecord(
        card_num=str(num).zfill(16),
        acct_id=acct_id,
        cvv_cd="123",
        embossed_name=f"CARDHOLDER {num}",
        expiration_date="2025-12-31",
        active_status="Y",
    )


def _make_repos_with_cards(count: int = 15):
    """Return repos pre-loaded with *count* cards."""
    card_repo = InMemoryCardRepository()
    xref_repo = InMemoryCardXrefRepository()
    for i in range(1, count + 1):
        card = _make_card(i)
        card_repo.add_card(card)
        xref_repo.add_xref(CardXrefRecord(
            card_num=card.card_num,
            cust_id=str(i).zfill(9),
            acct_id="00000000001",
        ))
    return card_repo, xref_repo


# ===========================================================================
# 1. Account filter validation
# ===========================================================================

class TestValidateAccountFilter(unittest.TestCase):
    """Tests for account ID filter validation."""

    def test_blank_is_valid(self):
        self.assertTrue(validate_account_filter("").is_valid)

    def test_asterisk_is_valid(self):
        self.assertTrue(validate_account_filter("*").is_valid)

    def test_numeric_is_valid(self):
        self.assertTrue(validate_account_filter("00000000001").is_valid)

    def test_non_numeric_invalid(self):
        result = validate_account_filter("ABC")
        self.assertFalse(result.is_valid)
        self.assertIn("11 digit number", result.error_message)

    def test_all_zeros_invalid(self):
        result = validate_account_filter("00000000000")
        self.assertFalse(result.is_valid)


# ===========================================================================
# 2. Card filter validation
# ===========================================================================

class TestValidateCardFilter(unittest.TestCase):
    """Tests for card number filter validation."""

    def test_blank_is_valid(self):
        self.assertTrue(validate_card_filter("").is_valid)

    def test_asterisk_is_valid(self):
        self.assertTrue(validate_card_filter("*").is_valid)

    def test_numeric_is_valid(self):
        self.assertTrue(validate_card_filter("4000123456789010").is_valid)

    def test_non_numeric_invalid(self):
        result = validate_card_filter("ABCXYZ")
        self.assertFalse(result.is_valid)
        self.assertIn("16 digit number", result.error_message)

    def test_all_zeros_invalid(self):
        result = validate_card_filter("0000000000000000")
        self.assertFalse(result.is_valid)


# ===========================================================================
# 3. Search cards
# ===========================================================================

class TestSearchCards(unittest.TestCase):
    """Tests for the search_cards function."""

    def test_no_filter_returns_all(self):
        card_repo, xref_repo = _make_repos_with_cards(5)
        result = search_cards("", "", card_repo, xref_repo)
        self.assertTrue(result.success)
        self.assertEqual(result.total_cards, 5)
        self.assertEqual(len(result.cards), 5)

    def test_no_filter_pagination_page1(self):
        card_repo, xref_repo = _make_repos_with_cards(15)
        result = search_cards("", "", card_repo, xref_repo, page=1)
        self.assertTrue(result.success)
        self.assertEqual(len(result.cards), PAGE_SIZE)
        self.assertTrue(result.has_more)
        self.assertFalse(result.has_previous)

    def test_no_filter_pagination_page2(self):
        card_repo, xref_repo = _make_repos_with_cards(15)
        result = search_cards("", "", card_repo, xref_repo, page=2)
        self.assertTrue(result.success)
        self.assertEqual(len(result.cards), PAGE_SIZE)
        self.assertTrue(result.has_more)
        self.assertTrue(result.has_previous)

    def test_no_filter_pagination_last_page(self):
        card_repo, xref_repo = _make_repos_with_cards(15)
        result = search_cards("", "", card_repo, xref_repo, page=3)
        self.assertTrue(result.success)
        self.assertEqual(len(result.cards), 1)  # 15 - 14 = 1
        self.assertFalse(result.has_more)
        self.assertTrue(result.has_previous)

    def test_filter_by_account(self):
        card_repo = InMemoryCardRepository()
        xref_repo = InMemoryCardXrefRepository()
        card_repo.add_card(CardRecord(
            card_num="4000000000000001", acct_id="00000000001",
            embossed_name="CARD 1", expiration_date="2025-12-31",
            active_status="Y",
        ))
        card_repo.add_card(CardRecord(
            card_num="4000000000000002", acct_id="00000000002",
            embossed_name="CARD 2", expiration_date="2025-12-31",
            active_status="Y",
        ))
        result = search_cards("1", "", card_repo, xref_repo)
        self.assertTrue(result.success)
        self.assertEqual(result.total_cards, 1)
        self.assertEqual(result.cards[0].acct_id, "00000000001")

    def test_filter_by_card_number(self):
        card_repo = InMemoryCardRepository()
        xref_repo = InMemoryCardXrefRepository()
        card_repo.add_card(CardRecord(
            card_num="4000000000000001", acct_id="00000000001",
            embossed_name="CARD 1", expiration_date="2025-12-31",
            active_status="Y",
        ))
        card_repo.add_card(CardRecord(
            card_num="4000000000000002", acct_id="00000000002",
            embossed_name="CARD 2", expiration_date="2025-12-31",
            active_status="Y",
        ))
        result = search_cards("", "4000000000000001", card_repo, xref_repo)
        self.assertTrue(result.success)
        self.assertEqual(result.total_cards, 1)
        self.assertEqual(result.cards[0].card_num, "4000000000000001")

    def test_no_cards_found(self):
        card_repo = InMemoryCardRepository()
        xref_repo = InMemoryCardXrefRepository()
        result = search_cards("1", "", card_repo, xref_repo)
        self.assertFalse(result.success)
        self.assertIn("No cards found", result.message)

    def test_invalid_account_filter(self):
        card_repo, xref_repo = _make_repos_with_cards(5)
        result = search_cards("ABC", "", card_repo, xref_repo)
        self.assertFalse(result.success)
        self.assertIn("11 digit number", result.message)

    def test_invalid_card_filter(self):
        card_repo, xref_repo = _make_repos_with_cards(5)
        result = search_cards("", "XYZ", card_repo, xref_repo)
        self.assertFalse(result.success)
        self.assertIn("16 digit number", result.message)

    def test_card_list_item_fields(self):
        card_repo, xref_repo = _make_repos_with_cards(1)
        result = search_cards("", "", card_repo, xref_repo)
        self.assertTrue(result.success)
        item = result.cards[0]
        self.assertEqual(item.card_num, "0000000000000001")
        self.assertEqual(item.acct_id, "00000000001")
        self.assertEqual(item.card_status, "Y")
        self.assertEqual(item.expiration_date, "2025-12-31")
        self.assertIn("CARDHOLDER", item.embossed_name)


# ===========================================================================
# 4. Card selection
# ===========================================================================

class TestSelectCard(unittest.TestCase):
    """Tests for the select_card function."""

    def test_select_for_view(self):
        card_repo = InMemoryCardRepository()
        card_repo.add_card(CardRecord(
            card_num="4000000000000001", acct_id="00000000001",
        ))
        result = select_card("4000000000000001", "view", card_repo)
        self.assertTrue(result.success)
        self.assertEqual(result.target_program, "COCRDSLC")
        self.assertEqual(result.selected_card_num, "4000000000000001")

    def test_select_for_update(self):
        card_repo = InMemoryCardRepository()
        card_repo.add_card(CardRecord(
            card_num="4000000000000001", acct_id="00000000001",
        ))
        result = select_card("4000000000000001", "update", card_repo)
        self.assertTrue(result.success)
        self.assertEqual(result.target_program, "COCRDUPC")

    def test_select_nonexistent(self):
        card_repo = InMemoryCardRepository()
        result = select_card("9999999999999999", "view", card_repo)
        self.assertFalse(result.success)
        self.assertIn("not found", result.message)


# ===========================================================================
# 5. Header info
# ===========================================================================

class TestGetHeaderInfo(unittest.TestCase):
    """Tests for screen header information."""

    def test_program_name(self):
        info = get_header_info()
        self.assertEqual(info["program_name"], "COCRDLIC")

    def test_transaction_id(self):
        info = get_header_info()
        self.assertEqual(info["transaction_id"], "CCLI")


# ===========================================================================
# 6. In-memory card repository
# ===========================================================================

class TestInMemoryCardRepository(unittest.TestCase):
    """Tests for InMemoryCardRepository."""

    def test_add_and_get(self):
        repo = InMemoryCardRepository()
        card = _make_card(1)
        repo.add_card(card)
        result = repo.get_card("0000000000000001")
        self.assertIsNotNone(result)

    def test_get_nonexistent(self):
        repo = InMemoryCardRepository()
        self.assertIsNone(repo.get_card("9999999999999999"))

    def test_list_by_account(self):
        repo = InMemoryCardRepository()
        repo.add_card(_make_card(1, "00000000001"))
        repo.add_card(_make_card(2, "00000000001"))
        repo.add_card(_make_card(3, "00000000002"))
        result = repo.list_cards_by_account("00000000001")
        self.assertEqual(len(result), 2)

    def test_list_cards_from(self):
        repo = InMemoryCardRepository()
        for i in range(1, 6):
            repo.add_card(_make_card(i))
        result = repo.list_cards_from("0000000000000003", 2)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].card_num, "0000000000000003")

    def test_list_all_cards(self):
        repo = InMemoryCardRepository()
        for i in range(1, 4):
            repo.add_card(_make_card(i))
        self.assertEqual(len(repo.list_all_cards()), 3)


if __name__ == "__main__":
    unittest.main()
