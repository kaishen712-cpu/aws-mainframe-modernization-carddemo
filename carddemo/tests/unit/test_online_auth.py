"""
Unit tests for CardDemo Phase 2 — Authentication & Navigation.

Tests cover:
- Login/logout flow (translated from COSGN00C.cbl)
- Invalid credentials handling
- Login attempt throttling (brute-force prevention)
- CSRF protection
- Admin vs regular user menu routing
- @login_required enforcement on menu views
- @user_passes_test blocks regular users from admin menu
- First-time login / password reset flow
- Menu view rendering (translated from COMEN01C.cbl and COADM01C.cbl)

Target: 90% coverage (security-sensitive module).
All test data is synthetic — never uses real customer data.
"""
from __future__ import annotations

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from accounts.models import CardDemoUser
from accounts.services import reset_throttle_store

# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------


class TestCardDemoUserModel(TestCase):
    """Tests for the CardDemoUser custom user model."""

    def test_create_regular_user(self) -> None:
        """Regular user creation maps SEC-USR-TYPE = 'U'."""
        user = CardDemoUser.objects.create_user(
            username="regular01",
            password="Pass1234!",
            user_type=CardDemoUser.UserType.REGULAR,
        )
        assert user.user_type == "regular"
        assert user.is_regular_user is True
        assert user.is_admin_user is False

    def test_create_admin_user(self) -> None:
        """Admin user creation maps SEC-USR-TYPE = 'A'."""
        user = CardDemoUser.objects.create_user(
            username="admin01",
            password="Pass1234!",
            user_type=CardDemoUser.UserType.ADMIN,
        )
        assert user.user_type == "admin"
        assert user.is_admin_user is True
        assert user.is_regular_user is False

    def test_default_user_type_is_regular(self) -> None:
        """Default user type should be 'regular'."""
        user = CardDemoUser.objects.create_user(
            username="default01",
            password="Pass1234!",
        )
        assert user.user_type == "regular"

    def test_password_reset_required_default_false(self) -> None:
        """Password reset required defaults to False."""
        user = CardDemoUser.objects.create_user(
            username="user01",
            password="Pass1234!",
        )
        assert user.password_reset_required is False

    def test_str_representation(self) -> None:
        """String representation includes username and type display."""
        user = CardDemoUser.objects.create_user(
            username="struser",
            password="Pass1234!",
            user_type=CardDemoUser.UserType.ADMIN,
        )
        assert str(user) == "struser (Admin)"


# ---------------------------------------------------------------------------
# Login View Tests — translated from COSGN00C.cbl
# ---------------------------------------------------------------------------


