"""
Django views for User Administration.

Translated from COBOL programs:
- COUSR00C.cbl → UserListView (list with pagination)
- COUSR01C.cbl → UserCreateView (add user)
- COUSR02C.cbl → UserUpdateView (update user)
- COUSR03C.cbl → UserDeleteView (delete user)

All views restricted to admin users via @user_passes_test.
Views handle HTTP only; business logic delegated to services.py.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    UserPassesTestMixin,
)
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView

from python.user_admin.forms import (
    UserCreateForm,
    UserFilterForm,
    UserUpdateForm,
)
from python.user_admin.services import (
    create_user,
    delete_user,
    get_user_list,
    is_admin_user,
    update_user,
)


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin to restrict access to admin users only.

    Translated from COBOL SEC-USR-TYPE = 'A' check that gates
    access to user administration functions.
    """

    def test_func(self) -> bool:
        """Check if user has admin privileges."""
        return is_admin_user(self.request.user)


class UserListView(AdminRequiredMixin, ListView):
    """List users with pagination and search.

    Translated from COUSR00C.cbl — 0000-MAIN.

    The original COBOL program uses CICS STARTBR/READNEXT to
    browse the USRSEC VSAM file. This Django view replaces that
    with queryset pagination.

    Business rules:
    - Admin-only access.
    - Search by username or name.
    - Results ordered by username.
    """

    model = User
    template_name = "user_admin/user_list.html"
    context_object_name = "users"
    paginate_by = getattr(settings, "USERS_PER_PAGE", 10)

    def get_queryset(self) -> list[User]:
        """Build filtered queryset.

        Translated from COUSR00C.cbl — 2000-RECEIVE-MAP.
        """
        self.filter_form = UserFilterForm(self.request.GET)
        search_query = ""

        if self.filter_form.is_valid():
            search_query = self.filter_form.cleaned_data.get(
                "search", ""
            )

        return get_user_list(search_query=search_query)

    def get_context_data(self, **kwargs: object) -> dict:
        """Add filter form and header info to context."""
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.filter_form
        context["program_name"] = "COUSR00C"
        context["transaction_id"] = "CU00"
        return context


class UserCreateView(AdminRequiredMixin, View):
    """Create a new user.

    Translated from COUSR01C.cbl — full add workflow.

    Business rules:
    - Admin-only access.
    - Username must be unique.
    - All fields required.
    - User type: A (Admin) or U (Regular User).
    """

    template_name = "user_admin/user_create.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        """Display empty user creation form.

        Translated from COUSR01C.cbl — INITIALIZE-ALL-FIELDS.
        """
        form = UserCreateForm()
        return render(request, self.template_name, {
            "form": form,
            "program_name": "COUSR01C",
            "transaction_id": "CU01",
        })

    def post(self, request: HttpRequest) -> HttpResponse:
        """Process user creation.

        Translated from COUSR01C.cbl — ADD-USER.
        """
        form = UserCreateForm(request.POST)

        if not form.is_valid():
            return render(request, self.template_name, {
                "form": form,
                "program_name": "COUSR01C",
                "transaction_id": "CU01",
            })

        result = create_user(
            username=form.cleaned_data["username"],
            password=form.cleaned_data["password"],
            first_name=form.cleaned_data["first_name"],
            last_name=form.cleaned_data["last_name"],
            user_type=form.cleaned_data["user_type"],
        )

        if result.success:
            messages.success(request, result.message)
            return redirect("user_admin:user_list")

        messages.error(request, result.message)
        return render(request, self.template_name, {
            "form": form,
            "program_name": "COUSR01C",
            "transaction_id": "CU01",
        })


class UserUpdateView(AdminRequiredMixin, View):
    """Update an existing user.

    Translated from COUSR02C.cbl — full update workflow.

    Business rules:
    - Admin-only access.
    - Username cannot be changed.
    - Password optional (blank = keep current).
    - First/last names required.
    - User type: A or U.
    """

    template_name = "user_admin/user_update.html"

    def get(
        self, request: HttpRequest, pk: int,
    ) -> HttpResponse:
        """Display user update form with current values.

        Translated from COUSR02C.cbl — show current data.
        """
        target_user = get_object_or_404(User, pk=pk)
        profile = getattr(
            target_user, "carddemo_profile", None,
        )
        user_type = profile.user_type if profile else "U"

        initial = {
            "first_name": target_user.first_name,
            "last_name": target_user.last_name,
            "user_type": user_type,
        }
        form = UserUpdateForm(initial=initial)
        return render(request, self.template_name, {
            "form": form,
            "target_user": target_user,
            "program_name": "COUSR02C",
            "transaction_id": "CU02",
        })

    def post(
        self, request: HttpRequest, pk: int,
    ) -> HttpResponse:
        """Process user update.

        Translated from COUSR02C.cbl — UPDATE-USER.
        """
        target_user = get_object_or_404(User, pk=pk)
        form = UserUpdateForm(request.POST)

        if not form.is_valid():
            return render(request, self.template_name, {
                "form": form,
                "target_user": target_user,
                "program_name": "COUSR02C",
                "transaction_id": "CU02",
            })

        result = update_user(
            user_id=pk,
            first_name=form.cleaned_data["first_name"],
            last_name=form.cleaned_data["last_name"],
            user_type=form.cleaned_data["user_type"],
            new_password=form.cleaned_data.get(
                "new_password", "",
            ),
        )

        if result.success:
            messages.success(request, result.message)
            return redirect("user_admin:user_list")

        messages.error(request, result.message)
        return render(request, self.template_name, {
            "form": form,
            "target_user": target_user,
            "program_name": "COUSR02C",
            "transaction_id": "CU02",
        })


class UserDeleteView(AdminRequiredMixin, View):
    """Delete a user with confirmation.

    Translated from COUSR03C.cbl — DELETE-USER.

    Business rules:
    - Admin-only access.
    - GET: Display confirmation page.
    - POST: Execute deletion.
    - Cannot delete self.
    """

    template_name = "user_admin/user_delete.html"

    def get(
        self, request: HttpRequest, pk: int,
    ) -> HttpResponse:
        """Display delete confirmation page.

        Translated from COUSR03C.cbl — confirm screen.
        """
        target_user = get_object_or_404(User, pk=pk)
        return render(request, self.template_name, {
            "target_user": target_user,
            "program_name": "COUSR03C",
            "transaction_id": "CU03",
        })

    def post(
        self, request: HttpRequest, pk: int,
    ) -> HttpResponse:
        """Process user deletion.

        Translated from COUSR03C.cbl — DELETE-USER.
        """
        if request.user.pk == pk:
            messages.error(
                request, "Cannot delete your own account.",
            )
            return redirect("user_admin:user_list")

        result = delete_user(user_id=pk)

        if result.success:
            messages.success(request, result.message)
        else:
            messages.error(request, result.message)

        return redirect("user_admin:user_list")
