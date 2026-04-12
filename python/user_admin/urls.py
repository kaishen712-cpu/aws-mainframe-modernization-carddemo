"""URL configuration for the user_admin app."""

from __future__ import annotations

from django.urls import path

from python.user_admin import views

app_name = "user_admin"

urlpatterns = [
    path("", views.UserListView.as_view(), name="user_list"),
    path(
        "create/",
        views.UserCreateView.as_view(),
        name="user_create",
    ),
    path(
        "<int:pk>/update/",
        views.UserUpdateView.as_view(),
        name="user_update",
    ),
    path(
        "<int:pk>/delete/",
        views.UserDeleteView.as_view(),
        name="user_delete",
    ),
]
