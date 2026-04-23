"""
Unit tests for cosgn00c.py — the Python translation of COSGN00C.CBL.

These tests verify the same business rules that the original COBOL program
enforces for the sign-on (login) screen.
"""

import unittest

from cosgn00c import (
    CommArea,
    InMemoryUserSecurityRepository,
    SignonInput,
    SignonResult,
    UserSecurityRecord,
    authenticate_user,
    get_header_info,
    process_signon,
    validate_signon_input,
    MSG_INVALID_KEY,
    MSG_THANK_YOU,
    PROGRAM_NAME,
    TRANSACTION_ID,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_repo() -> InMemoryUserSecurityRepository:
    """Return a repo pre-loaded with an admin and a regular user."""
    repo = InMemoryUserSecurityRepository()
    repo.add_user(
        UserSecurityRecord(
            sec_usr_id="ADMIN001",
            sec_usr_fname="ADMIN",
            sec_usr_lname="USER",
            sec_usr_pwd="PASSWORD",
            sec_usr_type="A",
        )
    )
    repo.add_user(
        UserSecurityRecord(
            sec_usr_id="USER0001",
            sec_usr_fname="REGULAR",
            sec_usr_lname="USER",
            sec_usr_pwd="PASSWORD",
            sec_usr_type="U",
        )
    )
    return repo


# ===========================================================================
# 1. Input validation
# ===========================================================================

class TestValidateSignonInput(unittest.TestCase):
    """Tests corresponding to the input validation in PROCESS-ENTER-KEY."""

    def test_valid_input(self):
        """Both user ID and password provided should pass validation."""
        inp = SignonInput(user_id="ADMIN001", password="PASSWORD")
        result = validate_signon_input(inp)
        self.assertTrue(result.success)

    def test_empty_user_id(self):
        """Empty user ID returns 'Please enter User ID ...'"""
        inp = SignonInput(user_id="", password="PASSWORD")
        result = validate_signon_input(inp)
        self.assertFalse(result.success)
        self.assertIn("Please enter User ID", result.error_message)
        self.assertEqual(result.error_field, "user_id")

    def test_spaces_user_id(self):
        """Spaces-only user ID treated as empty."""
        inp = SignonInput(user_id="   ", password="PASSWORD")
        result = validate_signon_input(inp)
        self.assertFalse(result.success)
        self.assertIn("Please enter User ID", result.error_message)

    def test_empty_password(self):
        """Empty password returns 'Please enter Password ...'"""
        inp = SignonInput(user_id="ADMIN001", password="")
        result = validate_signon_input(inp)
        self.assertFalse(result.success)
        self.assertIn("Please enter Password", result.error_message)
        self.assertEqual(result.error_field, "password")

    def test_spaces_password(self):
        """Spaces-only password treated as empty."""
        inp = SignonInput(user_id="ADMIN001", password="   ")
        result = validate_signon_input(inp)
        self.assertFalse(result.success)
        self.assertIn("Please enter Password", result.error_message)

    def test_both_empty(self):
        """Both empty → user ID error is returned first."""
        inp = SignonInput(user_id="", password="")
        result = validate_signon_input(inp)
        self.assertFalse(result.success)
        self.assertIn("Please enter User ID", result.error_message)

    def test_input_uppercased(self):
        """Both user ID and password should be uppercased after validation."""
        inp = SignonInput(user_id="admin001", password="password")
        result = validate_signon_input(inp)
        self.assertTrue(result.success)
        self.assertEqual(inp.user_id, "ADMIN001")
        self.assertEqual(inp.password, "PASSWORD")


# ===========================================================================
# 2. User authentication
# ===========================================================================

class TestAuthenticateUser(unittest.TestCase):
    """Tests corresponding to READ-USER-SEC-FILE paragraph."""

    def test_user_not_found(self):
        """Unknown user ID returns 'User not found. Try again ...'"""
        repo = _make_repo()
        inp = SignonInput(user_id="UNKNOWN1", password="PASSWORD")
        result = authenticate_user(inp, repo)
        self.assertFalse(result.success)
        self.assertIn("User not found", result.error_message)
        self.assertEqual(result.error_field, "user_id")

    def test_wrong_password(self):
        """Correct user but wrong password returns 'Wrong Password. Try again ...'"""
        repo = _make_repo()
        inp = SignonInput(user_id="ADMIN001", password="WRONGPWD")
        result = authenticate_user(inp, repo)
        self.assertFalse(result.success)
        self.assertIn("Wrong Password", result.error_message)
        self.assertEqual(result.error_field, "password")

    def test_admin_login_routes_to_admin_menu(self):
        """Admin user (type 'A') should route to COADM01C."""
        repo = _make_repo()
        inp = SignonInput(user_id="ADMIN001", password="PASSWORD")
        result = authenticate_user(inp, repo)
        self.assertTrue(result.success)
        self.assertEqual(result.target_program, "COADM01C")

    def test_regular_user_routes_to_user_menu(self):
        """Regular user (type 'U') should route to COMEN01C."""
        repo = _make_repo()
        inp = SignonInput(user_id="USER0001", password="PASSWORD")
        result = authenticate_user(inp, repo)
        self.assertTrue(result.success)
        self.assertEqual(result.target_program, "COMEN01C")

    def test_commarea_populated_on_success(self):
        """Successful login should populate COMMAREA correctly."""
        repo = _make_repo()
        inp = SignonInput(user_id="ADMIN001", password="PASSWORD")
        result = authenticate_user(inp, repo)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.commarea)
        self.assertEqual(result.commarea.cdemo_from_tranid, "CC00")
        self.assertEqual(result.commarea.cdemo_from_program, "COSGN00C")
        self.assertEqual(result.commarea.cdemo_user_id, "ADMIN001")
        self.assertEqual(result.commarea.cdemo_user_type, "A")
        self.assertEqual(result.commarea.cdemo_pgm_context, 0)

    def test_commarea_for_regular_user(self):
        """COMMAREA user type should be 'U' for regular user."""
        repo = _make_repo()
        inp = SignonInput(user_id="USER0001", password="PASSWORD")
        result = authenticate_user(inp, repo)
        self.assertTrue(result.success)
        self.assertEqual(result.commarea.cdemo_user_type, "U")

    def test_no_commarea_on_failure(self):
        """Failed login should not populate COMMAREA."""
        repo = _make_repo()
        inp = SignonInput(user_id="UNKNOWN1", password="PASSWORD")
        result = authenticate_user(inp, repo)
        self.assertFalse(result.success)
        self.assertIsNone(result.commarea)


