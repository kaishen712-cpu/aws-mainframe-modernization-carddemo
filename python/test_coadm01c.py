"""
Unit tests for coadm01c.py — the Python translation of COADM01C.CBL.

These tests verify the same business rules that the original COBOL program
enforces for the admin menu.
"""

import unittest

from coadm01c import (
    ADMIN_MENU_OPTIONS,
    ADMIN_OPT_COUNT,
    AdminMenuOption,
    AdminMenuSelectionResult,
    CommArea,
    MSG_INVALID_KEY,
    PROGRAM_NAME,
    SIGNON_PROGRAM,
    TRANSACTION_ID,
    build_admin_menu_display,
    build_commarea_for_transfer,
    get_header_info,
    process_admin_menu_selection,
    validate_admin_option,
)


# ===========================================================================
# 1. Admin menu option data integrity
# ===========================================================================

class TestAdminMenuOptionsData(unittest.TestCase):
    """Verify the admin menu options match COADM02Y copybook definitions."""

    def test_option_count_is_6(self):
        """CDEMO-ADMIN-OPT-COUNT is 6 in the copybook."""
        self.assertEqual(ADMIN_OPT_COUNT, 6)

    def test_option_numbers_are_sequential(self):
        """Option numbers should be 1 through 6."""
        for i, opt in enumerate(ADMIN_MENU_OPTIONS, start=1):
            self.assertEqual(opt.opt_num, i)

    def test_option_1_user_list(self):
        self.assertEqual(ADMIN_MENU_OPTIONS[0].opt_name, "User List (Security)")
        self.assertEqual(ADMIN_MENU_OPTIONS[0].opt_pgmname, "COUSR00C")

    def test_option_2_user_add(self):
        self.assertEqual(ADMIN_MENU_OPTIONS[1].opt_name, "User Add (Security)")
        self.assertEqual(ADMIN_MENU_OPTIONS[1].opt_pgmname, "COUSR01C")

    def test_option_3_user_update(self):
        self.assertEqual(ADMIN_MENU_OPTIONS[2].opt_name, "User Update (Security)")
        self.assertEqual(ADMIN_MENU_OPTIONS[2].opt_pgmname, "COUSR02C")

    def test_option_4_user_delete(self):
        self.assertEqual(ADMIN_MENU_OPTIONS[3].opt_name, "User Delete (Security)")
        self.assertEqual(ADMIN_MENU_OPTIONS[3].opt_pgmname, "COUSR03C")

    def test_option_5_tran_type_list(self):
        self.assertEqual(ADMIN_MENU_OPTIONS[4].opt_name,
                         "Transaction Type List/Update (Db2)")
        self.assertEqual(ADMIN_MENU_OPTIONS[4].opt_pgmname, "COTRTLIC")

    def test_option_6_tran_type_maint(self):
        self.assertEqual(ADMIN_MENU_OPTIONS[5].opt_name,
                         "Transaction Type Maintenance (Db2)")
        self.assertEqual(ADMIN_MENU_OPTIONS[5].opt_pgmname, "COTRTUPC")


# ===========================================================================
# 2. Option validation
# ===========================================================================

