"""URL configuration for the transactions app."""

from __future__ import annotations

from django.urls import path

from python.transactions import views

app_name = "transactions"

urlpatterns = [
    path(
        "",
        views.TransactionListView.as_view(),
        name="transaction_list",
    ),
    path(
        "add/",
        views.TransactionCreateView.as_view(),
        name="transaction_create",
    ),
    path(
        "billpay/",
        views.BillPaymentView.as_view(),
        name="bill_payment",
    ),
    path(
        "<str:tran_id>/",
        views.TransactionDetailView.as_view(),
        name="transaction_detail",
    ),
]
