"""
Unit tests for Phase 6: User Administration.

Tests cover:
- UserProfile model
- User services (is_admin, list, create, update, delete)
- User forms (filter, create, update)
- User views (list, create, update, delete) with admin restriction

Coverage target: 70% minimum.
All test data is synthetic — no real customer data (CPS 234).
"""

from __future__ import annotations

from django.contrib.auth.models import User
from django.test import Client, TestCase

from python.user_admin.forms import (
    UserCreateForm,
    UserFilterForm,
    UserUpdateForm,
)
from python.user_admin.models import UserProfile
from python.user_admin.services import (
    create_user,
    delete_user,
    get_user_list,
    is_admin_user,
    update_user,
)


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestUserProfileModel(TestCase):
    """Tests for the UserProfile model."""

    def test_create_profile(self) -> None:
        """UserProfile can be created with user link."""
        user = User.objects.create_user(
            username="testuser", password="testpass123",
        )
        profile = UserProfile.objects.create(
            user=user, user_type="U",
        )
        assert profile.pk is not None
        assert profile.user_type == "U"

    def test_admin_profile(self) -> None:
        """Admin profile is_admin returns True."""
        user = User.objects.create_user(
            username="adminuser", password="testpass123",
        )
        profile = UserProfile.objects.create(
            user=user, user_type="A",
        )
        assert profile.is_admin is True

    def test_regular_profile(self) -> None:
        """Regular profile is_admin returns False."""
        user = User.objects.create_user(
            username="reguser", password="testpass123",
        )
        profile = UserProfile.objects.create(
            user=user, user_type="U",
        )
        assert profile.is_admin is False

    def test_str_representation(self) -> None:
        """Profile str shows username and type."""
        user = User.objects.create_user(
            username="jdoe", password="testpass123",
        )
        profile = UserProfile.objects.create(
            user=user, user_type="A",
        )
        result = str(profile)
        assert "jdoe" in result
        assert "Admin" in result


# ---------------------------------------------------------------------------
# Service tests — is_admin_user
# ---------------------------------------------------------------------------


class TestIsAdminUser(TestCase):
    """Tests for is_admin_user service function."""

    def test_staff_user_is_admin(self) -> None:
        """Django staff users are admins."""
        user = User.objects.create_user(
            username="staffuser",
            password="testpass123",
            is_staff=True,
        )
        assert is_admin_user(user) is True

    def test_superuser_is_admin(self) -> None:
        """Django superusers are admins."""
        user = User.objects.create_superuser(
            username="superuser",
            password="testpass123",
        )
        assert is_admin_user(user) is True

    def test_profile_admin_is_admin(self) -> None:
        """User with admin profile type is admin."""
        user = User.objects.create_user(
            username="profileadmin", password="testpass123",
        )
        UserProfile.objects.create(
            user=user, user_type="A",
        )
        assert is_admin_user(user) is True

    def test_regular_user_not_admin(self) -> None:
        """Regular user without admin profile is not admin."""
        user = User.objects.create_user(
            username="reguser", password="testpass123",
        )
        UserProfile.objects.create(
            user=user, user_type="U",
        )
        assert is_admin_user(user) is False

    def test_no_profile_not_admin(self) -> None:
        """User without profile is not admin."""
        user = User.objects.create_user(
            username="noprofile", password="testpass123",
        )
        assert is_admin_user(user) is False


# ---------------------------------------------------------------------------
# Service tests — get_user_list
# ---------------------------------------------------------------------------


class TestGetUserList(TestCase):
    """Tests for get_user_list service function."""

    def setUp(self) -> None:
        """Create synthetic users."""
        User.objects.create_user(
            username="jdoe",
            password="testpass123",
            first_name="John",
            last_name="Doe",
        )
        User.objects.create_user(
            username="jsmith",
            password="testpass123",
            first_name="Jane",
            last_name="Smith",
        )

    def test_no_filter(self) -> None:
        """No filter returns all users."""
        result = get_user_list()
        assert result.count() == 2

    def test_search_by_username(self) -> None:
        """Search by username works."""
        result = get_user_list(search_query="jdoe")
        assert result.count() == 1

    def test_search_by_first_name(self) -> None:
        """Search by first name works."""
        result = get_user_list(search_query="John")
        assert result.count() == 1

    def test_search_by_last_name(self) -> None:
        """Search by last name works."""
        result = get_user_list(search_query="Smith")
        assert result.count() == 1

    def test_search_no_results(self) -> None:
        """Non-matching search returns empty."""
        result = get_user_list(search_query="nobody")
        assert result.count() == 0

    def test_ordered_by_username(self) -> None:
        """Results are ordered by username."""
        result = list(get_user_list())
        assert result[0].username == "jdoe"
        assert result[1].username == "jsmith"