# ===========================================================================
# 3. Full sign-on workflow
# ===========================================================================

class TestProcessSignon(unittest.TestCase):
    """End-to-end tests for process_signon (PROCESS-ENTER-KEY)."""

    def test_successful_admin_login(self):
        """Happy path: admin user logs in successfully."""
        repo = _make_repo()
        inp = SignonInput(user_id="admin001", password="password")
        result = process_signon(inp, repo)
        self.assertTrue(result.success)
        self.assertEqual(result.target_program, "COADM01C")
        self.assertEqual(result.commarea.cdemo_user_id, "ADMIN001")

    def test_successful_regular_login(self):
        """Happy path: regular user logs in successfully."""
        repo = _make_repo()
        inp = SignonInput(user_id="user0001", password="password")
        result = process_signon(inp, repo)
        self.assertTrue(result.success)
        self.assertEqual(result.target_program, "COMEN01C")

    def test_empty_user_id_stops_before_auth(self):
        """Empty user ID fails at validation, not authentication."""
        repo = _make_repo()
        inp = SignonInput(user_id="", password="password")
        result = process_signon(inp, repo)
        self.assertFalse(result.success)
        self.assertIn("Please enter User ID", result.error_message)

    def test_empty_password_stops_before_auth(self):
        """Empty password fails at validation, not authentication."""
        repo = _make_repo()
        inp = SignonInput(user_id="admin001", password="")
        result = process_signon(inp, repo)
        self.assertFalse(result.success)
        self.assertIn("Please enter Password", result.error_message)

    def test_wrong_password_after_validation(self):
        """Valid input but wrong password fails at authentication."""
        repo = _make_repo()
        inp = SignonInput(user_id="admin001", password="WRONGPWD")
        result = process_signon(inp, repo)
        self.assertFalse(result.success)
        self.assertIn("Wrong Password", result.error_message)

    def test_user_not_found_after_validation(self):
        """Valid input but unknown user fails at authentication."""
        repo = _make_repo()
        inp = SignonInput(user_id="NOBODY99", password="PASSWORD")
        result = process_signon(inp, repo)
        self.assertFalse(result.success)
        self.assertIn("User not found", result.error_message)

    def test_case_insensitive_credentials(self):
        """Lowercase input should be uppercased and match."""
        repo = _make_repo()
        inp = SignonInput(user_id="Admin001", password="Password")
        result = process_signon(inp, repo)
        self.assertTrue(result.success)

    def test_password_comparison_is_exact(self):
        """Password must match exactly after uppercasing."""
        repo = _make_repo()
        inp = SignonInput(user_id="admin001", password="PASSWOR")
        result = process_signon(inp, repo)
        self.assertFalse(result.success)
        self.assertIn("Wrong Password", result.error_message)


