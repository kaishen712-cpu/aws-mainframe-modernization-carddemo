"""
Unit tests for common/menu.py.

Covers MenuOption dataclass, main menu options, admin menu options,
and the get_*_menu_option lookup functions including boundary cases.
"""

from python.common.menu import (
    MenuOption,
    MAIN_MENU_OPTIONS,
    MAIN_MENU_OPTION_COUNT,
    ADMIN_MENU_OPTIONS,
    ADMIN_MENU_OPTION_COUNT,
    get_main_menu_option,
    get_admin_menu_option,
)


# ===================================================================
# MenuOption Dataclass
# ===================================================================

class TestMenuOption:
    """Tests for MenuOption dataclass."""

    def test_defaults(self) -> None:
        opt = MenuOption(number=1, name="Test", program_name="TESTPGM")
        assert opt.number == 1
        assert opt.name == "Test"
        assert opt.program_name == "TESTPGM"
        assert opt.user_type == ""

    def test_with_user_type(self) -> None:
        opt = MenuOption(number=1, name="Test", program_name="TESTPGM", user_type="A")
        assert opt.user_type == "A"


# ===================================================================
# Main Menu Options
# ===================================================================

class TestMainMenuOptions:
    """Tests for COMEN02Y.cpy main menu options."""

    def test_option_count(self) -> None:
        assert MAIN_MENU_OPTION_COUNT == 11
        assert len(MAIN_MENU_OPTIONS) == 11

    def test_first_option(self) -> None:
        opt = MAIN_MENU_OPTIONS[0]
        assert opt.number == 1
        assert opt.name == "Account View"
        assert opt.program_name == "COACTVWC"
        assert opt.user_type == "U"

    def test_last_option(self) -> None:
        opt = MAIN_MENU_OPTIONS[-1]
        assert opt.number == 11
        assert opt.name == "Pending Authorization View"
        assert opt.program_name == "COPAUS0C"

    def test_transaction_add_option(self) -> None:
        opt = MAIN_MENU_OPTIONS[7]
        assert opt.number == 8
        assert opt.name == "Transaction Add"
        assert opt.program_name == "COTRN02C"

    def test_all_options_are_menu_options(self) -> None:
        for opt in MAIN_MENU_OPTIONS:
            assert isinstance(opt, MenuOption)

    def test_option_numbers_sequential(self) -> None:
        for i, opt in enumerate(MAIN_MENU_OPTIONS, start=1):
            assert opt.number == i


# ===================================================================
# Admin Menu Options
# ===================================================================

class TestAdminMenuOptions:
    """Tests for COADM02Y.cpy admin menu options."""

    def test_option_count(self) -> None:
        assert ADMIN_MENU_OPTION_COUNT == 6
        assert len(ADMIN_MENU_OPTIONS) == 6

    def test_first_option(self) -> None:
        opt = ADMIN_MENU_OPTIONS[0]
        assert opt.number == 1
        assert opt.name == "User List (Security)"
        assert opt.program_name == "COUSR00C"

    def test_last_option(self) -> None:
        opt = ADMIN_MENU_OPTIONS[-1]
        assert opt.number == 6
        assert opt.program_name == "COTRTUPC"

    def test_all_options_are_menu_options(self) -> None:
        for opt in ADMIN_MENU_OPTIONS:
            assert isinstance(opt, MenuOption)


# ===================================================================
# get_main_menu_option
# ===================================================================

class TestGetMainMenuOption:
    """Tests for get_main_menu_option lookup function."""

    def test_valid_option_1(self) -> None:
        opt = get_main_menu_option(1)
        assert opt is not None
        assert opt.name == "Account View"

    def test_valid_option_11(self) -> None:
        opt = get_main_menu_option(11)
        assert opt is not None
        assert opt.number == 11

    def test_option_not_found_zero(self) -> None:
        assert get_main_menu_option(0) is None

    def test_option_not_found_negative(self) -> None:
        assert get_main_menu_option(-1) is None

    def test_option_not_found_too_high(self) -> None:
        assert get_main_menu_option(12) is None

    def test_option_not_found_99(self) -> None:
        assert get_main_menu_option(99) is None


# ===================================================================
# get_admin_menu_option
# ===================================================================

class TestGetAdminMenuOption:
    """Tests for get_admin_menu_option lookup function."""

    def test_valid_option_1(self) -> None:
        opt = get_admin_menu_option(1)
        assert opt is not None
        assert opt.name == "User List (Security)"

    def test_valid_option_6(self) -> None:
        opt = get_admin_menu_option(6)
        assert opt is not None
        assert opt.number == 6

    def test_option_not_found_zero(self) -> None:
        assert get_admin_menu_option(0) is None

    def test_option_not_found_negative(self) -> None:
        assert get_admin_menu_option(-1) is None

    def test_option_not_found_too_high(self) -> None:
        assert get_admin_menu_option(7) is None

    def test_option_not_found_99(self) -> None:
        assert get_admin_menu_option(99) is None