# ---------------------------------------------------------------------------
# Service tests — create_user
# ---------------------------------------------------------------------------


class TestCreateUser(TestCase):
    """Tests for create_user service function."""

    def test_create_regular_user(self) -> None:
        """Regular user can be created."""
        result = create_user(
            username="newuser",
            password="pass1234",
            first_name="New",
            last_name="User",
            user_type="U",
        )
        assert result.success
        user = User.objects.get(username="newuser")
        assert user.first_name == "New"
        assert not user.is_staff

    def test_create_admin_user(self) -> None:
        """Admin user is created with is_staff=True."""
        result = create_user(
            username="newadmin",
            password="pass1234",
            first_name="Admin",
            last_name="User",
            user_type="A",
        )
        assert result.success
        user = User.objects.get(username="newadmin")
        assert user.is_staff
        profile = user.carddemo_profile
        assert profile.user_type == "A"

    def test_duplicate_username(self) -> None:
        """Duplicate username returns error."""
        User.objects.create_user(
            username="existing", password="pass1234",
        )
        result = create_user(
            username="existing",
            password="pass1234",
            first_name="Dup",
            last_name="User",
            user_type="U",
        )
        assert not result.success
        assert "already exists" in result.message

    def test_empty_username(self) -> None:
        """Empty username fails."""
        result = create_user(
            username="",
            password="pass1234",
            first_name="Test",
            last_name="User",
            user_type="U",
        )
        assert not result.success

    def test_empty_password(self) -> None:
        """Empty password fails."""
        result = create_user(
            username="nopass",
            password="",
            first_name="Test",
            last_name="User",
            user_type="U",
        )
        assert not result.success

    def test_empty_first_name(self) -> None:
        """Empty first name fails."""
        result = create_user(
            username="nofirst",
            password="pass1234",
            first_name="",
            last_name="User",
            user_type="U",
        )
        assert not result.success

    def test_empty_last_name(self) -> None:
        """Empty last name fails."""
        result = create_user(
            username="nolast",
            password="pass1234",
            first_name="Test",
            last_name="",
            user_type="U",
        )
        assert not result.success

    def test_invalid_user_type(self) -> None:
        """Invalid user type fails."""
        result = create_user(
            username="badtype",
            password="pass1234",
            first_name="Test",
            last_name="User",
            user_type="X",
        )
        assert not result.success


# ---------------------------------------------------------------------------
# Service tests — update_user
# ---------------------------------------------------------------------------


class TestUpdateUser(TestCase):
    """Tests for update_user service function."""

    def setUp(self) -> None:
        """Create synthetic user to update."""
        self.user = User.objects.create_user(
            username="updateme",
            password="pass1234",
            first_name="Original",
            last_name="Name",
        )
        UserProfile.objects.create(
            user=self.user, user_type="U",
        )

    def test_update_name(self) -> None:
        """Update first and last name."""
        result = update_user(
            user_id=self.user.pk,
            first_name="Updated",
            last_name="Username",
            user_type="U",
        )
        assert result.success
        self.user.refresh_from_db()
        assert self.user.first_name == "Updated"

    def test_update_to_admin(self) -> None:
        """Change user type to admin."""
        result = update_user(
            user_id=self.user.pk,
            first_name="Original",
            last_name="Name",
            user_type="A",
        )
        assert result.success
        self.user.refresh_from_db()
        assert self.user.is_staff

    def test_update_password(self) -> None:
        """Update password when provided."""
        result = update_user(
            user_id=self.user.pk,
            first_name="Original",
            last_name="Name",
            user_type="U",
            new_password="newpass1",
        )
        assert result.success
        self.user.refresh_from_db()
        assert self.user.check_password("newpass1")

    def test_no_password_change(self) -> None:
        """Empty password field keeps current password."""
        result = update_user(
            user_id=self.user.pk,
            first_name="Original",
            last_name="Name",
            user_type="U",
            new_password="",
        )
        assert result.success
        self.user.refresh_from_db()
        assert self.user.check_password("pass1234")

    def test_user_not_found(self) -> None:
        """Non-existent user ID returns error."""
        result = update_user(
            user_id=99999,
            first_name="Test",
            last_name="User",
            user_type="U",
        )
        assert not result.success
        assert "not found" in result.message.lower()

    def test_empty_first_name(self) -> None:
        """Empty first name fails."""
        result = update_user(
            user_id=self.user.pk,
            first_name="",
            last_name="Name",
            user_type="U",
        )
        assert not result.success

    def test_invalid_type(self) -> None:
        """Invalid user type fails."""
        result = update_user(
            user_id=self.user.pk,
            first_name="Test",
            last_name="User",
            user_type="X",
        )
        assert not result.success


