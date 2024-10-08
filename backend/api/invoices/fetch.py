from django.db.models import When, CharField, F
from django.db.models.expressions import Case, Value
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from backend.decorators import web_require_scopes
from backend.models import Invoice
from backend.types.htmx import HtmxHttpRequest
from backend.service.invoices.common.fetch import get_context


@require_http_methods(["GET"])
@web_require_scopes("invoices:read", True, True)
def fetch_all_invoices(request: HtmxHttpRequest):
    # Redirect if not an HTMX request
    if not request.htmx:
        return redirect("invoices:single:dashboard")

    if request.user.logged_in_as_team:
        invoices = Invoice.objects.filter(organization=request.user.logged_in_as_team)
    else:
        invoices = Invoice.objects.filter(user=request.user)

    # Get filter and sort parameters from the request
    sort_by = request.GET.get("sort")
    sort_direction = request.GET.get("sort_direction", "")
    action_filter_type = request.GET.get("filter_type")
    action_filter_by = request.GET.get("filter")

    # Define previous filters as a dictionary
    previous_filters = {
        "payment_status": {
            "paid": True if request.GET.get("payment_status_paid") else False,
            "pending": True if request.GET.get("payment_status_pending") else False,
            "overdue": True if request.GET.get("payment_status_overdue") else False,
        },
        "amount": {
            "20+": True if request.GET.get("amount_20+") else False,
            "50+": True if request.GET.get("amount_50+") else False,
            "100+": True if request.GET.get("amount_100+") else False,
        },
    }

    context, invoices = get_context(invoices, sort_by, previous_filters, sort_direction, action_filter_type, action_filter_by)

    # check/update payment status to make sure it is correct before invoices are filtered and displayed
    invoices.update(
        payment_status=Case(
            When(
                date_due__lt=timezone.now().date(),
                payment_status="pending",
                then=Value("overdue"),
            ),
            When(
                date_due__gt=timezone.now().date(),
                payment_status="overdue",
                then=Value("pending"),
            ),
            default=F("payment_status"),
            output_field=CharField(),
        )
    )

    # Render the HTMX response
    return render(request, "pages/invoices/dashboard/_fetch_body.html", context)
