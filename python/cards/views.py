"""
Django views for Credit Card Management.

Translated from COBOL programs:
- COCRDLIC.cbl → CardListView (list with pagination)
- COCRDSLC.cbl → CardDetailView (view/select)
- COCRDUPC.cbl → CardUpdateView (update)

Views handle HTTP only; business logic delegated to services.py.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView, ListView

from python.cards.forms import CardFilterForm, CardUpdateForm
from python.cards.models import Card
from python.cards.services import (
    get_card_list,
    update_card,
)


class CardListView(LoginRequiredMixin, ListView):
    """List credit cards with pagination and filtering.

    Translated from COCRDLIC.cbl — PROCESS-PAGE-FORWARD / BACKWARD.

    The original COBOL program uses CICS STARTBR/READNEXT to browse
    the CARDDAT VSAM file with a 7-row screen buffer. This Django
    view replaces that pattern with queryset pagination.

    Business rules:
    - Admin users see all cards (no account filter required).
    - Regular users only see cards for their associated account.
    - Supports filtering by account ID and card number prefix.
    - Selection column: 'S' for detail view, 'U' for update.
    """

    model = Card
    template_name = "cards/card_list.html"
    context_object_name = "cards"
    paginate_by = getattr(settings, "CARDS_PER_PAGE", 10)

    def get_queryset(self) -> list[Card]:
        """Build filtered queryset from form inputs.

        Translated from COCRDLIC.cbl — 2000-RECEIVE-MAP /
        9000-READ-DATA paragraphs.
        """
        self.filter_form = CardFilterForm(self.request.GET)
        acct_id = ""
        card_num_filter = ""

        if self.filter_form.is_valid():
            acct_id = self.filter_form.cleaned_data.get(
                "acct_id", ""
            )
            card_num_filter = self.filter_form.cleaned_data.get(
                "card_num", ""
            )

        is_admin = self.request.user.is_staff
        return get_card_list(
            acct_id=acct_id,
            card_num_filter=card_num_filter,
            is_admin=is_admin,
        )

    def get_context_data(self, **kwargs: object) -> dict:
        """Add filter form and header info to context.

        Translated from COCRDLIC.cbl — 1000-SEND-MAP.
        """
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.filter_form
        context["program_name"] = "COCRDLIC"
        context["transaction_id"] = "CCLI"
        return context


class CardDetailView(LoginRequiredMixin, DetailView):
    """Display credit card details (read-only).

    Translated from COCRDSLC.cbl — 9000-READ-DATA / 1000-SEND-MAP.

    Business rules:
    - Card looked up by account ID + card number.
    - Displays all card fields in read-only mode.
    - PF3 returns to card list (back navigation).
    """

    model = Card
    template_name = "cards/card_detail.html"
    context_object_name = "card"

    def get_object(self, queryset=None):  # type: ignore[override]
        """Look up card by card_num from URL.

        Translated from COCRDSLC.cbl — 9000-READ-DATA.
        """
        card_num = self.kwargs["card_num"]
        return get_object_or_404(Card, card_num=card_num)

    def get_context_data(self, **kwargs: object) -> dict:
        """Add header info to context."""
        context = super().get_context_data(**kwargs)
        context["program_name"] = "COCRDSLC"
        context["transaction_id"] = "CCDL"
        return context


class CardUpdateView(LoginRequiredMixin, View):
    """Update credit card details.

    Translated from COCRDUPC.cbl — full update workflow.

    Business rules (from COCRDUPC.cbl):
    - GET: Display current card details in editable form.
    - POST: Validate inputs, detect changes, update record.
    - Name must be alphabetic + spaces only.
    - Status must be Y or N.
    - Expiry month 1-12, year 1950-2099.
    - Detects "no change" scenario.
    - Confirmation step before final save (F5 in COBOL).
    """

    template_name = "cards/card_update.html"

    def get(
        self, request: HttpRequest, card_num: str,
    ) -> HttpResponse:
        """Display card update form with current values.

        Translated from COCRDUPC.cbl — CCUP-SHOW-DETAILS state.
        """
        card = get_object_or_404(Card, card_num=card_num)
        exp_parts = card.card_expiration_date.split("-")
        initial = {
            "card_name": card.card_embossed_name,
            "card_status": card.card_active_status,
            "expiry_month": exp_parts[1] if len(exp_parts) > 1
            else "",
            "expiry_year": exp_parts[0] if exp_parts else "",
        }
        form = CardUpdateForm(initial=initial)
        return render(request, self.template_name, {
            "form": form,
            "card": card,
            "program_name": "COCRDUPC",
            "transaction_id": "CCUP",
        })

    def post(
        self, request: HttpRequest, card_num: str,
    ) -> HttpResponse:
        """Process card update submission.

        Translated from COCRDUPC.cbl — 2000-PROCESS-INPUTS /
        9100-UPDATE-DATA paragraphs.
        """
        card = get_object_or_404(Card, card_num=card_num)
        form = CardUpdateForm(request.POST)

        if not form.is_valid():
            return render(request, self.template_name, {
                "form": form,
                "card": card,
                "program_name": "COCRDUPC",
                "transaction_id": "CCUP",
            })

        result = update_card(
            card_num=card_num,
            card_name=form.cleaned_data["card_name"],
            card_status=form.cleaned_data["card_status"],
            expiry_month=form.cleaned_data["expiry_month"],
            expiry_year=form.cleaned_data["expiry_year"],
        )

        if result.success:
            messages.success(request, result.message)
            return redirect("cards:card_detail", card_num=card_num)

        messages.error(request, result.message)
        return render(request, self.template_name, {
            "form": form,
            "card": card,
            "program_name": "COCRDUPC",
            "transaction_id": "CCUP",
        })