# ---------------------------------------------------------------------------
# Service tests — delete_user
# ---------------------------------------------------------------------------


class TestDeleteUser(TestCase):
    """Tests for delete_user service function."""

    def test_successful_delete(self) -> None:
        """User is deleted successfully."""
        user = User.objects.create_user(
            username="deleteme", password="pass1234",
        )
        result = delete_user(user_id=user.pk)
        assert result.success
        assert not User.objects.filter(pk=user.pk).exists()

    def test_delete_not_found(self) -> None:
        """Non-existent user returns error."""
        result = delete_user(user_id=99999)
        assert not result.success

    def test_cascades_to_profile(self) -> None:
        """Profile is deleted when user is deleted."""
        user = User.objects.create_user(
            username="cascademe", password="pass1234",
        )
        UserProfile.objects.create(
            user=user, user_type="U",
        )
        delete_user(user_id=user.pk)
        assert UserProfile.objects.count() == 0


# ---------------------------------------------------------------------------
# Form tests
# ---------------------------------------------------------------------------


class TestUserFilterForm(TestCase):
    """Tests for UserFilterForm."""

    def test_valid_form(self) -> None:
        """Form with search term is valid."""
        form = UserFilterForm(data={"search": "john"})
        assert form.is_valid()

    def test_empty_form(self) -> None:
        """Empty form is valid (optional field)."""
        form = UserFilterForm(data={})
        assert form.is_valid()


class TestUserCreateForm(TestCase):
    """Tests for UserCreateForm."""

    def test_valid_form(self) -> None:
        """Form with all fields is valid."""
        form = UserCreateForm(data={
            "username": "newuser",
            "password": "pass1234",
            "first_name": "New",
            "last_name": "User",
            "user_type": "U",
        })
        assert form.is_valid()

    def test_missing_username(self) -> None:
        """Missing username is invalid."""
        form = UserCreateForm(data={
            "password": "pass1234",
            "first_name": "New",
            "last_name": "User",
            "user_type": "U",
        })
        assert not form.is_valid()

    def test_username_too_long(self) -> None:
        """Username > 8 chars is invalid."""
        form = UserCreateForm(data={
            "username": "toolongusername",
            "password": "pass1234",
            "first_name": "New",
            "last_name": "User",
            "user_type": "U",
        })
        assert not form.is_valid()


class TestUserUpdateForm(TestCase):
    """Tests for UserUpdateForm."""

    def test_valid_form(self) -> None:
        """Form with required fields is valid."""
        form = UserUpdateForm(data={
            "first_name": "Updated",
            "last_name": "Name",
            "user_type": "U",
        })
        assert form.is_valid()

    def test_password_optional(self) -> None:
        """Password field is optional."""
        form = UserUpdateForm(data={
            "first_name": "Updated",
            "last_name": "Name",
            "user_type": "A",
            "new_password": "",
        })
        assert form.is_valid()


# ---------------------------------------------------------------------------
# View tests
# ---------------------------------------------------------------------------


class TestUserListView(TestCase):
    """Tests for UserListView."""

    def setUp(self) -> None:
        """Create admin test user."""
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin",
            password="testpass123",
            is_staff=True,
        )
        self.client.login(
            username="admin", password="testpass123",
        )

    def test_admin_access(self) -> None:
        """Admin can access user list."""
        response = self.client.get("/users/")
        assert response.status_code == 200

    def test_non_admin_redirected(self) -> None:
        """Non-admin user is denied access."""
        self.client.logout()
        User.objects.create_user(
            username="regular", password="testpass123",
        )
        self.client.login(
            username="regular", password="testpass123",
        )
        response = self.client.get("/users/")
        assert response.status_code == 403

    def test_unauthenticated_redirected(self) -> None:
        """Unauthenticated user is redirected."""
        self.client.logout()
        response = self.client.get("/users/")
        assert response.status_code == 302

    def test_template_used(self) -> None:
        """Correct template is used."""
        response = self.client.get("/users/")
        self.assertTemplateUsed(
            response, "user_admin/user_list.html",
        )

    def test_search_filter(self) -> None:
        """Search parameter is applied."""
        response = self.client.get("/users/?search=admin")
        assert response.status_code == 200


