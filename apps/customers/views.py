from typing import TYPE_CHECKING

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.access import requires
from apps.core.pagination import paged
from apps.core.redirects import back
from apps.customers.forms import CustomerForm
from apps.customers.models import Customer

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


@requires("customers.view_customer")
def customer_directory(request: HttpRequest) -> HttpResponse:
    """Everyone billow can invoice, or — asked for — everyone archived.

    Either can be searched by name, legal name or GSTIN, and a search stays
    inside the one it was typed into.
    """
    showing_archived = request.GET.get("show") == "archived"
    everyone = (
        Customer.including_archived.archived()
        if showing_archived
        else Customer.objects.all()
    )

    query = request.GET.get("q", "").strip()
    customers = everyone.matching(query) if query else everyone

    page = paged(request, customers)
    # The paginator's own count, not `if customers:`. Asking a queryset whether
    # it is empty fetches every row it has and caches them, and the slice that
    # follows is then taken in Python: the page would be a page, and the
    # register behind it would still arrive whole.
    matched = page["page_obj"].paginator.count

    # Which nothing this is gets decided here rather than in the template,
    # where every one of them is just an empty list. A search that matches
    # nothing is always a no-match, even over an empty list, since whoever
    # was searched for may be on the other side of archiving.
    if matched:
        empty = None
    elif query:
        empty = "customers/empty/no_match.html"
    elif showing_archived:
        empty = "customers/empty/nobody_archived.html"
    else:
        empty = "customers/empty/nobody_on_file.html"

    return render(
        request,
        "customers/directory.html",
        {
            # The page, not the whole register: see apps/core/pagination.py.
            "customers": page["page_obj"],
            "matched": matched,
            "total": everyone.count(),
            "empty": empty,
            "showing_archived": showing_archived,
            "query": query,
            **page,
        },
    )


@requires("customers.add_customer")
def record_customer(request: HttpRequest) -> HttpResponse:
    """Put a new Customer on file."""
    if request.method != "POST":
        return render(request, "customers/record.html", {"form": CustomerForm()})

    form = CustomerForm(request.POST)

    if not form.is_valid():
        # Rendered rather than redirected, so that everything already typed is
        # still on the page next to what was wrong with it.
        return render(request, "customers/record.html", {"form": form})

    customer = form.save()
    messages.success(request, f"{customer.name} is saved.")
    return redirect("customer_directory")


@requires("customers.view_customer")
def customer_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """What is on file about a Customer, as an invoice to them will carry it."""
    customer = get_object_or_404(Customer.including_archived, pk=pk)
    return render(request, "customers/detail.html", {"customer": customer})


@requires("customers.change_customer")
def edit_customer(request: HttpRequest, pk: int) -> HttpResponse:
    """Correct what is on file about a Customer.

    Every rule that applies to recording applies here, the GSTIN included: a
    wrong recipient GSTIN cannot be amended in GSTR-1A, so a typo caught later
    has to be fixable rather than worked around with a second Customer. What is
    corrected here is the Customer and nothing else; see
    docs/adr/0007-invoices-snapshot-the-recipient.md.
    """
    customer = get_object_or_404(Customer.including_archived, pk=pk)

    if request.method != "POST":
        form = CustomerForm(instance=customer)
        return render(
            request,
            "customers/edit.html",
            {"form": form, "customer": customer},
        )

    # Bound to its own instance: a form that fails validation still writes what
    # it could clean onto the instance it holds, and `customer` is what the
    # page shows as on file.
    form = CustomerForm(
        request.POST,
        instance=Customer.including_archived.get(pk=pk),
    )

    if not form.is_valid():
        # Rendered rather than redirected, so that everything already typed is
        # still on the page next to what was wrong with it.
        return render(
            request,
            "customers/edit.html",
            {"form": form, "customer": customer},
        )

    form.save()
    messages.success(request, f"{form.instance.name} is saved.")
    return redirect("customer_detail", pk=pk)


@requires("customers.archive_customer")
@require_POST
def archive_customer(request: HttpRequest, pk: int) -> HttpResponse:
    """Withdraw a Customer who has stopped buying from the directory."""
    customer = get_object_or_404(Customer.including_archived, pk=pk)
    customer.archive()

    messages.success(request, f"{customer.name} is archived.")
    return back(request, "customer_detail", pk=pk)


@requires("customers.archive_customer")
@require_POST
def restore_customer(request: HttpRequest, pk: int) -> HttpResponse:
    """Bring back a Customer who returned, as the record they always were."""
    customer = get_object_or_404(Customer.including_archived, pk=pk)
    customer.restore()

    messages.success(request, f"{customer.name} is back on file.")
    return back(request, "customer_detail", pk=pk)
