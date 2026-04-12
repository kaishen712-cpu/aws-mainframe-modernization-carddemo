"""URL configuration for the reports app."""

from __future__ import annotations

from django.urls import path

from python.reports import views

app_name = "reports"

urlpatterns = [
    path(
        "",
        views.ReportDispatchView.as_view(),
        name="report_dispatch",
    ),
]
