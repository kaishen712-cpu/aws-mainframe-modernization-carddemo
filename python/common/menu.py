"""
Menu definitions for the CardDemo application.

Translated from:
- COMEN02Y.cpy — main menu (11 options, available to regular users)
- COADM02Y.cpy — admin menu (6 options, available to admin users)

Each option is represented as a ``MenuOption`` dataclass containing
the option number, display name, target program, and required user type.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class MenuOption:
    """A single menu option entry.

    Attributes:
        number:       The numeric option selector (1-based).
        name:         Human-readable menu item label.
        program_name: The COBOL program name (8 chars) invoked by this option.
        user_type:    Required user type — ``'U'`` for regular user,
                      ``'A'`` for admin.  An empty string means any type.
    """

    number: int
    name: str
    program_name: str
    user_type: str = ""


# ---------------------------------------------------------------------------
# Main menu (COMEN02Y.cpy — CARDDEMO-MAIN-MENU-OPTIONS, 11 options)
# ---------------------------------------------------------------------------

MAIN_MENU_OPTIONS: List[MenuOption] = [
    MenuOption(1,  "Account View",                "COACTVWC", "U"),
    MenuOption(2,  "Account Update",              "COACTUPC", "U"),
    MenuOption(3,  "Credit Card List",            "COCRDLIC", "U"),
    MenuOption(4,  "Credit Card View",            "COCRDSLC", "U"),
    MenuOption(5,  "Credit Card Update",          "COCRDUPC", "U"),
    MenuOption(6,  "Transaction List",            "COTRN00C", "U"),
    MenuOption(7,  "Transaction View",            "COTRN01C", "U"),
    MenuOption(8,  "Transaction Add",             "COTRN02C", "U"),
    MenuOption(9,  "Transaction Reports",         "CORPT00C", "U"),
    MenuOption(10, "Bill Payment",                "COBIL00C", "U"),
    MenuOption(11, "Pending Authorization View",  "COPAUS0C", "U"),
]

MAIN_MENU_OPTION_COUNT = len(MAIN_MENU_OPTIONS)


# ---------------------------------------------------------------------------
# Admin menu (COADM02Y.cpy — CARDDEMO-ADMIN-MENU-OPTIONS, 6 options)
# ---------------------------------------------------------------------------

ADMIN_MENU_OPTIONS: List[MenuOption] = [
    MenuOption(1, "User List (Security)",                "COUSR00C"),
    MenuOption(2, "User Add (Security)",                 "COUSR01C"),
    MenuOption(3, "User Update (Security)",              "COUSR02C"),
    MenuOption(4, "User Delete (Security)",              "COUSR03C"),
    MenuOption(5, "Transaction Type List/Update (Db2)",  "COTRTLIC"),
    MenuOption(6, "Transaction Type Maintenance (Db2)",  "COTRTUPC"),
]

ADMIN_MENU_OPTION_COUNT = len(ADMIN_MENU_OPTIONS)


def get_main_menu_option(number: int) -> MenuOption | None:
    """Return the main-menu option matching ``number``, or None.

    Args:
        number: 1-based menu option number.
    """
    for opt in MAIN_MENU_OPTIONS:
        if opt.number == number:
            return opt
    return None


def get_admin_menu_option(number: int) -> MenuOption | None:
    """Return the admin-menu option matching ``number``, or None.

    Args:
        number: 1-based menu option number.
    """
    for opt in ADMIN_MENU_OPTIONS:
        if opt.number == number:
            return opt
    return None