class TestUserCreateView(TestCase):
    """Tests for UserCreateView."""

    def setUp(self) -> None:
        """Create admin test user."""
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin",
            password="testpass123",
            is_staff=True,
        )
        self.client.login(
            username="admin", password="testpass123",
        )

    def test_get_form(self) -> None:
        """Create form loads."""
        response = self.client.get("/users/create/")
        assert response.status_code == 200

    def test_post_success(self) -> None:
        """Valid submission creates user."""
        response = self.client.post("/users/create/", {
            "username": "newuser",
            "password": "pass1234",
            "first_name": "New",
            "last_name": "User",
            "user_type": "U",
        })
        assert response.status_code == 302
        assert User.objects.filter(username="newuser").exists()

    def test_post_duplicate(self) -> None:
        """Duplicate username re-renders form."""
        response = self.client.post("/users/create/", {
            "username": "admin",
            "password": "pass1234",
            "first_name": "Dup",
            "last_name": "User",
            "user_type": "U",
        })
        assert response.status_code == 200

    def test_non_admin_denied(self) -> None:
        """Non-admin cannot create users."""
        self.client.logout()
        User.objects.create_user(
            username="regular", password="testpass123",
        )
        self.client.login(
            username="regular", password="testpass123",
        )
        response = self.client.get("/users/create/")
        assert response.status_code == 403


class TestUserUpdateView(TestCase):
    """Tests for UserUpdateView."""

    def setUp(self) -> None:
        """Create admin and target user."""
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin",
            password="testpass123",
            is_staff=True,
        )
        self.target = User.objects.create_user(
            username="target",
            password="pass1234",
            first_name="Original",
            last_name="Name",
        )
        UserProfile.objects.create(
            user=self.target, user_type="U",
        )
        self.client.login(
            username="admin", password="testpass123",
        )

    def test_get_form(self) -> None:
        """Update form loads with current values."""
        response = self.client.get(
            f"/users/{self.target.pk}/update/"
        )
        assert response.status_code == 200

    def test_post_success(self) -> None:
        """Valid update redirects to list."""
        response = self.client.post(
            f"/users/{self.target.pk}/update/",
            {
                "first_name": "Updated",
                "last_name": "Name",
                "user_type": "U",
            },
        )
        assert response.status_code == 302

    def test_not_found(self) -> None:
        """Non-existent user returns 404."""
        response = self.client.get("/users/99999/update/")
        assert response.status_code == 404


class TestUserDeleteView(TestCase):
    """Tests for UserDeleteView."""

    def setUp(self) -> None:
        """Create admin and target user."""
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin",
            password="testpass123",
            is_staff=True,
        )
        self.target = User.objects.create_user(
            username="target", password="pass1234",
        )
        self.client.login(
            username="admin", password="testpass123",
        )

    def test_get_confirmation(self) -> None:
        """Delete confirmation page loads."""
        response = self.client.get(
            f"/users/{self.target.pk}/delete/"
        )
        assert response.status_code == 200

    def test_post_delete(self) -> None:
        """POST deletes user and redirects."""
        response = self.client.post(
            f"/users/{self.target.pk}/delete/"
        )
        assert response.status_code == 302
        assert not User.objects.filter(pk=self.target.pk).exists()

    def test_cannot_delete_self(self) -> None:
        """Admin cannot delete own account."""
        response = self.client.post(
            f"/users/{self.admin.pk}/delete/"
        )
        assert response.status_code == 302
        assert User.objects.filter(pk=self.admin.pk).exists()

    def test_non_admin_denied(self) -> None:
        """Non-admin cannot delete users."""
        self.client.logout()
        User.objects.create_user(
            username="regular", password="testpass123",
        )
        self.client.login(
            username="regular", password="testpass123",
        )
        response = self.client.post(
            f"/users/{self.target.pk}/delete/"
        )
        assert response.status_code == 403