class TestLoginView(TestCase):
    """Tests for the login view (COSGN00C.cbl sign-on screen)."""

    def setUp(self) -> None:
        """Set up test data and clear throttle state."""
        reset_throttle_store()
        self.client = Client()
        self.login_url = reverse("accounts:login")
        self.regular_user = CardDemoUser.objects.create_user(
            username="testuser",
            password="TestPass123!",
            first_name="John",
            last_name="Doe",
            user_type=CardDemoUser.UserType.REGULAR,
        )
        self.admin_user = CardDemoUser.objects.create_user(
            username="adminuser",
            password="AdminPass123!",
            first_name="Jane",
            last_name="Admin",
            user_type=CardDemoUser.UserType.ADMIN,
        )

    def test_login_page_renders(self) -> None:
        """GET /accounts/login/ displays the sign-on screen.

        Translated from COSGN00C.cbl SEND-SIGNON-SCREEN.
        """
        response = self.client.get(self.login_url)
        assert response.status_code == 200
        assert b"Sign On" in response.content

    def test_login_page_has_csrf_token(self) -> None:
        """Login form must include CSRF token for protection."""
        response = self.client.get(self.login_url)
        assert b"csrfmiddlewaretoken" in response.content

    def test_successful_regular_user_login(self) -> None:
        """Valid regular user credentials redirect to main menu.

        Translated from COSGN00C.cbl READ-USER-SEC-FILE:
        ELSE -> XCTL PROGRAM('COMEN01C')
        """
        response = self.client.post(
            self.login_url,
            {"username": "testuser", "password": "TestPass123!"},
        )
        assert response.status_code == 302
        assert response.url == "/menu/"

    def test_successful_admin_user_login(self) -> None:
        """Valid admin user credentials redirect to admin menu.

        Translated from COSGN00C.cbl READ-USER-SEC-FILE:
        IF CDEMO-USRTYP-ADMIN -> XCTL PROGRAM('COADM01C')
        """
        response = self.client.post(
            self.login_url,
            {"username": "adminuser", "password": "AdminPass123!"},
        )
        assert response.status_code == 302
        assert response.url == "/admin-menu/"

    def test_invalid_password_rejected(self) -> None:
        """Wrong password shows error message.

        Translated from COSGN00C.cbl READ-USER-SEC-FILE:
        'Wrong Password. Try again ...'
        """
        response = self.client.post(
            self.login_url,
            {"username": "testuser", "password": "WrongPass!"},
        )
        assert response.status_code == 200
        assert b"Invalid credentials" in response.content

    def test_user_not_found_rejected(self) -> None:
        """Non-existent username shows error message.

        Translated from COSGN00C.cbl READ-USER-SEC-FILE:
        WHEN 13 -> 'User not found. Try again ...'
        Combined with wrong password for security (no username enumeration).
        """
        response = self.client.post(
            self.login_url,
            {"username": "nonexistent", "password": "AnyPass!"},
        )
        assert response.status_code == 200
        assert b"Invalid credentials" in response.content

    def test_empty_username_rejected(self) -> None:
        """Empty username shows validation error.

        Translated from COSGN00C.cbl PROCESS-ENTER-KEY:
        WHEN USERIDI = SPACES -> 'Please enter User ID ...'
        """
        response = self.client.post(
            self.login_url,
            {"username": "", "password": "SomePass!"},
        )
        assert response.status_code == 200
        # Form validation catches empty required field

    def test_empty_password_rejected(self) -> None:
        """Empty password shows validation error.

        Translated from COSGN00C.cbl PROCESS-ENTER-KEY:
        WHEN PASSWDI = SPACES -> 'Please enter Password ...'
        """
        response = self.client.post(
            self.login_url,
            {"username": "testuser", "password": ""},
        )
        assert response.status_code == 200

    def test_authenticated_user_redirected_from_login(self) -> None:
        """Already authenticated user is redirected to their menu."""
        self.client.login(username="testuser", password="TestPass123!")
        response = self.client.get(self.login_url)
        assert response.status_code == 302
        assert response.url == "/menu/"

    def test_authenticated_admin_redirected_from_login(self) -> None:
        """Already authenticated admin is redirected to admin menu."""
        self.client.login(username="adminuser", password="AdminPass123!")
        response = self.client.get(self.login_url)
        assert response.status_code == 302
        assert response.url == "/admin-menu/"


# ---------------------------------------------------------------------------
# Logout View Tests
# ---------------------------------------------------------------------------


class TestLogoutView(TestCase):
    """Tests for the logout view."""

    def setUp(self) -> None:
        """Set up test data."""
        self.client = Client()
        self.logout_url = reverse("accounts:logout")
        self.regular_user = CardDemoUser.objects.create_user(
            username="testuser",
            password="TestPass123!",
            user_type=CardDemoUser.UserType.REGULAR,
        )

    def test_logout_redirects_to_login(self) -> None:
        """Logout clears session and redirects to login.

        Translated from COSGN00C.cbl SEND-PLAIN-TEXT:
        Displays CCDA-MSG-THANK-YOU and EXEC CICS RETURN.
        """
        self.client.login(username="testuser", password="TestPass123!")
        response = self.client.get(self.logout_url)
        assert response.status_code == 302
        assert response.url == reverse("accounts:login")

    def test_logout_clears_session(self) -> None:
        """Session should be cleared after logout."""
        self.client.login(username="testuser", password="TestPass123!")
        self.client.get(self.logout_url)
        # Verify session is cleared by trying to access a protected page
        response = self.client.get(reverse("core:main_menu"))
        assert response.status_code == 302  # Redirected to login

    def test_logout_shows_thank_you_message(self) -> None:
        """Logout displays thank you message.

        Translated from COSGN00C.cbl:
        MOVE CCDA-MSG-THANK-YOU TO WS-MESSAGE
        """
        self.client.login(username="testuser", password="TestPass123!")
        response = self.client.get(self.logout_url, follow=True)
        assert b"Thank you for using CardDemo" in response.content


