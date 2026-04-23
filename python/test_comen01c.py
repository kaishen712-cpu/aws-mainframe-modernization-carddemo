"""
Unit tests for comen01c.py — the Python translation of COMEN01C.CBL.

These tests verify the same business rules that the original COBOL program
enforces for the regular-user main menu.
"""

import unittest

from comen01c import (
    CommArea,
    ConfigurableProgramChecker,
    MenuOption,
    MENU_OPT_COUNT,
    MENU_OPTIONS,
    PROGRAM_NAME,
    SIGNON_PROGRAM,
    TRANSACTION_ID,
    build_commarea_for_transfer,
    build_menu_display,
    get_header_info,
    process_menu_selection,
    validate_menu_option,
)


# ===========================================================================
# 1. Menu option data integrity
# ===========================================================================

class TestMenuOptionsData(unittest.TestCase):
    """Verify the menu options match COMEN02Y copybook definitions."""

    def test_option_count_is_11(self):
        """CDEMO-MENU-OPT-COUNT is 11 in the copybook."""
        self.assertEqual(MENU_OPT_COUNT, 11)

    def test_option_numbers_are_sequential(self):
        """Option numbers should be 1 through 11."""
        for i, opt in enumerate(MENU_OPTIONS, start=1):
            self.assertEqual(opt.opt_num, i)

    def test_option_1_account_view(self):
        self.assertEqual(MENU_OPTIONS[0].opt_name, "Account View")
        self.assertEqual(MENU_OPTIONS[0].opt_pgmname, "COACTVWC")
        self.assertEqual(MENU_OPTIONS[0].opt_usrtype, "U")

    def test_option_8_transaction_add(self):
        self.assertEqual(MENU_OPTIONS[7].opt_name, "Transaction Add")
        self.assertEqual(MENU_OPTIONS[7].opt_pgmname, "COTRN02C")

    def test_option_11_pending_auth_view(self):
        self.assertEqual(MENU_OPTIONS[10].opt_name, "Pending Authorization View")
        self.assertEqual(MENU_OPTIONS[10].opt_pgmname, "COPAUS0C")

    def test_all_options_have_user_type(self):
        """All 11 options in COMEN02Y have user type 'U'."""
        for opt in MENU_OPTIONS:
            self.assertEqual(opt.opt_usrtype, "U")


# ===========================================================================
# 2. Option validation
# ===========================================================================

class TestValidateMenuOption(unittest.TestCase):
    """Tests corresponding to PROCESS-ENTER-KEY validation logic."""

    def test_valid_option_1(self):
        result = validate_menu_option("1", "U")
        self.assertTrue(result.success)
        self.assertEqual(result.target_program, "COACTVWC")

    def test_valid_option_11(self):
        result = validate_menu_option("11", "U")
        self.assertTrue(result.success)
        self.assertEqual(result.target_program, "COPAUS0C")

    def test_valid_option_with_leading_space(self):
        """Input '  1' should be treated as option 1."""
        result = validate_menu_option("  1", "U")
        self.assertTrue(result.success)
        self.assertEqual(result.target_program, "COACTVWC")

    def test_valid_option_with_zero_padding(self):
        """Input '01' should be treated as option 1."""
        result = validate_menu_option("01", "U")
        self.assertTrue(result.success)

    def test_empty_input_returns_error(self):
        """Empty string is invalid."""
        result = validate_menu_option("", "U")
        self.assertFalse(result.success)
        self.assertIn("valid option number", result.error_message)

    def test_zero_returns_error(self):
        """Option 0 is out of range."""
        result = validate_menu_option("0", "U")
        self.assertFalse(result.success)
        self.assertIn("valid option number", result.error_message)

    def test_exceeds_max_returns_error(self):
        """Option 12 exceeds the 11-option count."""
        result = validate_menu_option("12", "U")
        self.assertFalse(result.success)
        self.assertIn("valid option number", result.error_message)

    def test_non_numeric_returns_error(self):
        """Letters are not a valid option."""
        result = validate_menu_option("AB", "U")
        self.assertFalse(result.success)
        self.assertIn("valid option number", result.error_message)

    def test_special_characters_return_error(self):
        """Special characters are not valid."""
        result = validate_menu_option("@!", "U")
        self.assertFalse(result.success)

    def test_admin_only_option_denied_for_regular_user(self):
        """A regular user selecting an admin-only option gets denied."""
        # Create a custom menu with one admin-only option
        custom_options = [
            MenuOption(1, "Admin Function", "COADM99C", "A"),
            MenuOption(2, "User Function", "COUSR99C", "U"),
        ]
        result = validate_menu_option("1", "U", menu_options=custom_options)
        self.assertFalse(result.success)
        self.assertIn("No access - Admin Only", result.error_message)

    def test_admin_user_can_access_admin_option(self):
        """An admin user can access admin-only options."""
        custom_options = [
            MenuOption(1, "Admin Function", "COADM99C", "A"),
        ]
        result = validate_menu_option("1", "A", menu_options=custom_options)
        self.assertTrue(result.success)

    def test_negative_number_returns_error(self):
        """Negative numbers are not valid (non-numeric after padding)."""
        result = validate_menu_option("-1", "U")
        self.assertFalse(result.success)


# ===========================================================================
# 3. Full menu selection with special program handling
# ===========================================================================

