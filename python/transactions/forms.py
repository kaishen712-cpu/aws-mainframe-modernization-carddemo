"""
Django forms for Transaction Management.

Translated from COBOL BMS map definitions:
- COTRN0A (transaction list filter)
- COTRN1A (transaction detail)
- COTRN2A (transaction add)
- COBIL0A (bill payment)
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django import forms


class TransactionFilterForm(forms.Form):
    """Filter form for the transaction list view.

    Translated from COTRN00C.cbl — 2000-RECEIVE-MAP.
    """

    card_num = forms.CharField(
        max_length=16,
        required=False,
        label="Card Number",
        widget=forms.TextInput(
            attrs={"placeholder": "16-digit Card Number"}
        ),
    )
    acct_id = forms.CharField(
        max_length=11,
        required=False,
        label="Account ID",
        widget=forms.TextInput(
            attrs={"placeholder": "11-digit Account ID"}
        ),
    )
    tran_type_cd = forms.CharField(
        max_length=2,
        required=False,
        label="Type Code",
        widget=forms.TextInput(
            attrs={"placeholder": "Type code"}
        ),
    )


class TransactionCreateForm(forms.Form):
    """Form for adding a new transaction.

    Translated from COTRN02C.cbl — COTRN2AI BMS map.
    All validation rules preserved from the original COBOL.
    """

    acct_id = forms.CharField(
        max_length=11,
        required=False,
        label="Account ID",
    )
    card_num = forms.CharField(
        max_length=16,
        required=False,
        label="Card Number",
    )
    tran_type_cd = forms.CharField(
        max_length=2,
        label="Type Code",
        help_text="Numeric transaction type code",
    )
    tran_cat_cd = forms.CharField(
        max_length=4,
        label="Category Code",
        help_text="Numeric category code",
    )
    tran_source = forms.CharField(
        max_length=10,
        label="Source",
    )
    tran_desc = forms.CharField(
        max_length=100,
        label="Description",
    )
    tran_amt = forms.CharField(
        max_length=12,
        label="Amount",
        help_text="Format: +/-99999999.99",
    )
    orig_date = forms.CharField(
        max_length=10,
        label="Origination Date",
        help_text="YYYY-MM-DD",
    )
    proc_date = forms.CharField(
        max_length=10,
        label="Processing Date",
        help_text="YYYY-MM-DD",
    )
    merchant_id = forms.CharField(
        max_length=9,
        label="Merchant ID",
        help_text="Numeric",
    )
    merchant_name = forms.CharField(
        max_length=50,
        label="Merchant Name",
    )
    merchant_city = forms.CharField(
        max_length=50,
        label="Merchant City",
    )
    merchant_zip = forms.CharField(
        max_length=10,
        label="Merchant Zip",
    )
    confirm = forms.CharField(
        max_length=1,
        required=False,
        label="Confirm (Y/N)",
        initial="N",
    )


class BillPaymentForm(forms.Form):
    """Form for bill payment.

    Translated from COBIL00C.cbl — COBIL0AI BMS map.

    Business rules:
    - Account ID and card number required.
    - Payment amount must be positive decimal.
    """

    acct_id = forms.CharField(
        max_length=11,
        label="Account ID",
        help_text="11-digit Account ID",
    )
    card_num = forms.CharField(
        max_length=16,
        label="Card Number",
        help_text="16-digit Card Number",
    )
    payment_amount = forms.CharField(
        max_length=12,
        label="Payment Amount",
        help_text="Positive decimal amount",
    )

    def clean_payment_amount(self) -> str:
        """Validate payment amount is positive decimal."""
        amount = self.cleaned_data["payment_amount"]
        try:
            amt = Decimal(amount)
            if amt <= 0:
                raise forms.ValidationError(
                    "Payment amount must be positive..."
                )
        except InvalidOperation:
            raise forms.ValidationError(
                "Payment amount must be a valid number..."
            )
        return amount