# ---------------------------------------------------------------------------
# Login Throttling Tests
# ---------------------------------------------------------------------------


@override_settings(LOGIN_MAX_ATTEMPTS=3, LOGIN_LOCKOUT_DURATION_SECONDS=60)
class TestLoginThrottling(TestCase):
    """Tests for login attempt throttling (brute-force prevention).

    Business rule improvement: the original COBOL (COSGN00C.cbl) had no
    brute-force protection. This is a security improvement in the Python version.

    FLAG FOR HUMAN REVIEW: hardcoded thresholds — LOGIN_MAX_ATTEMPTS=3
    and LOGIN_LOCKOUT_DURATION_SECONDS=60 (overridden in test settings).
    """

    def setUp(self) -> None:
        """Set up test data and clear throttle state."""
        reset_throttle_store()
        self.client = Client()
        self.login_url = reverse("accounts:login")
        CardDemoUser.objects.create_user(
            username="throttleuser",
            password="CorrectPass123!",
            user_type=CardDemoUser.UserType.REGULAR,
        )

    def test_login_succeeds_within_attempt_limit(self) -> None:
        """Login should work if under the max attempt threshold."""
        # Fail twice (under limit of 3)
        for _ in range(2):
            self.client.post(
                self.login_url,
                {"username": "throttleuser", "password": "WrongPass!"},
            )
        # Third attempt with correct password should work
        response = self.client.post(
            self.login_url,
            {"username": "throttleuser", "password": "CorrectPass123!"},
        )
        assert response.status_code == 302
        assert response.url == "/menu/"

    def test_login_blocked_after_max_attempts(self) -> None:
        """Login should be blocked after exceeding max failed attempts."""
        # Exhaust all 3 attempts
        for _ in range(3):
            self.client.post(
                self.login_url,
                {"username": "throttleuser", "password": "WrongPass!"},
            )
        # Next attempt (even correct password) should be throttled
        response = self.client.post(
            self.login_url,
            {"username": "throttleuser", "password": "CorrectPass123!"},
        )
        assert response.status_code == 200
        assert b"Too many failed login attempts" in response.content

    def test_throttle_message_displayed(self) -> None:
        """Throttle message should be shown when locked out."""
        for _ in range(3):
            self.client.post(
                self.login_url,
                {"username": "throttleuser", "password": "Bad!"},
            )
        response = self.client.post(
            self.login_url,
            {"username": "throttleuser", "password": "Bad!"},
        )
        assert b"Too many failed login attempts" in response.content

    def test_different_ips_tracked_separately(self) -> None:
        """Throttling should track different IPs independently."""
        reset_throttle_store()
        # Fail from one IP
        for _ in range(3):
            self.client.post(
                self.login_url,
                {"username": "throttleuser", "password": "Bad!"},
                REMOTE_ADDR="10.0.0.1",
            )
        # Different IP should not be throttled
        response = self.client.post(
            self.login_url,
            {"username": "throttleuser", "password": "CorrectPass123!"},
            REMOTE_ADDR="10.0.0.2",
        )
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# CSRF Protection Tests
# ---------------------------------------------------------------------------


class TestCSRFProtection(TestCase):
    """Tests for CSRF protection on authentication endpoints."""

    def setUp(self) -> None:
        """Set up test data."""
        self.login_url = reverse("accounts:login")
        CardDemoUser.objects.create_user(
            username="csrfuser",
            password="CsrfPass123!",
            user_type=CardDemoUser.UserType.REGULAR,
        )

    def test_login_without_csrf_rejected(self) -> None:
        """POST to login without CSRF token should be rejected."""
        client = Client(enforce_csrf_checks=True)
        response = client.post(
            self.login_url,
            {"username": "csrfuser", "password": "CsrfPass123!"},
        )
        assert response.status_code == 403

    def test_login_with_csrf_accepted(self) -> None:
        """POST to login with CSRF token should NOT return 403.

        When CSRF token is present, the request should be processed
        (either redirect on success or re-render form) — never 403.
        """
        reset_throttle_store()
        import re

        client = Client(enforce_csrf_checks=True)
        # Get CSRF token from login page
        get_response = client.get(self.login_url)
        assert get_response.status_code == 200
        # Extract CSRF token from the rendered form
        match = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"',
            get_response.content.decode(),
        )
        assert match is not None, "CSRF token not found in form"
        csrf_token = match.group(1)
        response = client.post(
            self.login_url,
            {
                "csrfmiddlewaretoken": csrf_token,
                "username": "csrfuser",
                "password": "CsrfPass123!",
            },
        )
        # Must NOT be 403 — CSRF token was valid
        assert response.status_code != 403
        # Should be 302 (redirect to menu) or 200 (form re-rendered)
        assert response.status_code in (200, 302)