class TestProcessMenuSelection(unittest.TestCase):
    """End-to-end tests for process_menu_selection."""

    def test_normal_program_routes_successfully(self):
        """Selecting option 1 (COACTVWC) routes directly."""
        result = process_menu_selection("1", "U")
        self.assertTrue(result.success)
        self.assertEqual(result.target_program, "COACTVWC")

    def test_copaus0c_installed_routes_successfully(self):
        """COPAUS0C routes if program is installed."""
        checker = ConfigurableProgramChecker(installed_programs={"COPAUS0C"})
        result = process_menu_selection("11", "U", program_checker=checker)
        self.assertTrue(result.success)
        self.assertEqual(result.target_program, "COPAUS0C")

    def test_copaus0c_not_installed_returns_error(self):
        """COPAUS0C not installed returns 'not installed' error."""
        checker = ConfigurableProgramChecker(installed_programs=set())
        result = process_menu_selection("11", "U", program_checker=checker)
        self.assertFalse(result.success)
        self.assertTrue(result.is_not_installed)
        self.assertIn("not installed", result.error_message)

    def test_dummy_program_returns_coming_soon(self):
        """DUMMY* program returns 'coming soon' message."""
        custom_options = [
            MenuOption(1, "Future Feature", "DUMMY01C", "U"),
        ]
        result = process_menu_selection("1", "U", menu_options=custom_options)
        self.assertFalse(result.success)
        self.assertTrue(result.is_coming_soon)
        self.assertIn("coming soon", result.error_message)

    def test_invalid_option_fails_before_program_check(self):
        """Invalid option number fails at validation, not program check."""
        result = process_menu_selection("99", "U")
        self.assertFalse(result.success)
        self.assertIn("valid option number", result.error_message)

    def test_all_installed_checker_default(self):
        """Default checker assumes all programs are installed."""
        # Option 11 is COPAUS0C; with default checker it should work
        result = process_menu_selection("11", "U")
        self.assertTrue(result.success)
        self.assertEqual(result.target_program, "COPAUS0C")

    def test_each_option_routes_to_correct_program(self):
        """Each of the 11 options should route to the expected program."""
        expected = [
            ("1", "COACTVWC"), ("2", "COACTUPC"), ("3", "COCRDLIC"),
            ("4", "COCRDSLC"), ("5", "COCRDUPC"), ("6", "COTRN00C"),
            ("7", "COTRN01C"), ("8", "COTRN02C"), ("9", "CORPT00C"),
            ("10", "COBIL00C"), ("11", "COPAUS0C"),
        ]
        for opt_str, pgm in expected:
            with self.subTest(option=opt_str):
                result = process_menu_selection(opt_str, "U")
                self.assertTrue(result.success)
                self.assertEqual(result.target_program, pgm)


# ===========================================================================
# 4. COMMAREA building
# ===========================================================================

class TestBuildCommareaForTransfer(unittest.TestCase):
    """Tests for build_commarea_for_transfer."""

    def test_sets_from_tranid(self):
        ca = CommArea(cdemo_user_id="USER0001", cdemo_user_type="U")
        build_commarea_for_transfer(ca)
        self.assertEqual(ca.cdemo_from_tranid, "CM00")

    def test_sets_from_program(self):
        ca = CommArea()
        build_commarea_for_transfer(ca)
        self.assertEqual(ca.cdemo_from_program, "COMEN01C")

    def test_sets_pgm_context_to_zero(self):
        ca = CommArea(cdemo_pgm_context=1)
        build_commarea_for_transfer(ca)
        self.assertEqual(ca.cdemo_pgm_context, 0)

    def test_preserves_user_info(self):
        ca = CommArea(cdemo_user_id="USER0001", cdemo_user_type="U")
        build_commarea_for_transfer(ca)
        self.assertEqual(ca.cdemo_user_id, "USER0001")
        self.assertEqual(ca.cdemo_user_type, "U")


# ===========================================================================
# 5. Menu display builder
# ===========================================================================

class TestBuildMenuDisplay(unittest.TestCase):
    """Tests for build_menu_display (BUILD-MENU-OPTIONS paragraph)."""

    def test_returns_11_lines(self):
        lines = build_menu_display()
        self.assertEqual(len(lines), 11)

    def test_first_line_format(self):
        lines = build_menu_display()
        self.assertEqual(lines[0], "01. Account View")

    def test_last_line_format(self):
        lines = build_menu_display()
        self.assertEqual(lines[10], "11. Pending Authorization View")

    def test_option_8_format(self):
        lines = build_menu_display()
        self.assertEqual(lines[7], "08. Transaction Add")


# ===========================================================================
# 6. Constants and header helpers
# ===========================================================================

class TestConstantsAndHelpers(unittest.TestCase):
    """Tests for constants and screen helper functions."""

    def test_program_name(self):
        self.assertEqual(PROGRAM_NAME, "COMEN01C")

    def test_transaction_id(self):
        self.assertEqual(TRANSACTION_ID, "CM00")

    def test_signon_program(self):
        self.assertEqual(SIGNON_PROGRAM, "COSGN00C")

    def test_header_info_fields(self):
        info = get_header_info()
        self.assertEqual(info["program_name"], "COMEN01C")
        self.assertEqual(info["transaction_id"], "CM00")
        self.assertIn("title01", info)
        self.assertIn("current_date", info)
        self.assertIn("current_time", info)


if __name__ == "__main__":
    unittest.main()
