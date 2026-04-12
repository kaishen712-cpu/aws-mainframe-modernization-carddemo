"""
Django views for Transaction Management.

Translated from COBOL programs:
- COTRN00C.cbl → TransactionListView (list with pagination)
- COTRN01C.cbl → TransactionDetailView (detail view)
- COTRN02C.cbl → TransactionCreateView (add transaction)
- COBIL00C.cbl → BillPaymentView (bill payment)

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

from python.transactions.forms import (
    BillPaymentForm,
    TransactionCreateForm,
    TransactionFilterForm,
)
from python.transactions.models import Transaction
from python.transactions.services import (
    TransactionInput,
    add_transaction,
    get_transaction_list,
    process_bill_payment,
)


class TransactionListView(LoginRequiredMixin, ListView):
    """List transactions with pagination and filtering.

    Translated from COTRN00C.cbl — PROCESS-PAGE-FORWARD / BACKWARD.

    The original COBOL program uses CICS STARTBR/READNEXT to browse
    the TRANSACT VSAM file. This Django view replaces that pattern
    with queryset pagination.

    Business rules:
    - Filter by card number, account ID, or transaction type.
    - Results ordered by transaction ID descending.
    - PF7/PF8 map to previous/next page.
    """

    model = Transaction
    template_name = "transactions/transaction_list.html"
    context_object_name = "transactions"
    paginate_by = getattr(settings, "TRANSACTIONS_PER_PAGE", 10)

    def get_queryset(self) -> list[Transaction]:
        """Build filtered queryset.

        Translated from COTRN00C.cbl — 2000-RECEIVE-MAP.
        """
        self.filter_form = TransactionFilterForm(self.request.GET)
        card_num = ""
        acct_id = ""
        tran_type_cd = ""

        if self.filter_form.is_valid():
            card_num = self.filter_form.cleaned_data.get(
                "card_num", ""
            )
            acct_id = self.filter_form.cleaned_data.get(
                "acct_id", ""
            )
            tran_type_cd = self.filter_form.cleaned_data.get(
                "tran_type_cd", ""
            )

        return get_transaction_list(
            card_num=card_num,
            acct_id=acct_id,
            tran_type_cd=tran_type_cd,
        )

    def get_context_data(self, **kwargs: object) -> dict:
        """Add filter form and header info to context."""
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.filter_form
        context["program_name"] = "COTRN00C"
        context["transaction_id"] = "CT00"
        return context


class TransactionDetailView(LoginRequiredMixin, DetailView):
    """Display transaction details (read-only).

    Translated from COTRN01C.cbl — 9000-READ-DATA / 1000-SEND-MAP.

    Business rules:
    - Transaction looked up by tran_id.
    - All fields displayed read-only.
    - PF3 returns to list.
    """

    model = Transaction
    template_name = "transactions/transaction_detail.html"
    context_object_name = "transaction"

    def get_object(self, queryset=None):  # type: ignore[override]
        """Look up transaction by tran_id from URL.

        Translated from COTRN01C.cbl — 9000-READ-DATA.
        """
        tran_id = self.kwargs["tran_id"]
        return get_object_or_404(Transaction, tran_id=tran_id)

    def get_context_data(self, **kwargs: object) -> dict:
        """Add header info to context."""
        context = super().get_context_data(**kwargs)
        context["program_name"] = "COTRN01C"
        context["transaction_id"] = "CT01"
        return context


class TransactionCreateView(LoginRequiredMixin, View):
    """Add a new transaction.

    Translated from COTRN02C.cbl — full add workflow.

    Business rules (from COTRN02C.cbl):
    - GET: Display empty transaction form.
    - POST: Validate all fields, require confirmation, write record.
    - Key fields: account ID or card number (cross-reference lookup).
    - Data fields: type, category, source, desc, amount, dates, merchant.
    - Confirmation step: user must enter Y to confirm.
    """

    template_name = "transactions/transaction_create.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        """Display empty transaction form.

        Translated from COTRN02C.cbl — INITIALIZE-ALL-FIELDS.
        """
        form = TransactionCreateForm()
        return render(request, self.template_name, {
            "form": form,
            "program_name": "COTRN02C",
            "transaction_id": "CT02",
        })

    def post(self, request: HttpRequest) -> HttpResponse:
        """Process transaction add submission.

        Translated from COTRN02C.cbl — PROCESS-ENTER-KEY.
        """
        form = TransactionCreateForm(request.POST)

        if not form.is_valid():
            return render(request, self.template_name, {
                "form": form,
                "program_name": "COTRN02C",
                "transaction_id": "CT02",
            })

        txn_input = TransactionInput(
            acct_id=form.cleaned_data.get("acct_id", ""),
            card_num=form.cleaned_data.get("card_num", ""),
            tran_type_cd=form.cleaned_data["tran_type_cd"],
            tran_cat_cd=form.cleaned_data["tran_cat_cd"],
            tran_source=form.cleaned_data["tran_source"],
            tran_desc=form.cleaned_data["tran_desc"],
            tran_amt=form.cleaned_data["tran_amt"],
            orig_date=form.cleaned_data["orig_date"],
            proc_date=form.cleaned_data["proc_date"],
            merchant_id=form.cleaned_data["merchant_id"],
            merchant_name=form.cleaned_data["merchant_name"],
            merchant_city=form.cleaned_data["merchant_city"],
            merchant_zip=form.cleaned_data["merchant_zip"],
            confirm=form.cleaned_data.get("confirm", "N"),
        )

        result = add_transaction(txn_input)

        if result.success:
            messages.success(request, result.message)
            return redirect("transactions:transaction_list")

        messages.error(request, result.message)
        return render(request, self.template_name, {
            "form": form,
            "program_name": "COTRN02C",
            "transaction_id": "CT02",
        })


class BillPaymentView(LoginRequiredMixin, View):
    """Process bill payments.

    Translated from COBIL00C.cbl — PROCESS-BILL-PAYMENT.

    Business rules:
    - Account ID and card number required.
    - Payment amount must be positive.
    - Card must belong to the account.
    - Creates bill payment transaction and updates balance.
    """

    template_name = "transactions/bill_payment.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        """Display bill payment form.

        Translated from COBIL00C.cbl — initial screen display.
        """
        form = BillPaymentForm()
        return render(request, self.template_name, {
            "form": form,
            "program_name": "COBIL00C",
            "transaction_id": "BP00",
        })

    def post(self, request: HttpRequest) -> HttpResponse:
        """Process bill payment submission.

        Translated from COBIL00C.cbl — PROCESS-BILL-PAYMENT.
        """
        form = BillPaymentForm(request.POST)

        if not form.is_valid():
            return render(request, self.template_name, {
                "form": form,
                "program_name": "COBIL00C",
                "transaction_id": "BP00",
            })

        result = process_bill_payment(
            acct_id=form.cleaned_data["acct_id"],
            card_num=form.cleaned_data["card_num"],
            payment_amount=form.cleaned_data["payment_amount"],
        )

        if result.success:
            messages.success(request, result.message)
            return redirect("transactions:transaction_list")

        messages.error(request, result.message)
        return render(request, self.template_name, {
            "form": form,
            "program_name": "COBIL00C",
            "transaction_id": "BP00",
        })
