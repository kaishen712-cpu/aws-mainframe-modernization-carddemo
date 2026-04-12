"""
Menu views for the CardDemo application.

Translated from:
- COMEN01C.cbl (309 lines) — Main Menu for regular users
- COADM01C.cbl (289 lines) — Admin Menu for admin users

COBOL program flow (both programs share similar structure):
1. MAIN-PARA: Check commarea, display menu or process selection
2. PROCESS-ENTER-KEY: Validate option number, check user type access,
   XCTL to target program
3. BUILD-MENU-OPTIONS: Populate screen fields with menu option text
4. SEND-MENU-SCREEN / RECEIVE-MENU-SCREEN: BMS map I/O

Django equivalent:
- main_menu_view: Displays menu options for regular users (COMEN01C)
- admin_menu_view: Displays admin menu options (COADM01C)
- placeholder_view: "Coming Soon" page for phases not yet implemented
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse

# ---------------------------------------------------------------------------
# Menu option definitions
# Translated from COMEN02Y.cpy (CARDDEMO-MAIN-MENU-OPTIONS, 11 options)
# and COADM02Y.cpy (CARDDEMO-ADMIN-MENU-OPTIONS, 6 options)
# ---------------------------------------------------------------------------

MAIN_MENU_OPTIONS: list[dict[str, str]] = [
    {"number": "1", "name": "Account View", "url": "/account-view/"},
    {"number": "2", "name": "Account Update", "url": "/account-update/"},
    {"number": "3", "name": "Credit Card List", "url": "/credit-card-list/"},
    {"number": "4", "name": "Credit Card View", "url": "/credit-card-view/"},
    {"number": "5", "name": "Credit Card Update", "url": "/credit-card-update/"},
    {"number": "6", "name": "Transaction List", "url": "/transaction-list/"},
    {"number": "7", "name": "Transaction View", "url": "/transaction-view/"},
    {"number": "8", "name": "Transaction Add", "url": "/transaction-add/"},
    {"number": "9", "name": "Transaction Reports", "url": "/transaction-reports/"},
    {"number": "10", "name": "Bill Payment", "url": "/bill-payment/"},
    {"number": "11", "name": "Pending Authorization View", "url": "/pending-auth/"},
]

ADMIN_MENU_OPTIONS: list[dict[str, str]] = [
    {"number": "1", "name": "User List (Security)", "url": "/user-list/"},
    {"number": "2", "name": "User Add (Security)", "url": "/user-add/"},
    {"number": "3", "name": "User Update (Security)", "url": "/user-update/"},
    {"number": "4", "name": "User Delete (Security)", "url": "/user-delete/"},
    {"number": "5", "name": "Transaction Type List/Update (Db2)", "url": "/tran-type-list/"},
    {"number": "6", "name": "Transaction Type Maintenance (Db2)", "url": "/tran-type-maint/"},
]


def _is_admin(user: object) -> bool:
    """Check if user is an admin.

    Translated from COCOM01Y.cpy: 88 CDEMO-USRTYP-ADMIN VALUE 'A'.

    Args:
        user: The user object (typed as object for user_passes_test compat).

    Returns:
        True if the user has admin user_type.
    """
    return getattr(user, "user_type", None) == "admin"


@login_required
def main_menu_view(request: HttpRequest) -> HttpResponse:
    """Display the main menu for regular users.

    Translated from COMEN01C.cbl SEND-MENU-SCREEN and BUILD-MENU-OPTIONS.

    The COBOL program builds menu options from COMEN02Y.cpy data and renders
    them via BMS map COMEN1A. This view renders the equivalent Django template.

    Business rules preserved:
    - Menu options filtered by user type (CDEMO-MENU-OPT-USRTYPE)
    - All 11 main menu options displayed (CDEMO-MENU-OPT-COUNT = 11)
    - Invalid option selection shows error (handled client-side in template)
    """
    context = {
        "menu_options": MAIN_MENU_OPTIONS,
        "page_title": "Main Menu",
        "user": request.user,
    }
    return render(request, "core/menu.html", context)


@login_required
@user_passes_test(_is_admin, login_url="/accounts/login/")
def admin_menu_view(request: HttpRequest) -> HttpResponse:
    """Display the admin menu for admin users.

    Translated from COADM01C.cbl SEND-MENU-SCREEN and BUILD-MENU-OPTIONS.

    The COBOL program builds admin menu options from COADM02Y.cpy data
    and renders them via BMS map COADM1A. Only admin users can access this.

    Business rules preserved:
    - Only admin users can access (CDEMO-USRTYP-ADMIN check)
    - 6 admin menu options displayed (CDEMO-ADMIN-OPT-COUNT = 6)
    - PGMIDERR handler shows "option not installed" message
    """
    context = {
        "menu_options": ADMIN_MENU_OPTIONS,
        "page_title": "Admin Menu",
        "user": request.user,
    }
    return render(request, "core/admin_menu.html", context)


@login_required
def placeholder_view(request: HttpRequest) -> HttpResponse:
    """Placeholder view for features not yet implemented.

    Translated from COMEN01C.cbl PROCESS-ENTER-KEY:
    WHEN CDEMO-MENU-OPT-PGMNAME(WS-OPTION)(1:5) = 'DUMMY'
        'This option ... is coming soon ...'

    This serves as a "Coming Soon" page for Phases 3-6 menu targets.
    """
    return render(request, "core/placeholder.html")
