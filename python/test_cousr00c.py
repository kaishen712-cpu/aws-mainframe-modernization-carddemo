"""
Unit tests for cousr00c.py — the Python translation of COUSR00C.CBL.

These tests verify the same business rules that the original COBOL program
enforces, organised by functional area.
"""

import unittest

from user_security_repository import (
    InMemoryUserSecurityRepository,
    UserSecurityRecord,
)
from cousr00c import (
    PAGE_SIZE,
    MSG_INVALID_SELECTION,
    MSG_TOP_OF_PAGE,
    MSG_BOTTOM_OF_PAGE,
    browse_users_forward,
    browse_users_backward,
    get_header_info,
    get_initial_page,
    process_page_backward,
    process_page_forward,
    process_user_selection,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_repo(count: int = 25) -> InMemoryUserSecurityRepository:
    """Return a repo pre-loaded with *count* user records."""
    repo = InMemoryUserSecurityRepository()
    for i in range(1, count + 1):
        uid = f"USER{i:04d}"
        repo.seed(UserSecurityRecord(
            user_id=uid,
            first_name=f"First{i}",
            last_name=f"Last{i}",
            password="PASS1234",
            user_type="A" if i % 5 == 0 else "U",
        ))
    return repo


def _empty_repo() -> InMemoryUserSecurityRepository:
    return InMemoryUserSecurityRepository()


# ===========================================================================
# 1. User selection logic
# ===========================================================================

class TestProcessUserSelection(unittest.TestCase):
    """Tests corresponding to the selection EVALUATE in PROCESS-ENTER-KEY."""

    def test_select_update_uppercase(self):
        result = process_user_selection("U", "USER0001")
        self.assertEqual(result.action, "update")
        self.assertEqual(result.selected_user_id, "USER0001")
        self.assertEqual(result.error_message, "")

    def test_select_update_lowercase(self):
        result = process_user_selection("u", "USER0002")
        self.assertEqual(result.action, "update")
        self.assertEqual(result.selected_user_id, "USER0002")

    def test_select_delete_uppercase(self):
        result = process_user_selection("D", "USER0003")
        self.assertEqual(result.action, "delete")
        self.assertEqual(result.selected_user_id, "USER0003")

    def test_select_delete_lowercase(self):
        result = process_user_selection("d", "USER0004")
        self.assertEqual(result.action, "delete")
        self.assertEqual(result.selected_user_id, "USER0004")

    def test_invalid_selection_value(self):
        result = process_user_selection("X", "USER0001")
        self.assertEqual(result.action, "")
        self.assertEqual(result.error_message, MSG_INVALID_SELECTION)

    def test_no_selection_blank_flag(self):
        result = process_user_selection("", "USER0001")
        self.assertEqual(result.action, "")
        self.assertEqual(result.error_message, "")

    def test_no_selection_blank_user(self):
        result = process_user_selection("U", "")
        self.assertEqual(result.action, "")
        self.assertEqual(result.error_message, "")

    def test_no_selection_both_blank(self):
        result = process_user_selection("", "")
        self.assertEqual(result.action, "")
        self.assertEqual(result.error_message, "")

    def test_spaces_only_flag(self):
        result = process_user_selection("   ", "USER0001")
        self.assertEqual(result.action, "")
        self.assertEqual(result.error_message, "")

    def test_invalid_digit_selection(self):
        result = process_user_selection("1", "USER0001")
        self.assertEqual(result.action, "")
        self.assertIn("Invalid selection", result.error_message)


# ===========================================================================
# 2. Forward browsing
# ===========================================================================

class TestBrowseUsersForward(unittest.TestCase):
    """Tests corresponding to PROCESS-PAGE-FORWARD."""

    def test_first_page_full(self):
        """25 users → first page has 10 rows, has_next=True."""
        repo = _make_repo(25)
        page = browse_users_forward(repo, "", 0)

        self.assertEqual(len(page.rows), PAGE_SIZE)
        self.assertEqual(page.page_num, 1)
        self.assertTrue(page.has_next_page)
        self.assertEqual(page.rows[0].user_id, "USER0001")
        self.assertEqual(page.rows[9].user_id, "USER0010")

    def test_first_page_partial(self):
        """5 users → first page has 5 rows, has_next=False."""
        repo = _make_repo(5)
        page = browse_users_forward(repo, "", 0)

        self.assertEqual(len(page.rows), 5)
        self.assertEqual(page.page_num, 1)
        self.assertFalse(page.has_next_page)

    def test_empty_file(self):
        """No users → empty page."""
        repo = _empty_repo()
        page = browse_users_forward(repo, "", 0)

        self.assertEqual(len(page.rows), 0)
        self.assertEqual(page.page_num, 0)
        self.assertFalse(page.has_next_page)

    def test_rows_contain_correct_data(self):
        """Verify the field mapping from record to row."""
        repo = _make_repo(3)
        page = browse_users_forward(repo, "", 0)

        row = page.rows[0]
        self.assertEqual(row.user_id, "USER0001")
        self.assertEqual(row.first_name, "First1")
        self.assertEqual(row.last_name, "Last1")
        self.assertEqual(row.user_type, "U")

    def test_start_from_specific_user(self):
        """Browsing from a specific user ID starts at that user."""
        repo = _make_repo(25)
        page = browse_users_forward(repo, "USER0011", 1)

        self.assertEqual(page.rows[0].user_id, "USER0011")
        self.assertEqual(len(page.rows), PAGE_SIZE)
        self.assertEqual(page.page_num, 2)

    def test_tracks_first_and_last_ids(self):
        """Page should track first and last user IDs for pagination."""
        repo = _make_repo(25)
        page = browse_users_forward(repo, "", 0)

        self.assertEqual(page.first_user_id, "USER0001")
        self.assertEqual(page.last_user_id, "USER0010")


# ===========================================================================
# 3. Backward browsing
# ===========================================================================

class TestBrowseUsersBackward(unittest.TestCase):
    """Tests corresponding to PROCESS-PAGE-BACKWARD."""

    def test_backward_from_end(self):
        """Browsing backward from end of 25 users gets last 10."""
        repo = _make_repo(25)
        page = browse_users_backward(repo, "USER0025", 3)

        self.assertEqual(len(page.rows), PAGE_SIZE)
        # Should be in ascending order
        self.assertEqual(page.rows[0].user_id, "USER0016")
        self.assertEqual(page.rows[9].user_id, "USER0025")

    def test_backward_returns_ascending_order(self):
        """Records returned by backward browse should be in ascending order."""
        repo = _make_repo(15)
        page = browse_users_backward(repo, "USER0015", 2)

        ids = [r.user_id for r in page.rows]
        self.assertEqual(ids, sorted(ids))

    def test_backward_has_next_true(self):
        """Going backward should always report has_next_page = True."""
        repo = _make_repo(25)
        page = browse_users_backward(repo, "USER0020", 3)
        self.assertTrue(page.has_next_page)

    def test_empty_file_backward(self):
        """No users → empty page backward."""
        repo = _empty_repo()
        page = browse_users_backward(repo, "", 1)
        self.assertEqual(len(page.rows), 0)


# ===========================================================================
# 4. Page forward / backward (PF8 / PF7)
# ===========================================================================

class TestProcessPageForward(unittest.TestCase):
    """Tests corresponding to PROCESS-PF8-KEY."""

    def test_page_forward_when_next_exists(self):
        repo = _make_repo(25)
        page = process_page_forward(repo, "USER0010", 1, True)

        self.assertEqual(len(page.rows), PAGE_SIZE)
        self.assertEqual(page.page_num, 2)
        self.assertEqual(page.rows[0].user_id, "USER0011")

    def test_page_forward_at_end(self):
        """When no next page, display bottom-of-page message."""
        repo = _make_repo(10)
        page = process_page_forward(repo, "USER0010", 1, False)

        self.assertEqual(page.message, MSG_BOTTOM_OF_PAGE)
        self.assertEqual(page.page_num, 1)


class TestProcessPageBackward(unittest.TestCase):
    """Tests corresponding to PROCESS-PF7-KEY."""

    def test_page_backward_from_page_2(self):
        repo = _make_repo(25)
        page = process_page_backward(repo, "USER0011", 2)

        self.assertTrue(len(page.rows) > 0)

    def test_page_backward_at_top(self):
        """When on page 1, display top-of-page message."""
        repo = _make_repo(25)
        page = process_page_backward(repo, "USER0001", 1)

        self.assertEqual(page.message, MSG_TOP_OF_PAGE)
        self.assertEqual(page.page_num, 1)


# ===========================================================================
# 5. Initial page load
# ===========================================================================

class TestGetInitialPage(unittest.TestCase):
    """Tests for the initial page load."""

    def test_initial_page_with_data(self):
        repo = _make_repo(15)
        page = get_initial_page(repo)

        self.assertEqual(len(page.rows), PAGE_SIZE)
        self.assertEqual(page.page_num, 1)
        self.assertTrue(page.has_next_page)
        self.assertEqual(page.rows[0].user_id, "USER0001")

    def test_initial_page_empty_file(self):
        repo = _empty_repo()
        page = get_initial_page(repo)

        self.assertEqual(len(page.rows), 0)
        self.assertEqual(page.page_num, 0)
        self.assertFalse(page.has_next_page)

    def test_initial_page_exact_page_size(self):
        """Exactly 10 users → one full page, no next."""
        repo = _make_repo(10)
        page = get_initial_page(repo)

        self.assertEqual(len(page.rows), PAGE_SIZE)
        self.assertEqual(page.page_num, 1)
        self.assertFalse(page.has_next_page)


# ===========================================================================
# 6. Header info
# ===========================================================================

class TestGetHeaderInfo(unittest.TestCase):
    """Tests for the POPULATE-HEADER-INFO equivalent."""

    def test_header_contains_required_fields(self):
        info = get_header_info()

        self.assertIn("title01", info)
        self.assertIn("title02", info)
        self.assertIn("transaction_id", info)
        self.assertIn("program_name", info)
        self.assertIn("current_date", info)
        self.assertIn("current_time", info)
        self.assertEqual(info["program_name"], "COUSR00C")
        self.assertEqual(info["transaction_id"], "CU00")


# ===========================================================================
# 7. Edge cases
# ===========================================================================

class TestEdgeCases(unittest.TestCase):
    """Miscellaneous edge-case tests."""

    def test_single_user(self):
        """File with exactly one user."""
        repo = InMemoryUserSecurityRepository()
        repo.seed(UserSecurityRecord(
            user_id="ADMIN001",
            first_name="Admin",
            last_name="User",
            password="PASSWORD",
            user_type="A",
        ))
        page = get_initial_page(repo)

        self.assertEqual(len(page.rows), 1)
        self.assertEqual(page.page_num, 1)
        self.assertFalse(page.has_next_page)
        self.assertEqual(page.rows[0].user_id, "ADMIN001")

    def test_user_type_display(self):
        """Admin users should show type 'A', regular users type 'U'."""
        repo = _make_repo(10)
        page = get_initial_page(repo)

        # USER0005 is admin (i % 5 == 0), USER0001 is regular
        admin_row = next(r for r in page.rows if r.user_id == "USER0005")
        regular_row = next(r for r in page.rows if r.user_id == "USER0001")

        self.assertEqual(admin_row.user_type, "A")
        self.assertEqual(regular_row.user_type, "U")

    def test_selection_strips_whitespace(self):
        """Selection flag and user ID should be stripped."""
        result = process_user_selection(" U ", " USER0001 ")
        self.assertEqual(result.action, "update")
        self.assertEqual(result.selected_user_id, "USER0001")


if __name__ == "__main__":
    unittest.main()
