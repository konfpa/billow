from typing import TYPE_CHECKING

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.business.models import Business
from apps.core.access import requires
from apps.core.pagination import paged
from apps.core.redirects import back
from apps.suppliers.forms import SupplierForm
from apps.suppliers.models import Supplier

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


@requires("suppliers.view_supplier")
def supplier_directory(request: HttpRequest) -> HttpResponse:
    """Everyone the Business buys from, or — asked for — everyone archived.

    Either can be searched by name, legal name or GSTIN, and a search stays
    inside the one it was typed into.
    """
    showing_archived = request.GET.get("show") == "archived"
    everyone = (
        Supplier.including_archived.archived()
        if showing_archived
        else Supplier.objects.all()
    )

    query = request.GET.get("q", "").strip()
    suppliers = everyone.matching(query) if query else everyone

    page = paged(request, suppliers)
    # The paginator's own count, not `if suppliers:`. Asking a queryset whether
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
        empty = "suppliers/empty/no_match.html"
    elif showing_archived:
        empty = "suppliers/empty/nobody_archived.html"
    else:
        empty = "suppliers/empty/nobody_on_file.html"

    return render(
        request,
        "suppliers/directory.html",
        {
            # The page, not the whole register: see apps/core/pagination.py.
            "suppliers": page["page_obj"],
            "matched": matched,
            "total": everyone.count(),
            "empty": empty,
            "showing_archived": showing_archived,
            "query": query,
            **page,
        },
    )


@requires("suppliers.add_supplier")
def record_supplier(request: HttpRequest) -> HttpResponse:
    """Put a new Supplier on file."""
    if request.method != "POST":
        return render(request, "suppliers/record.html", {"form": SupplierForm()})

    form = SupplierForm(request.POST)

    if not form.is_valid():
        # Rendered rather than redirected, so that everything already typed is
        # still on the page next to what was wrong with it.
        return render(request, "suppliers/record.html", {"form": form})

    supplier = form.save()
    messages.success(request, f"{supplier.name} is saved.")
    return redirect("supplier_directory")


@requires("suppliers.view_supplier")
def supplier_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """What is on file about a Supplier, and their Purchases to whoever may see them."""
    supplier = get_object_or_404(Supplier.including_archived, pk=pk)

    purchases = None
    if request.user.has_perm("purchases.view_purchase"):
        business = Business.load()
        purchases = [
            (purchase, purchase.totals(business))
            for purchase in supplier.purchases.prefetch_related("lines__item")
        ]

    return render(
        request,
        "suppliers/detail.html",
        {"supplier": supplier, "purchases": purchases},
    )


@requires("suppliers.change_supplier")
def edit_supplier(request: HttpRequest, pk: int) -> HttpResponse:
    """Correct what is on file about a Supplier.

    Every rule that applies to recording applies here, the GSTIN included, so
    a typo caught later is fixed rather than worked around with a second
    Supplier.
    """
    supplier = get_object_or_404(Supplier.including_archived, pk=pk)

    if request.method != "POST":
        form = SupplierForm(instance=supplier)
        return render(
            request,
            "suppliers/edit.html",
            {"form": form, "supplier": supplier},
        )

    # Bound to its own instance: a form that fails validation still writes what
    # it could clean onto the instance it holds, and `supplier` is what the
    # page shows as on file.
    form = SupplierForm(
        request.POST,
        instance=Supplier.including_archived.get(pk=pk),
    )

    if not form.is_valid():
        # Rendered rather than redirected, so that everything already typed is
        # still on the page next to what was wrong with it.
        return render(
            request,
            "suppliers/edit.html",
            {"form": form, "supplier": supplier},
        )

    form.save()
    messages.success(request, f"{form.instance.name} is saved.")
    return redirect("supplier_detail", pk=pk)


@requires("suppliers.archive_supplier")
@require_POST
def archive_supplier(request: HttpRequest, pk: int) -> HttpResponse:
    """Withdraw a Supplier the Business no longer buys from."""
    supplier = get_object_or_404(Supplier.including_archived, pk=pk)
    supplier.archive()

    messages.success(request, f"{supplier.name} is archived.")
    return back(request, "supplier_detail", pk=pk)


@requires("suppliers.archive_supplier")
@require_POST
def restore_supplier(request: HttpRequest, pk: int) -> HttpResponse:
    """Bring back a Supplier who returned, as the record they always were."""
    supplier = get_object_or_404(Supplier.including_archived, pk=pk)
    supplier.restore()

    messages.success(request, f"{supplier.name} is back on file.")
    return back(request, "supplier_detail", pk=pk)