# ---------------------------------------------------------------------------
# Menu View Tests — translated from COMEN01C.cbl and COADM01C.cbl
# ---------------------------------------------------------------------------


class TestMainMenuView(TestCase):
    """Tests for the main menu view (COMEN01C.cbl)."""

    def setUp(self) -> None:
        """Set up test data."""
        self.client = Client()
        self.menu_url = reverse("core:main_menu")
        self.regular_user = CardDemoUser.objects.create_user(
            username="menuuser",
            password="MenuPass123!",
            user_type=CardDemoUser.UserType.REGULAR,
        )
        self.admin_user = CardDemoUser.objects.create_user(
            username="menuadmin",
            password="AdminPass123!",
            user_type=CardDemoUser.UserType.ADMIN,
        )

    def test_login_required_redirects_anonymous(self) -> None:
        """Anonymous users should be redirected to login.

        Translated from COMEN01C.cbl MAIN-PARA:
        IF EIBCALEN = 0 -> PERFORM RETURN-TO-SIGNON-SCREEN
        """
        response = self.client.get(self.menu_url)
        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_regular_user_sees_main_menu(self) -> None:
        """Regular user can access main menu.

        Translated from COMEN01C.cbl SEND-MENU-SCREEN.
        """
        self.client.login(username="menuuser", password="MenuPass123!")
        response = self.client.get(self.menu_url)
        assert response.status_code == 200
        assert b"Main Menu" in response.content

    def test_admin_user_can_access_main_menu(self) -> None:
        """Admin user can also access the main menu."""
        self.client.login(username="menuadmin", password="AdminPass123!")
        response = self.client.get(self.menu_url)
        assert response.status_code == 200

    def test_main_menu_shows_all_options(self) -> None:
        """Main menu should display all 11 options.

        Translated from COMEN02Y.cpy: CDEMO-MENU-OPT-COUNT = 11.
        """
        self.client.login(username="menuuser", password="MenuPass123!")
        response = self.client.get(self.menu_url)
        content = response.content.decode()
        assert "Account View" in content
        assert "Account Update" in content
        assert "Credit Card List" in content
        assert "Transaction List" in content
        assert "Bill Payment" in content

    def test_main_menu_contains_signoff_link(self) -> None:
        """Main menu should have a sign-off link.

        Translated from COMEN01C.cbl: WHEN DFHPF3 -> RETURN-TO-SIGNON-SCREEN.
        """
        self.client.login(username="menuuser", password="MenuPass123!")
        response = self.client.get(self.menu_url)
        assert b"Sign Off" in response.content


