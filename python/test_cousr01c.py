"""
Unit tests for cousr01c.py — the Python translation of COUSR01C.CBL.

These tests verify the same business rules that the original COBOL program
enforces, organised by functional area.
"""

import unittest

from user_security_repository import (
    InMemoryUserSecurityRepository,
    UserSecurityRecord,
)
from cousr01c import (
    UserAddInput,
    add_user,
    clear_all_fields,
    get_header_info,
    validate_user_input,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_repo() -> InMemoryUserSecurityRepository:
    """Return a repo pre-loaded with one existing user."""
    repo = InMemoryUserSecurityRepository()
    repo.seed(UserSecurityRecord(
        user_id="ADMIN001",
        first_name="Admin",
        last_name="User",
        password="PASSWORD",
        user_type="A",
    ))
    return repo


def _valid_input() -> UserAddInput:
    """Return a fully valid UserAddInput ready to be added."""
    return UserAddInput(
        user_id="NEWUSR01",
        first_name="John",
        last_name="Doe",
        password="PASS1234",
        user_type="U",
    )


# ===========================================================================
# 1. Input validation
# ===========================================================================

class TestValidateUserInput(unittest.TestCase):
    """Tests corresponding to the EVALUATE in PROCESS-ENTER-KEY."""

    def test_all_fields_valid(self):
        result = validate_user_input(_valid_input())
        self.assertTrue(result.is_valid)

    def test_empty_first_name(self):
        inp = _valid_input()
        inp.first_name = ""
        result = validate_user_input(inp)
        self.assertFalse(result.is_valid)
        self.assertIn("First Name can NOT be empty", result.error_message)
        self.assertEqual(result.error_field, "first_name")

    def test_empty_last_name(self):
        inp = _valid_input()
        inp.last_name = ""
        result = validate_user_input(inp)
        self.assertFalse(result.is_valid)
        self.assertIn("Last Name can NOT be empty", result.error_message)
        self.assertEqual(result.error_field, "last_name")

    def test_empty_user_id(self):
        inp = _valid_input()
        inp.user_id = ""
        result = validate_user_input(inp)
        self.assertFalse(result.is_valid)
        self.assertIn("User ID can NOT be empty", result.error_message)
        self.assertEqual(result.error_field, "user_id")

    def test_empty_password(self):
        inp = _valid_input()
        inp.password = ""
        result = validate_user_input(inp)
        self.assertFalse(result.is_valid)
        self.assertIn("Password can NOT be empty", result.error_message)
        self.assertEqual(result.error_field, "password")

    def test_empty_user_type(self):
        inp = _valid_input()
        inp.user_type = ""
        result = validate_user_input(inp)
        self.assertFalse(result.is_valid)
        self.assertIn("User Type can NOT be empty", result.error_message)
        self.assertEqual(result.error_field, "user_type")

    def test_spaces_only_first_name(self):
        inp = _valid_input()
        inp.first_name = "   "
        result = validate_user_input(inp)
        self.assertFalse(result.is_valid)
        self.assertIn("First Name can NOT be empty", result.error_message)

    def test_validation_stops_at_first_error(self):
        """When multiple fields are empty, the first one (in COBOL order) is reported."""
        inp = UserAddInput()  # all empty
        result = validate_user_input(inp)
        self.assertFalse(result.is_valid)
        self.assertIn("First Name can NOT be empty", result.error_message)
        self.assertEqual(result.error_field, "first_name")


# ===========================================================================
# 2. Full add-user workflow
# ===========================================================================

class TestAddUser(unittest.TestCase):
    """End-to-end tests for the add_user function."""

    def test_successful_add(self):
        """Happy path: valid input writes the record."""
        repo = _make_repo()
        inp = _valid_input()
        result = add_user(inp, repo)

        self.assertTrue(result.success)
        self.assertIn("NEWUSR01", result.message)
        self.assertIn("has been added", result.message)
        # Verify record was persisted
        self.assertIsNotNone(repo.lookup_user("NEWUSR01"))

    def test_duplicate_user_id(self):
        """Attempting to add an existing user ID returns error."""
        repo = _make_repo()
        inp = _valid_input()
        inp.user_id = "ADMIN001"  # already exists
        result = add_user(inp, repo)

        self.assertFalse(result.success)
        self.assertIn("User ID already exist", result.message)

    def test_rejected_empty_field(self):
        """Validation error prevents write."""
        repo = _make_repo()
        inp = _valid_input()
        inp.first_name = ""
        result = add_user(inp, repo)

        self.assertFalse(result.success)
        self.assertIn("First Name can NOT be empty", result.message)
        # No new user should be created
        self.assertIsNone(repo.lookup_user("NEWUSR01"))

    def test_record_fields_are_correct(self):
        """Verify that all fields are stored correctly."""
        repo = _make_repo()
        inp = _valid_input()
        add_user(inp, repo)

        rec = repo.lookup_user("NEWUSR01")
        self.assertIsNotNone(rec)
        self.assertEqual(rec.user_id, "NEWUSR01")
        self.assertEqual(rec.first_name, "John")
        self.assertEqual(rec.last_name, "Doe")
        self.assertEqual(rec.password, "PASS1234")
        self.assertEqual(rec.user_type, "U")

    def test_add_admin_user(self):
        """Adding a user with type 'A' should succeed."""
        repo = _make_repo()
        inp = _valid_input()
        inp.user_type = "A"
        result = add_user(inp, repo)

        self.assertTrue(result.success)
        rec = repo.lookup_user("NEWUSR01")
        self.assertEqual(rec.user_type, "A")

    def test_multiple_adds(self):
        """Adding multiple users sequentially should succeed."""
        repo = _make_repo()
        for i in range(1, 6):
            inp = _valid_input()
            inp.user_id = f"NEW{i:05d}"
            inp.first_name = f"User{i}"
            result = add_user(inp, repo)
            self.assertTrue(result.success)

        self.assertEqual(len(repo.list_users()), 6)  # 1 original + 5 new


# ===========================================================================
# 3. Clear and header helpers
# ===========================================================================

class TestClearAndHeaderHelpers(unittest.TestCase):

    def test_clear_all_fields_returns_blank_input(self):
        blank = clear_all_fields()
        self.assertEqual(blank.user_id, "")
        self.assertEqual(blank.first_name, "")
        self.assertEqual(blank.last_name, "")
        self.assertEqual(blank.password, "")
        self.assertEqual(blank.user_type, "")

    def test_header_info_contains_required_fields(self):
        info = get_header_info()
        self.assertIn("title01", info)
        self.assertIn("title02", info)
        self.assertIn("transaction_id", info)
        self.assertIn("program_name", info)
        self.assertIn("current_date", info)
        self.assertIn("current_time", info)
        self.assertEqual(info["program_name"], "COUSR01C")
        self.assertEqual(info["transaction_id"], "CU01")


# ===========================================================================
# 4. Edge cases
# ===========================================================================

class TestEdgeCases(unittest.TestCase):

    def test_whitespace_trimmed_in_record(self):
        """Leading/trailing whitespace should be trimmed in the stored record."""
        repo = _make_repo()
        inp = _valid_input()
        inp.first_name = "  John  "
        inp.last_name = "  Doe  "
        add_user(inp, repo)

        rec = repo.lookup_user("NEWUSR01")
        self.assertEqual(rec.first_name, "John")
        self.assertEqual(rec.last_name, "Doe")

    def test_add_to_empty_repo(self):
        """Adding the first user to an empty repository should succeed."""
        repo = InMemoryUserSecurityRepository()
        inp = _valid_input()
        result = add_user(inp, repo)

        self.assertTrue(result.success)
        self.assertEqual(len(repo.list_users()), 1)

    def test_user_id_case_sensitive(self):
        """User IDs are case-sensitive (COBOL stores as-is)."""
        repo = _make_repo()
        inp = _valid_input()
        inp.user_id = "admin001"  # lowercase — different from ADMIN001
        result = add_user(inp, repo)
        self.assertTrue(result.success)

    def test_success_message_format(self):
        """Success message should match COBOL STRING format."""
        repo = _make_repo()
        inp = _valid_input()
        result = add_user(inp, repo)
        self.assertEqual(result.message, "User NEWUSR01 has been added ...")


if __name__ == "__main__":
    unittest.main()