class TestValidateAdminOption(unittest.TestCase):
    """Tests corresponding to PROCESS-ENTER-KEY validation logic."""

    def test_valid_option_1(self):
        result = validate_admin_option("1")
        self.assertTrue(result.success)
        self.assertEqual(result.target_program, "COUSR00C")

    def test_valid_option_6(self):
        result = validate_admin_option("6")
        self.assertTrue(result.success)
        self.assertEqual(result.target_program, "COTRTUPC")

    def test_valid_option_with_leading_space(self):
        """Input '  1' should be treated as option 1."""
        result = validate_admin_option("  1")
        self.assertTrue(result.success)
        self.assertEqual(result.target_program, "COUSR00C")

    def test_valid_option_with_zero_padding(self):
        """Input '01' should be treated as option 1."""
        result = validate_admin_option("01")
        self.assertTrue(result.success)

    def test_empty_input_returns_error(self):
        """Empty string is invalid."""
        result = validate_admin_option("")
        self.assertFalse(result.success)
        self.assertIn("valid option number", result.error_message)

    def test_zero_returns_error(self):
        """Option 0 is out of range."""
        result = validate_admin_option("0")
        self.assertFalse(result.success)
        self.assertIn("valid option number", result.error_message)

    def test_exceeds_max_returns_error(self):
        """Option 7 exceeds the 6-option count."""
        result = validate_admin_option("7")
        self.assertFalse(result.success)
        self.assertIn("valid option number", result.error_message)

    def test_large_number_returns_error(self):
        """Option 99 exceeds the count."""
        result = validate_admin_option("99")
        self.assertFalse(result.success)

    def test_non_numeric_returns_error(self):
        """Letters are not a valid option."""
        result = validate_admin_option("AB")
        self.assertFalse(result.success)
        self.assertIn("valid option number", result.error_message)

    def test_special_characters_return_error(self):
        """Special characters are not valid."""
        result = validate_admin_option("#!")
        self.assertFalse(result.success)

    def test_negative_number_returns_error(self):
        """Negative numbers are not valid."""
        result = validate_admin_option("-1")
        self.assertFalse(result.success)


# ===========================================================================
# 3. Full admin menu selection with DUMMY handling
# ===========================================================================

class TestProcessAdminMenuSelection(unittest.TestCase):
    """End-to-end tests for process_admin_menu_selection."""

    def test_normal_program_routes_successfully(self):
        """Selecting option 1 (COUSR00C) routes directly."""
        result = process_admin_menu_selection("1")
        self.assertTrue(result.success)
        self.assertEqual(result.target_program, "COUSR00C")

    def test_dummy_program_returns_not_installed(self):
        """DUMMY* program returns 'not installed' message."""
        custom_options = [
            AdminMenuOption(1, "Placeholder Feature", "DUMMY01C"),
        ]
        result = process_admin_menu_selection("1", admin_options=custom_options)
        self.assertFalse(result.success)
        self.assertTrue(result.is_not_installed)
        self.assertIn("not installed", result.error_message)

    def test_invalid_option_fails_before_dummy_check(self):
        """Invalid option number fails at validation."""
        result = process_admin_menu_selection("99")
        self.assertFalse(result.success)
        self.assertIn("valid option number", result.error_message)

    def test_each_option_routes_to_correct_program(self):
        """Each of the 6 options should route to the expected program."""
        expected = [
            ("1", "COUSR00C"), ("2", "COUSR01C"), ("3", "COUSR02C"),
            ("4", "COUSR03C"), ("5", "COTRTLIC"), ("6", "COTRTUPC"),
        ]
        for opt_str, pgm in expected:
            with self.subTest(option=opt_str):
                result = process_admin_menu_selection(opt_str)
                self.assertTrue(result.success)
                self.assertEqual(result.target_program, pgm)

    def test_dummy_prefix_exactly_five_chars(self):
        """A program name like 'DUMMYXXX' should be caught as DUMMY."""
        custom_options = [
            AdminMenuOption(1, "Test", "DUMMYABC"),
        ]
        result = process_admin_menu_selection("1", admin_options=custom_options)
        self.assertFalse(result.success)
        self.assertTrue(result.is_not_installed)

    def test_non_dummy_prefix_not_caught(self):
        """A program name like 'DUMM01C' should NOT be treated as DUMMY."""
        custom_options = [
            AdminMenuOption(1, "Test", "DUMM01CC"),
        ]
        result = process_admin_menu_selection("1", admin_options=custom_options)
        self.assertTrue(result.success)
        self.assertEqual(result.target_program, "DUMM01CC")


# ===========================================================================
# 4. COMMAREA building
# ===========================================================================

