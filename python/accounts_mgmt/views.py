"""
Django views for account management.

Translated from COBOL programs:
- COACTVWC.cbl — Account View (read-only detail display)
- COACTUPC.cbl — Account Update (edit form with validation)

Views handle HTTP only — validation lives in forms.py,
business logic lives in services.py (SRP).
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from accounts_mgmt.forms import AccountSearchForm, AccountUpdateForm
from accounts_mgmt.services import (
    apply_account_updates,
    lookup_account_with_customer,
)


@login_required
def account_search(request: HttpRequest) -> HttpResponse:
    """Display the account search form and process lookups.

    Translated from 0000-MAIN in COACTVWC.cbl.
    Handles the initial search screen where the user enters
    an account ID to view or update.

    Args:
        request: The HTTP request.

    Returns:
        Rendered search page or redirect to detail/update view.
    """
    form = AccountSearchForm(request.GET or None)
    context: dict = {"form": form}

    if request.GET and form.is_valid():
        acct_id = form.cleaned_data["acct_id"]
        account, customer, error = lookup_account_with_customer(acct_id)
        if error:
            messages.error(request, error)
        else:
            context["account"] = account
            context["customer"] = customer
    return render(request, "accounts_mgmt/account_search.html", context)


@login_required
def account_detail(request: HttpRequest, acct_id: str) -> HttpResponse:
    """Display read-only account and customer details.

    Translated from COACTVWC.cbl:
    - 1200-SETUP-SCREEN-VARS: populates all display fields
    - 9000-READ-ACCT: reads account → card xref → customer

    The COBOL program displays account info (status, limits, balances,
    dates) and linked customer info (name, address, SSN, phone, FICO).

    Args:
        request: The HTTP request.
        acct_id: The 11-digit account identifier.

    Returns:
        Rendered read-only account detail page.
    """
    account, customer, error = lookup_account_with_customer(acct_id)
    if error:
        messages.error(request, error)
        return redirect("accounts_mgmt:account_search")

    context = {
        "account": account,
        "customer": customer,
    }
    return render(request, "accounts_mgmt/account_detail.html", context)


def _build_initial_data(account, customer) -> dict:
    """Build initial form data from account and customer records.

    Translated from 3202-SHOW-ORIGINAL-VALUES in COACTUPC.cbl.
    Populates the update form with current database values.

    Args:
        account:  Account model instance.
        customer: Customer model instance.

    Returns:
        Dictionary of form field initial values.
    """
    # Parse phone numbers from (NPA)NXX-XXXX format
    phone1 = _parse_phone(customer.cust_phone_num_1 if customer else "")
    phone2 = _parse_phone(customer.cust_phone_num_2 if customer else "")

    return {
        "acct_active_status": account.acct_active_status,
        "acct_credit_limit": str(account.acct_credit_limit),
        "acct_cash_credit_limit": str(account.acct_cash_credit_limit),
        "acct_curr_bal": str(account.acct_curr_bal),
        "acct_curr_cyc_credit": str(account.acct_curr_cyc_credit),
        "acct_curr_cyc_debit": str(account.acct_curr_cyc_debit),
        "acct_open_date": account.acct_open_date,
        "acct_expiration_date": account.acct_expiration_date,
        "acct_reissue_date": account.acct_reissue_date,
        "acct_group_id": account.acct_group_id,
        "cust_first_name": customer.cust_first_name if customer else "",
        "cust_middle_name": customer.cust_middle_name if customer else "",
        "cust_last_name": customer.cust_last_name if customer else "",
        "cust_addr_line_1": customer.cust_addr_line_1 if customer else "",
        "cust_addr_line_2": customer.cust_addr_line_2 if customer else "",
        "cust_addr_line_3": customer.cust_addr_line_3 if customer else "",
        "cust_addr_state_cd": customer.cust_addr_state_cd if customer else "",
        "cust_addr_country_cd": customer.cust_addr_country_cd if customer else "",
        "cust_addr_zip": customer.cust_addr_zip if customer else "",
        "cust_phone_num_1_area": phone1[0],
        "cust_phone_num_1_prefix": phone1[1],
        "cust_phone_num_1_line": phone1[2],
        "cust_phone_num_2_area": phone2[0],
        "cust_phone_num_2_prefix": phone2[1],
        "cust_phone_num_2_line": phone2[2],
        "cust_ssn": customer.cust_ssn if customer else "",
        "cust_govt_issued_id": customer.cust_govt_issued_id if customer else "",
        "cust_dob": customer.cust_dob_yyyy_mm_dd if customer else "",
        "cust_eft_account_id": customer.cust_eft_account_id if customer else "",
        "cust_pri_card_holder_ind": customer.cust_pri_card_holder_ind if customer else "",
        "cust_fico_credit_score": customer.cust_fico_credit_score if customer else "",
    }


def _parse_phone(phone_str: str) -> tuple[str, str, str]:
    """Parse a phone string in ``(NPA)NXX-XXXX`` format into parts.

    Translated from COACTUPC.cbl phone field layout:
    ``ACUP-OLD-CUST-PHONE-NUM-1-X`` with sub-fields for area,
    prefix, and line number.

    Args:
        phone_str: Phone string in (NPA)NXX-XXXX format.

    Returns:
        Tuple of (area_code, prefix, line_number).
    """
    if not phone_str or len(phone_str.strip()) < 10:
        return ("", "", "")
    cleaned = phone_str.strip()
    # Expected format: (NPA)NXX-XXXX
    if cleaned.startswith("(") and ")" in cleaned:
        area = cleaned[1 : cleaned.index(")")]
        rest = cleaned[cleaned.index(")") + 1 :]
        if "-" in rest:
            prefix, line = rest.split("-", 1)
            return (area.strip(), prefix.strip(), line.strip())
    return ("", "", "")


@login_required
def account_update(request: HttpRequest, acct_id: str) -> HttpResponse:
    """Display and process the account update form.

    Translated from COACTUPC.cbl:
    - 0000-MAIN              — main processing flow
    - 1000-PROCESS-INPUTS    — receive and validate form data
    - 2000-DECIDE-ACTION     — determine next action based on state
    - 9600-WRITE-PROCESSING  — apply updates to database

    The COBOL program uses a multi-step flow:
    1. Display current values (ACUP-SHOW-DETAILS)
    2. User makes changes → validate (ACUP-CHANGES-NOT-OK / OK)
    3. Confirm save (ACUP-CHANGES-OK-NOT-CONFIRMED)
    4. Execute update (ACUP-CHANGES-OKAYED-AND-DONE)

    In Django we simplify to: display form → validate → save.

    Args:
        request: The HTTP request.
        acct_id: The 11-digit account identifier.

    Returns:
        Rendered update form or redirect on success.
    """
    account, customer, error = lookup_account_with_customer(acct_id)
    if error:
        messages.error(request, error)
        return redirect("accounts_mgmt:account_search")

    if request.method == "POST":
        form = AccountUpdateForm(request.POST)
        if form.is_valid():
            result = apply_account_updates(
                account, customer, form.cleaned_data,
            )
            if result.success:
                messages.success(request, "Changes committed to database.")
                return redirect(
                    "accounts_mgmt:account_detail", acct_id=acct_id,
                )
            messages.error(request, result.error_message)
    else:
        initial = _build_initial_data(account, customer)
        form = AccountUpdateForm(initial=initial)

    context = {
        "form": form,
        "account": account,
        "customer": customer,
    }
    return render(request, "accounts_mgmt/account_update.html", context)