# ===========================================================================
# 4. Constants and header helpers
# ===========================================================================

class TestConstantsAndHelpers(unittest.TestCase):
    """Tests for constants and screen helper functions."""

    def test_program_name_constant(self):
        self.assertEqual(PROGRAM_NAME, "COSGN00C")

    def test_transaction_id_constant(self):
        self.assertEqual(TRANSACTION_ID, "CC00")

    def test_thank_you_message(self):
        self.assertIn("Thank you", MSG_THANK_YOU)

    def test_invalid_key_message(self):
        self.assertIn("Invalid key", MSG_INVALID_KEY)

    def test_header_info_contains_required_fields(self):
        """get_header_info() should return program name, tran ID, and date/time."""
        info = get_header_info()
        self.assertEqual(info["program_name"], "COSGN00C")
        self.assertEqual(info["transaction_id"], "CC00")
        self.assertIn("title01", info)
        self.assertIn("title02", info)
        self.assertIn("current_date", info)
        self.assertIn("current_time", info)

    def test_header_date_format(self):
        """Date should be in MM/DD/YY format."""
        info = get_header_info()
        parts = info["current_date"].split("/")
        self.assertEqual(len(parts), 3)
        self.assertEqual(len(parts[2]), 2)  # YY not YYYY

    def test_header_time_format(self):
        """Time should be in HH:MM:SS format."""
        info = get_header_info()
        parts = info["current_time"].split(":")
        self.assertEqual(len(parts), 3)


# ===========================================================================
# 5. Edge cases
# ===========================================================================

class TestEdgeCases(unittest.TestCase):
    """Additional edge-case tests."""

    def test_user_id_with_leading_trailing_spaces(self):
        """Leading/trailing spaces should be stripped."""
        repo = _make_repo()
        inp = SignonInput(user_id="  ADMIN001  ", password="PASSWORD")
        result = process_signon(inp, repo)
        self.assertTrue(result.success)

    def test_password_with_leading_trailing_spaces(self):
        """Leading/trailing spaces on password should be stripped."""
        repo = _make_repo()
        inp = SignonInput(user_id="ADMIN001", password="  PASSWORD  ")
        result = process_signon(inp, repo)
        self.assertTrue(result.success)

    def test_empty_repo_returns_not_found(self):
        """Empty user security file should return not found."""
        repo = InMemoryUserSecurityRepository()
        inp = SignonInput(user_id="ADMIN001", password="PASSWORD")
        result = process_signon(inp, repo)
        self.assertFalse(result.success)
        self.assertIn("User not found", result.error_message)

    def test_signon_result_defaults(self):
        """Default SignonResult should indicate failure."""
        result = SignonResult()
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "")
        self.assertEqual(result.target_program, "")
        self.assertIsNone(result.commarea)

    def test_commarea_defaults(self):
        """Default CommArea should have empty strings and zero context."""
        ca = CommArea()
        self.assertEqual(ca.cdemo_from_tranid, "")
        self.assertEqual(ca.cdemo_pgm_context, 0)


if __name__ == "__main__":
    unittest.main()