class TestBuildCommareaForTransfer(unittest.TestCase):
    """Tests for build_commarea_for_transfer."""

    def test_sets_from_tranid(self):
        ca = CommArea(cdemo_user_id="ADMIN001", cdemo_user_type="A")
        build_commarea_for_transfer(ca)
        self.assertEqual(ca.cdemo_from_tranid, "CA00")

    def test_sets_from_program(self):
        ca = CommArea()
        build_commarea_for_transfer(ca)
        self.assertEqual(ca.cdemo_from_program, "COADM01C")

    def test_sets_pgm_context_to_zero(self):
        ca = CommArea(cdemo_pgm_context=1)
        build_commarea_for_transfer(ca)
        self.assertEqual(ca.cdemo_pgm_context, 0)

    def test_preserves_user_info(self):
        ca = CommArea(cdemo_user_id="ADMIN001", cdemo_user_type="A")
        build_commarea_for_transfer(ca)
        self.assertEqual(ca.cdemo_user_id, "ADMIN001")
        self.assertEqual(ca.cdemo_user_type, "A")


# ===========================================================================
# 5. Admin menu display builder
# ===========================================================================

class TestBuildAdminMenuDisplay(unittest.TestCase):
    """Tests for build_admin_menu_display (BUILD-MENU-OPTIONS paragraph)."""

    def test_returns_6_lines(self):
        lines = build_admin_menu_display()
        self.assertEqual(len(lines), 6)

    def test_first_line_format(self):
        lines = build_admin_menu_display()
        self.assertEqual(lines[0], "01. User List (Security)")

    def test_last_line_format(self):
        lines = build_admin_menu_display()
        self.assertEqual(lines[5], "06. Transaction Type Maintenance (Db2)")

    def test_option_4_format(self):
        lines = build_admin_menu_display()
        self.assertEqual(lines[3], "04. User Delete (Security)")


# ===========================================================================
# 6. Constants and header helpers
# ===========================================================================

class TestConstantsAndHelpers(unittest.TestCase):
    """Tests for constants and screen helper functions."""

    def test_program_name(self):
        self.assertEqual(PROGRAM_NAME, "COADM01C")

    def test_transaction_id(self):
        self.assertEqual(TRANSACTION_ID, "CA00")

    def test_signon_program(self):
        self.assertEqual(SIGNON_PROGRAM, "COSGN00C")

    def test_invalid_key_message(self):
        self.assertIn("Invalid key", MSG_INVALID_KEY)

    def test_header_info_fields(self):
        info = get_header_info()
        self.assertEqual(info["program_name"], "COADM01C")
        self.assertEqual(info["transaction_id"], "CA00")
        self.assertIn("title01", info)
        self.assertIn("current_date", info)
        self.assertIn("current_time", info)

    def test_header_date_format(self):
        """Date should be in MM/DD/YY format."""
        info = get_header_info()
        parts = info["current_date"].split("/")
        self.assertEqual(len(parts), 3)

    def test_header_time_format(self):
        """Time should be in HH:MM:SS format."""
        info = get_header_info()
        parts = info["current_time"].split(":")
        self.assertEqual(len(parts), 3)


# ===========================================================================
# 7. Edge cases
# ===========================================================================

class TestEdgeCases(unittest.TestCase):
    """Additional edge-case tests."""

    def test_result_defaults(self):
        """Default AdminMenuSelectionResult should indicate failure."""
        result = AdminMenuSelectionResult()
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "")
        self.assertEqual(result.target_program, "")
        self.assertFalse(result.is_not_installed)

    def test_commarea_defaults(self):
        """Default CommArea should have empty strings and zero context."""
        ca = CommArea()
        self.assertEqual(ca.cdemo_from_tranid, "")
        self.assertEqual(ca.cdemo_pgm_context, 0)

    def test_single_option_menu(self):
        """Menu with only one option should accept '1' and reject '2'."""
        custom = [AdminMenuOption(1, "Only Option", "TESTPGMC")]
        r1 = process_admin_menu_selection("1", admin_options=custom)
        self.assertTrue(r1.success)
        r2 = process_admin_menu_selection("2", admin_options=custom)
        self.assertFalse(r2.success)

    def test_spaces_only_input(self):
        """Spaces-only input treated as empty (option 0)."""
        result = validate_admin_option("   ")
        self.assertFalse(result.success)


if __name__ == "__main__":
    unittest.main()