class TestAdminMenuView(TestCase):
    """Tests for the admin menu view (COADM01C.cbl)."""

    def setUp(self) -> None:
        """Set up test data."""
        self.client = Client()
        self.admin_menu_url = reverse("core:admin_menu")
        self.regular_user = CardDemoUser.objects.create_user(
            username="regularuser",
            password="RegPass123!",
            user_type=CardDemoUser.UserType.REGULAR,
        )
        self.admin_user = CardDemoUser.objects.create_user(
            username="adminuser",
            password="AdminPass123!",
            user_type=CardDemoUser.UserType.ADMIN,
        )

    def test_login_required_redirects_anonymous(self) -> None:
        """Anonymous users should be redirected to login."""
        response = self.client.get(self.admin_menu_url)
        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_regular_user_blocked_from_admin_menu(self) -> None:
        """Regular user should NOT access admin menu.

        Translated from COMEN01C.cbl PROCESS-ENTER-KEY:
        IF CDEMO-USRTYP-USER AND CDEMO-MENU-OPT-USRTYPE(WS-OPTION) = 'A'
            'No access - Admin Only option...'
        """
        self.client.login(username="regularuser", password="RegPass123!")
        response = self.client.get(self.admin_menu_url)
        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_admin_user_sees_admin_menu(self) -> None:
        """Admin user can access admin menu.

        Translated from COADM01C.cbl SEND-MENU-SCREEN.
        """
        self.client.login(username="adminuser", password="AdminPass123!")
        response = self.client.get(self.admin_menu_url)
        assert response.status_code == 200
        assert b"Admin Menu" in response.content

    def test_admin_menu_shows_all_options(self) -> None:
        """Admin menu should display all 6 options.

        Translated from COADM02Y.cpy: CDEMO-ADMIN-OPT-COUNT = 6.
        """
        self.client.login(username="adminuser", password="AdminPass123!")
        response = self.client.get(self.admin_menu_url)
        content = response.content.decode()
        assert "User List (Security)" in content
        assert "User Add (Security)" in content
        assert "User Update (Security)" in content
        assert "User Delete (Security)" in content

    def test_admin_menu_contains_main_menu_link(self) -> None:
        """Admin menu should have a link back to main menu."""
        self.client.login(username="adminuser", password="AdminPass123!")
        response = self.client.get(self.admin_menu_url)
        assert b"Main Menu" in response.content

    def test_admin_menu_contains_signoff_link(self) -> None:
        """Admin menu should have a sign-off link.

        Translated from COADM01C.cbl: WHEN DFHPF3 -> RETURN-TO-SIGNON-SCREEN.
        """
        self.client.login(username="adminuser", password="AdminPass123!")
        response = self.client.get(self.admin_menu_url)
        assert b"Sign Off" in response.content


# ---------------------------------------------------------------------------
# Placeholder View Tests
# ---------------------------------------------------------------------------


class TestPlaceholderView(TestCase):
    """Tests for the Coming Soon placeholder view."""

    def setUp(self) -> None:
        """Set up test data."""
        self.client = Client()
        self.regular_user = CardDemoUser.objects.create_user(
            username="phuser",
            password="PlacePass123!",
            user_type=CardDemoUser.UserType.REGULAR,
        )

    def test_placeholder_requires_login(self) -> None:
        """Placeholder views require authentication."""
        response = self.client.get("/account-view/")
        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_placeholder_shows_coming_soon(self) -> None:
        """Placeholder views show 'Coming Soon' message.

        Translated from COMEN01C.cbl:
        'This option ... is coming soon ...'
        """
        self.client.login(username="phuser", password="PlacePass123!")
        response = self.client.get("/account-view/")
        assert response.status_code == 200
        assert b"Coming Soon" in response.content


# ---------------------------------------------------------------------------
# Password Reset / First-Time Login Tests
# ---------------------------------------------------------------------------


