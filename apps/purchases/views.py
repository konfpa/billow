from typing import TYPE_CHECKING

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.formats import date_format

from apps.business.models import Business
from apps.core.access import requires
from apps.core.filters import chosen, date_given
from apps.purchases.forms import PurchaseForm
from apps.purchases.models import Purchase
from apps.suppliers.models import Supplier

if TYPE_CHECKING:
    import datetime

    from django.http import HttpRequest, HttpResponse


def day(date: datetime.date) -> str:
    return date_format(date, "j M Y")


def billed_between(start: datetime.date | None, end: datetime.date | None) -> str:
    """The range of bill dates asked for, in words, or nothing if none was."""
    if start and end:
        return f"billed between {day(start)} and {day(end)}"
    if start:
        return f"billed on or after {day(start)}"
    if end:
        return f"billed on or before {day(end)}"
    return ""


@requires("purchases.view_purchase")
def purchase_directory(request: HttpRequest) -> HttpResponse:
    """Every Purchase on file, the most recently received first.

    Narrowed, when asked, to one Supplier's, to those billed between two dates
    (either end may be left open), and to those matching every word typed into
    the search.
    """
    everything = Purchase.objects.select_related("supplier").prefetch_related(
        "lines__item"
    )
    # Archived Suppliers included, since their bills are still on file; those
    # with none are left out, as picking one could only ever show nothing.
    suppliers = Supplier.including_archived.filter(
        pk__in=Purchase.objects.values("supplier")
    )

    supplier = chosen(suppliers, request.GET.get("supplier", ""))
    billed_from = date_given(request.GET.get("billed_from", ""))
    billed_to = date_given(request.GET.get("billed_to", ""))
    query = request.GET.get("q", "").strip()

    found = everything.matching(query)
    if supplier:
        found = found.filter(supplier=supplier)
    if billed_from:
        found = found.filter(bill_date__gte=billed_from)
    if billed_to:
        found = found.filter(bill_date__lte=billed_to)

    business = Business.load()
    purchases = [(purchase, purchase.totals(business)) for purchase in found]

    # As in the Item directory, a search that matches nothing is a no-match
    # even inside a filter, since the bill may be under another Supplier or
    # another period.
    if purchases:
        empty = None
    elif query:
        empty = "purchases/empty/no_match.html"
    elif supplier or billed_from or billed_to:
        empty = "purchases/empty/nothing_filtered.html"
    else:
        empty = "purchases/empty/nothing_recorded.html"

    return render(
        request,
        "purchases/directory.html",
        {
            "purchases": purchases,
            "total": everything.count(),
            "empty": empty,
            "suppliers": suppliers,
            "supplier": supplier,
            "billed_from": billed_from,
            "billed_to": billed_to,
            "billed": billed_between(billed_from, billed_to),
            "query": query,
        },
    )


@requires("purchases.add_purchase")
def record_purchase(request: HttpRequest) -> HttpResponse:
    """Record a Supplier's bill, line by line, as it was printed."""
    if request.method != "POST":
        return render(request, "purchases/record.html", {"form": PurchaseForm()})

    form = PurchaseForm(request.POST)

    if not form.is_valid():
        # Rendered rather than redirected, so that everything already typed is
        # still on the page next to what was wrong with it.
        return render(request, "purchases/record.html", {"form": form})

    purchase = form.save()
    messages.success(
        request, f"Bill {purchase.bill_number} from {purchase.supplier} is saved."
    )
    return redirect("purchase_detail", pk=purchase.pk)


@requires("purchases.view_purchase")
def purchase_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """A Purchase as recorded: its bill, its lines, and what it comes to."""
    purchase = get_object_or_404(
        Purchase.objects.select_related("supplier").prefetch_related("lines__item"),
        pk=pk,
    )
    business = Business.load()
    totals = purchase.totals(business)

    if not purchase.supplier_gstin:
        tax = "none"
    elif purchase.supplier_state == business.state:
        tax = "cgst_sgst"
    else:
        tax = "igst"

    return render(
        request,
        "purchases/detail.html",
        {
            "purchase": purchase,
            "lines": list(zip(purchase.lines.all(), totals.lines, strict=True)),
            "totals": totals,
            "tax": tax,
        },
    )
