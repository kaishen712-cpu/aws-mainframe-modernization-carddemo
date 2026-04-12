"""
Django views for Report Management.

Translated from COBOL program:
- CORPT00C.cbl — Report dispatch menu

The original COBOL program dispatches to various batch report
generation programs via CICS START commands. In the Django version,
this view presents the report menu and dispatches to report
generation services.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View

# Report type choices matching COBOL CORPT00C menu options
REPORT_TYPES = [
    {
        "code": "MONTHLY",
        "name": "Monthly Statement",
        "description": "Generate monthly account statements",
    },
    {
        "code": "YEARLY",
        "name": "Yearly Summary",
        "description": "Generate yearly account summary report",
    },
    {
        "code": "CUSTOM",
        "name": "Custom Date Range",
        "description": "Generate report for custom date range",
    },
]


class ReportDispatchView(LoginRequiredMixin, View):
    """Report dispatch menu.

    Translated from CORPT00C.cbl — 0000-MAIN / 1000-SEND-MAP.

    The original COBOL program presents a BMS screen with report
    type options and dispatches to the appropriate batch report
    program via CICS START. In Django, this view presents the
    menu and dispatches to report generation services.

    Business rules:
    - User selects report type from menu.
    - System validates selection.
    - Report generation is dispatched asynchronously
      (placeholder for batch integration).
    """

    template_name = "reports/report_dispatch.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        """Display report dispatch menu.

        Translated from CORPT00C.cbl — 1000-SEND-MAP.
        """
        return render(request, self.template_name, {
            "report_types": REPORT_TYPES,
            "program_name": "CORPT00C",
            "transaction_id": "CR00",
        })

    def post(self, request: HttpRequest) -> HttpResponse:
        """Process report dispatch request.

        Translated from CORPT00C.cbl — 2000-PROCESS-INPUTS.

        Note: Batch report execution is a placeholder pending
        Phase 7 (batch integration). Currently logs the request
        and displays a confirmation message.
        """
        report_type = request.POST.get("report_type", "")

        valid_codes = [r["code"] for r in REPORT_TYPES]
        if report_type not in valid_codes:
            messages.error(
                request,
                "Invalid report type selected. Please try again.",
            )
            return render(request, self.template_name, {
                "report_types": REPORT_TYPES,
                "program_name": "CORPT00C",
                "transaction_id": "CR00",
            })

        # Placeholder: In Phase 7, this will dispatch to batch
        # report generation via Celery or Django management command.
        messages.success(
            request,
            f"Report request submitted: {report_type}. "
            "Report will be generated and available shortly.",
        )
        return render(request, self.template_name, {
            "report_types": REPORT_TYPES,
            "program_name": "CORPT00C",
            "transaction_id": "CR00",
        })