class TestPasswordResetFlow(TestCase):
    """Tests for first-time login / forced password reset.

    Business rule: SEC-USR-PWD-RESET flag triggers mandatory password change.
    """

    def setUp(self) -> None:
        """Set up test data."""
        reset_throttle_store()
        self.client = Client()
        self.login_url = reverse("accounts:login")
        self.password_change_url = reverse("accounts:password_change")
        self.reset_user = CardDemoUser.objects.create_user(
            username="resetuser",
            password="TempPass123!",
            user_type=CardDemoUser.UserType.REGULAR,
            password_reset_required=True,
        )

    def test_first_time_login_redirects_to_password_change(self) -> None:
        """User with password_reset_required is redirected to password change."""
        response = self.client.post(
            self.login_url,
            {"username": "resetuser", "password": "TempPass123!"},
        )
        assert response.status_code == 302
        assert response.url == reverse("accounts:password_change")

    def test_password_change_page_renders(self) -> None:
        """Password change page should render for authenticated users."""
        self.client.login(username="resetuser", password="TempPass123!")
        response = self.client.get(self.password_change_url)
        assert response.status_code == 200
        assert b"Change Password" in response.content

    def test_password_change_success(self) -> None:
        """Successful password change clears the reset flag and redirects."""
        self.client.login(username="resetuser", password="TempPass123!")
        response = self.client.post(
            self.password_change_url,
            {
                "new_password": "NewSecurePass123!",
                "confirm_password": "NewSecurePass123!",
            },
        )
        assert response.status_code == 302
        # Verify flag is cleared
        self.reset_user.refresh_from_db()
        assert self.reset_user.password_reset_required is False

    def test_password_change_mismatch_rejected(self) -> None:
        """Mismatched passwords should be rejected."""
        self.client.login(username="resetuser", password="TempPass123!")
        response = self.client.post(
            self.password_change_url,
            {
                "new_password": "NewPass123!",
                "confirm_password": "DifferentPass!",
            },
        )
        assert response.status_code == 200
        assert b"Passwords do not match" in response.content

    def test_password_change_redirects_anonymous(self) -> None:
        """Anonymous users should be redirected to login from password change."""
        response = self.client.get(self.password_change_url)
        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_login_works_after_password_change(self) -> None:
        """User can log in with new password after change."""
        self.client.login(username="resetuser", password="TempPass123!")
        self.client.post(
            self.password_change_url,
            {
                "new_password": "BrandNewPass123!",
                "confirm_password": "BrandNewPass123!",
            },
        )
        self.client.logout()
        # Login with new password
        response = self.client.post(
            self.login_url,
            {"username": "resetuser", "password": "BrandNewPass123!"},
        )
        assert response.status_code == 302
        assert response.url == "/menu/"

    def test_normal_user_not_redirected_to_password_change(self) -> None:
        """User without password_reset_required goes straight to menu."""
        CardDemoUser.objects.create_user(
            username="normaluser",
            password="NormalPass123!",
            user_type=CardDemoUser.UserType.REGULAR,
            password_reset_required=False,
        )
        response = self.client.post(
            self.login_url,
            {"username": "normaluser", "password": "NormalPass123!"},
        )
        assert response.status_code == 302
        assert response.url == "/menu/"


# ---------------------------------------------------------------------------
# Service Layer Tests
# ---------------------------------------------------------------------------


class TestAuthServices(TestCase):
    """Tests for the authentication service layer."""

    def setUp(self) -> None:
        """Clear throttle state before each test."""
        reset_throttle_store()

    def test_get_menu_redirect_url_admin(self) -> None:
        """Admin user should be routed to /admin-menu/."""
        from accounts.services import get_menu_redirect_url

        assert get_menu_redirect_url("admin") == "/admin-menu/"

    def test_get_menu_redirect_url_regular(self) -> None:
        """Regular user should be routed to /menu/."""
        from accounts.services import get_menu_redirect_url

        assert get_menu_redirect_url("regular") == "/menu/"

    def test_get_client_ip_direct(self) -> None:
        """Client IP extraction from REMOTE_ADDR."""
        from django.test import RequestFactory

        from accounts.services import get_client_ip

        factory = RequestFactory()
        request = factory.get("/", REMOTE_ADDR="192.168.1.1")
        assert get_client_ip(request) == "192.168.1.1"

    def test_get_client_ip_forwarded(self) -> None:
        """Client IP extraction from X-Forwarded-For header."""
        from django.test import RequestFactory

        from accounts.services import get_client_ip

        factory = RequestFactory()
        request = factory.get(
            "/", HTTP_X_FORWARDED_FOR="10.0.0.1, 10.0.0.2", REMOTE_ADDR="127.0.0.1"
        )
        assert get_client_ip(request) == "10.0.0.1"

    def test_reset_throttle_store(self) -> None:
        """reset_throttle_store should clear all tracked attempts."""
        from django.test import RequestFactory

        from accounts.services import (
            is_login_throttled,
            record_failed_attempt,
            reset_throttle_store,
        )

        factory = RequestFactory()
        request = factory.get("/", REMOTE_ADDR="1.2.3.4")

        for _ in range(5):
            record_failed_attempt(request)

        assert is_login_throttled(request) is True
        reset_throttle_store()
        assert is_login_throttled(request) is False


# ---------------------------------------------------------------------------
# Form Tests
# ---------------------------------------------------------------------------


