"""URL configuration for the cards app."""

from __future__ import annotations

from django.urls import path

from python.cards import views

app_name = "cards"

urlpatterns = [
    path("", views.CardListView.as_view(), name="card_list"),
    path(
        "<str:card_num>/",
        views.CardDetailView.as_view(),
        name="card_detail",
    ),
    path(
        "<str:card_num>/update/",
        views.CardUpdateView.as_view(),
        name="card_update",
    ),
]
