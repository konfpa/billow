from typing import TYPE_CHECKING

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from apps.business.models import Business
from apps.core.access import requires
from apps.purchases.forms import PurchaseForm
from apps.purchases.models import Purchase

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


@requires("purchases.view_purchase")
def purchase_directory(request: HttpRequest) -> HttpResponse:
    """Every Purchase on file, the most recently received first."""
    business = Business.load()
    purchases = [
        (purchase, purchase.totals(business))
        for purchase in Purchase.objects.select_related("supplier").prefetch_related(
            "lines"
        )
    ]
    return render(request, "purchases/directory.html", {"purchases": purchases})


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