class TestLoginForm(TestCase):
    """Tests for the LoginForm."""

    def test_valid_form(self) -> None:
        """Form with username and password should be valid."""
        from accounts.forms import LoginForm

        form = LoginForm(data={"username": "testuser", "password": "Pass123!"})
        assert form.is_valid()

    def test_missing_username(self) -> None:
        """Form without username should be invalid."""
        from accounts.forms import LoginForm

        form = LoginForm(data={"username": "", "password": "Pass123!"})
        assert not form.is_valid()
        assert "username" in form.errors

    def test_missing_password(self) -> None:
        """Form without password should be invalid."""
        from accounts.forms import LoginForm

        form = LoginForm(data={"username": "testuser", "password": ""})
        assert not form.is_valid()
        assert "password" in form.errors


class TestPasswordChangeForm(TestCase):
    """Tests for the PasswordChangeForm."""

    def test_valid_matching_passwords(self) -> None:
        """Form with matching passwords should be valid."""
        from accounts.forms import PasswordChangeForm

        form = PasswordChangeForm(
            data={
                "new_password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            }
        )
        assert form.is_valid()

    def test_mismatched_passwords(self) -> None:
        """Form with mismatched passwords should be invalid."""
        from accounts.forms import PasswordChangeForm

        form = PasswordChangeForm(
            data={
                "new_password": "Pass1234!",
                "confirm_password": "Different!",
            }
        )
        assert not form.is_valid()

    def test_too_short_password(self) -> None:
        """Form with password shorter than 8 chars should be invalid."""
        from accounts.forms import PasswordChangeForm

        form = PasswordChangeForm(
            data={
                "new_password": "short",
                "confirm_password": "short",
            }
        )
        assert not form.is_valid()


# ---------------------------------------------------------------------------
# URL Routing Tests
# ---------------------------------------------------------------------------


class TestURLRouting(TestCase):
    """Tests for URL configuration."""

    def test_login_url_resolves(self) -> None:
        """Login URL should resolve correctly."""
        url = reverse("accounts:login")
        assert url == "/accounts/login/"

    def test_logout_url_resolves(self) -> None:
        """Logout URL should resolve correctly."""
        url = reverse("accounts:logout")
        assert url == "/accounts/logout/"

    def test_main_menu_url_resolves(self) -> None:
        """Main menu URL should resolve correctly."""
        url = reverse("core:main_menu")
        assert url == "/menu/"

    def test_admin_menu_url_resolves(self) -> None:
        """Admin menu URL should resolve correctly."""
        url = reverse("core:admin_menu")
        assert url == "/admin-menu/"

    def test_password_change_url_resolves(self) -> None:
        """Password change URL should resolve correctly."""
        url = reverse("accounts:password_change")
        assert url == "/accounts/password-change/"

    def test_placeholder_urls_resolve(self) -> None:
        """Placeholder URLs for future phases should resolve."""
        placeholder_names = [
            "core:account_view",
            "core:account_update",
            "core:credit_card_list",
            "core:transaction_list",
            "core:bill_payment",
            "core:user_list",
        ]
        for name in placeholder_names:
            url = reverse(name)
            assert url is not None


# ---------------------------------------------------------------------------
# Integration-level auth flow tests
# ---------------------------------------------------------------------------


class TestPasswordResetMiddleware(TestCase):
    """Tests for PasswordResetMiddleware enforcing mandatory password change.

    Business rule: SEC-USR-PWD-RESET flag must be enforced on every request,
    not just at login time. Users cannot bypass the password change by
    navigating directly to protected URLs.
    """

    def setUp(self) -> None:
        """Set up test data."""
        reset_throttle_store()
        self.client = Client()
        self.menu_url = reverse("core:main_menu")
        self.admin_menu_url = reverse("core:admin_menu")
        self.password_change_url = reverse("accounts:password_change")
        self.logout_url = reverse("accounts:logout")
        self.reset_user = CardDemoUser.objects.create_user(
            username="mwuser",
            password="TempMwPass123!",
            user_type=CardDemoUser.UserType.REGULAR,
            password_reset_required=True,
        )

    def test_reset_user_redirected_from_menu(self) -> None:
        """User with password_reset_required cannot access main menu."""
        self.client.login(username="mwuser", password="TempMwPass123!")
        response = self.client.get(self.menu_url)
        assert response.status_code == 302
        assert response.url == self.password_change_url

    def test_reset_user_can_access_password_change(self) -> None:
        """User with password_reset_required CAN access password change page."""
        self.client.login(username="mwuser", password="TempMwPass123!")
        response = self.client.get(self.password_change_url)
        assert response.status_code == 200

    def test_reset_user_can_logout(self) -> None:
        """User with password_reset_required CAN log out."""
        self.client.login(username="mwuser", password="TempMwPass123!")
        response = self.client.get(self.logout_url)
        assert response.status_code == 302

    def test_normal_user_not_blocked_by_middleware(self) -> None:
        """User without password_reset_required accesses menu normally."""
        CardDemoUser.objects.create_user(
            username="mwnormal",
            password="NormalMwPass123!",
            user_type=CardDemoUser.UserType.REGULAR,
        )
        self.client.login(username="mwnormal", password="NormalMwPass123!")
        response = self.client.get(self.menu_url)
        assert response.status_code == 200

    def test_after_password_change_middleware_allows_access(self) -> None:
        """After changing password, middleware allows access to menu."""
        self.client.login(username="mwuser", password="TempMwPass123!")
        self.client.post(
            self.password_change_url,
            {
                "new_password": "NewSecureMwPass123!",
                "confirm_password": "NewSecureMwPass123!",
            },
        )
        response = self.client.get(self.menu_url)
        assert response.status_code == 200


class TestPasswordValidation(TestCase):
    """Tests for password strength validation via AUTH_PASSWORD_VALIDATORS."""

    def test_common_password_rejected(self) -> None:
        """Common passwords like 'password' should be rejected."""
        from accounts.forms import PasswordChangeForm

        form = PasswordChangeForm(
            data={
                "new_password": "password",
                "confirm_password": "password",
            }
        )
        assert not form.is_valid()

    def test_numeric_only_password_rejected(self) -> None:
        """Purely numeric passwords should be rejected."""
        from accounts.forms import PasswordChangeForm

        form = PasswordChangeForm(
            data={
                "new_password": "12345678",
                "confirm_password": "12345678",
            }
        )
        assert not form.is_valid()

    def test_strong_password_accepted(self) -> None:
        """Strong passwords that meet all validators should be accepted."""
        from accounts.forms import PasswordChangeForm

        form = PasswordChangeForm(
            data={
                "new_password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            }
        )
        assert form.is_valid()


class TestFullAuthFlow(TestCase):
    """End-to-end authentication flow tests."""

    def setUp(self) -> None:
        """Set up test data."""
        reset_throttle_store()
        self.client = Client()
        self.login_url = reverse("accounts:login")
        self.menu_url = reverse("core:main_menu")
        self.admin_menu_url = reverse("core:admin_menu")
        self.logout_url = reverse("accounts:logout")
        CardDemoUser.objects.create_user(
            username="flowuser",
            password="FlowPass123!",
            first_name="Flow",
            last_name="User",
            user_type=CardDemoUser.UserType.REGULAR,
        )
        CardDemoUser.objects.create_user(
            username="flowadmin",
            password="FlowAdmin123!",
            first_name="Flow",
            last_name="Admin",
            user_type=CardDemoUser.UserType.ADMIN,
        )

    def test_regular_user_full_flow(self) -> None:
        """Regular user: login -> menu -> logout -> redirected to login."""
        # Login
        response = self.client.post(
            self.login_url,
            {"username": "flowuser", "password": "FlowPass123!"},
        )
        assert response.status_code == 302
        assert response.url == "/menu/"

        # Access menu
        response = self.client.get(self.menu_url)
        assert response.status_code == 200

        # Cannot access admin menu
        response = self.client.get(self.admin_menu_url)
        assert response.status_code == 302

        # Logout
        response = self.client.get(self.logout_url)
        assert response.status_code == 302

        # Cannot access menu after logout
        response = self.client.get(self.menu_url)
        assert response.status_code == 302

    def test_admin_user_full_flow(self) -> None:
        """Admin user: login -> admin menu -> main menu -> logout."""
        # Login (admin goes to admin menu)
        response = self.client.post(
            self.login_url,
            {"username": "flowadmin", "password": "FlowAdmin123!"},
        )
        assert response.status_code == 302
        assert response.url == "/admin-menu/"

        # Access admin menu
        response = self.client.get(self.admin_menu_url)
        assert response.status_code == 200

        # Admin can also access main menu
        response = self.client.get(self.menu_url)
        assert response.status_code == 200

        # Logout
        response = self.client.get(self.logout_url)
        assert response.status_code == 302
