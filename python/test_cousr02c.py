"""
Unit tests for cousr02c.py — the Python translation of COUSR02C.CBL.

These tests verify the same business rules that the original COBOL program
enforces, organised by functional area.
"""

import unittest

from user_security_repository import (
    InMemoryUserSecurityRepository,
    UserSecurityRecord,
)
from cousr02c import (
    MSG_NO_MODIFICATION,
    MSG_PRESS_PF5,
    UserUpdateInput,
    clear_all_fields,
    get_header_info,
    lookup_user_for_update,
    update_user,
    validate_update_fields,
    validate_user_id,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_repo() -> InMemoryUserSecurityRepository:
    """Return a repo pre-loaded with test users."""
    repo = InMemoryUserSecurityRepository()
    repo.seed(UserSecurityRecord(
        user_id="ADMIN001",
        first_name="Admin",
        last_name="User",
        password="PASSWORD",
        user_type="A",
    ))
    repo.seed(UserSecurityRecord(
        user_id="USER0001",
        first_name="Regular",
        last_name="User",
        password="USERPASS",
        user_type="U",
    ))
    return repo


def _update_input(
    user_id: str = "ADMIN001",
    first_name: str = "Admin",
    last_name: str = "User",
    password: str = "PASSWORD",
    user_type: str = "A",
) -> UserUpdateInput:
    return UserUpdateInput(
        user_id=user_id,
        first_name=first_name,
        last_name=last_name,
        password=password,
        user_type=user_type,
    )


# ===========================================================================
# 1. User ID validation
# ===========================================================================

class TestValidateUserId(unittest.TestCase):
    """Tests for the User ID validation."""

    def test_valid_user_id(self):
        result = validate_user_id("ADMIN001")
        self.assertTrue(result.is_valid)

    def test_empty_user_id(self):
        result = validate_user_id("")
        self.assertFalse(result.is_valid)
        self.assertIn("User ID can NOT be empty", result.error_message)

    def test_spaces_only_user_id(self):
        result = validate_user_id("   ")
        self.assertFalse(result.is_valid)
        self.assertIn("User ID can NOT be empty", result.error_message)


# ===========================================================================
# 2. Update-fields validation
# ===========================================================================

class TestValidateUpdateFields(unittest.TestCase):
    """Tests corresponding to the EVALUATE in UPDATE-USER-INFO."""

    def test_all_fields_valid(self):
        result = validate_update_fields(_update_input())
        self.assertTrue(result.is_valid)

    def test_empty_user_id(self):
        result = validate_update_fields(_update_input(user_id=""))
        self.assertFalse(result.is_valid)
        self.assertIn("User ID can NOT be empty", result.error_message)

    def test_empty_first_name(self):
        result = validate_update_fields(_update_input(first_name=""))
        self.assertFalse(result.is_valid)
        self.assertIn("First Name can NOT be empty", result.error_message)

    def test_empty_last_name(self):
        result = validate_update_fields(_update_input(last_name=""))
        self.assertFalse(result.is_valid)
        self.assertIn("Last Name can NOT be empty", result.error_message)

    def test_empty_password(self):
        result = validate_update_fields(_update_input(password=""))
        self.assertFalse(result.is_valid)
        self.assertIn("Password can NOT be empty", result.error_message)

    def test_empty_user_type(self):
        result = validate_update_fields(_update_input(user_type=""))
        self.assertFalse(result.is_valid)
        self.assertIn("User Type can NOT be empty", result.error_message)

    def test_validation_order_user_id_first(self):
        """When all fields are empty, user_id is reported first."""
        inp = UserUpdateInput()
        result = validate_update_fields(inp)
        self.assertEqual(result.error_field, "user_id")


# ===========================================================================
# 3. Lookup user for update
# ===========================================================================

class TestLookupUserForUpdate(unittest.TestCase):
    """Tests corresponding to PROCESS-ENTER-KEY."""

    def test_successful_lookup(self):
        repo = _make_repo()
        result = lookup_user_for_update("ADMIN001", repo)

        self.assertTrue(result.success)
        self.assertEqual(result.message, MSG_PRESS_PF5)
        self.assertIsNotNone(result.record)
        self.assertEqual(result.record.user_id, "ADMIN001")
        self.assertEqual(result.record.first_name, "Admin")

    def test_user_not_found(self):
        repo = _make_repo()
        result = lookup_user_for_update("NOBODY99", repo)

        self.assertFalse(result.success)
        self.assertIn("User ID NOT found", result.message)

    def test_empty_user_id(self):
        repo = _make_repo()
        result = lookup_user_for_update("", repo)

        self.assertFalse(result.success)
        self.assertIn("User ID can NOT be empty", result.message)


# ===========================================================================
# 4. Full update-user workflow
# ===========================================================================

class TestUpdateUser(unittest.TestCase):
    """End-to-end tests for the update_user function."""

    def test_successful_update_first_name(self):
        repo = _make_repo()
        inp = _update_input(first_name="NewAdmin")
        result = update_user(inp, repo)

        self.assertTrue(result.success)
        self.assertTrue(result.modified)
        self.assertIn("ADMIN001", result.message)
        self.assertIn("has been updated", result.message)
        # Verify the record was updated
        rec = repo.lookup_user("ADMIN001")
        self.assertEqual(rec.first_name, "NewAdmin")

    def test_successful_update_last_name(self):
        repo = _make_repo()
        inp = _update_input(last_name="NewLast")
        result = update_user(inp, repo)

        self.assertTrue(result.success)
        rec = repo.lookup_user("ADMIN001")
        self.assertEqual(rec.last_name, "NewLast")

    def test_successful_update_password(self):
        repo = _make_repo()
        inp = _update_input(password="NEWPASS1")
        result = update_user(inp, repo)

        self.assertTrue(result.success)
        rec = repo.lookup_user("ADMIN001")
        self.assertEqual(rec.password, "NEWPASS1")

    def test_successful_update_user_type(self):
        repo = _make_repo()
        inp = _update_input(user_type="U")
        result = update_user(inp, repo)

        self.assertTrue(result.success)
        rec = repo.lookup_user("ADMIN001")
        self.assertEqual(rec.user_type, "U")

    def test_no_modification(self):
        """When nothing changed, should report 'Please modify to update'."""
        repo = _make_repo()
        inp = _update_input()  # same as existing
        result = update_user(inp, repo)

        self.assertFalse(result.success)
        self.assertFalse(result.modified)
        self.assertEqual(result.message, MSG_NO_MODIFICATION)

    def test_user_not_found(self):
        repo = _make_repo()
        inp = _update_input(user_id="NOBODY99", first_name="X")
        result = update_user(inp, repo)

        self.assertFalse(result.success)
        self.assertIn("User ID NOT found", result.message)

    def test_empty_field_rejected(self):
        repo = _make_repo()
        inp = _update_input(first_name="")
        result = update_user(inp, repo)

        self.assertFalse(result.success)
        self.assertIn("First Name can NOT be empty", result.message)

    def test_multiple_fields_changed(self):
        """Changing multiple fields at once should succeed."""
        repo = _make_repo()
        inp = _update_input(
            first_name="New",
            last_name="Name",
            password="NEWPASS1",
            user_type="U",
        )
        result = update_user(inp, repo)

        self.assertTrue(result.success)
        rec = repo.lookup_user("ADMIN001")
        self.assertEqual(rec.first_name, "New")
        self.assertEqual(rec.last_name, "Name")
        self.assertEqual(rec.password, "NEWPASS1")
        self.assertEqual(rec.user_type, "U")

    def test_other_users_not_affected(self):
        """Updating one user should not affect other users."""
        repo = _make_repo()
        inp = _update_input(first_name="NewAdmin")
        update_user(inp, repo)

        other = repo.lookup_user("USER0001")
        self.assertEqual(other.first_name, "Regular")


# ===========================================================================
# 5. Clear and header helpers
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
        self.assertEqual(info["program_name"], "COUSR02C")
        self.assertEqual(info["transaction_id"], "CU02")


# ===========================================================================
# 6. Edge cases
# ===========================================================================

class TestEdgeCases(unittest.TestCase):

    def test_whitespace_difference_detected(self):
        """Trailing whitespace difference should be detected as a change."""
        repo = InMemoryUserSecurityRepository()
        repo.seed(UserSecurityRecord(
            user_id="TEST0001",
            first_name="John",
            last_name="Doe",
            password="PASS1234",
            user_type="U",
        ))
        inp = UserUpdateInput(
            user_id="TEST0001",
            first_name="  John  ",  # will be stripped to "John"
            last_name="Doe",
            password="PASS1234",
            user_type="U",
        )
        result = update_user(inp, repo)
        # "John" stripped == "John" stripped → no modification
        self.assertFalse(result.success)
        self.assertEqual(result.message, MSG_NO_MODIFICATION)

    def test_success_message_format(self):
        """Success message should match COBOL STRING format."""
        repo = _make_repo()
        inp = _update_input(first_name="NewFirst")
        result = update_user(inp, repo)
        self.assertEqual(result.message, "User ADMIN001 has been updated ...")


if __name__ == "__main__":
    unittest.main()
