from decimal import Decimal
from typing import TYPE_CHECKING

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from apps.catalogue.forms import ItemForm
from apps.catalogue.models import Item
from apps.core.access import requires

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


@requires("catalogue.view_item")
def item_directory(request: HttpRequest) -> HttpResponse:
    """Every Item on file, by name, with its code, stock unit, price and GST rate."""
    items = Item.objects.prefetch_related("units")
    return render(request, "catalogue/directory.html", {"items": items})


@requires("catalogue.add_item")
def record_item(request: HttpRequest) -> HttpResponse:
    """Describe a new Item once, so it need never be retyped on an invoice."""
    if request.method != "POST":
        return render(request, "catalogue/record.html", {"form": ItemForm()})

    form = ItemForm(request.POST)

    if not form.is_valid():
        # Rendered rather than redirected, so that everything already typed is
        # still on the page next to what was wrong with it.
        return render(request, "catalogue/record.html", {"form": form})

    item = form.save()
    messages.success(request, f"{item.name} is saved.")
    return redirect("item_detail", pk=item.pk)


@requires("catalogue.view_item")
def item_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """What is on file about an Item, as an invoice line will copy it."""
    item = get_object_or_404(Item.objects.prefetch_related("units"), pk=pk)
    further_units = [
        (unit, item.quote(Decimal(1), unit))
        for unit in sorted(item.units.all(), key=lambda unit: unit.pk)
        if not unit.is_stock_unit
    ]
    return render(
        request,
        "catalogue/detail.html",
        {"item": item, "further_units": further_units},
    )


@requires("catalogue.change_item")
def edit_item(request: HttpRequest, pk: int) -> HttpResponse:
    """Correct an Item's details, its stock unit or its price."""
    item = get_object_or_404(Item.objects.prefetch_related("units"), pk=pk)

    if request.method != "POST":
        form = ItemForm(instance=item)
        return render(request, "catalogue/edit.html", {"form": form, "item": item})

    # Bound to its own instance: a form that fails validation still writes what
    # it could clean onto the instance it holds, and `item` is what the page
    # shows as on file.
    form = ItemForm(request.POST, instance=Item.objects.get(pk=pk))

    if not form.is_valid():
        # Rendered rather than redirected, so that everything already typed is
        # still on the page next to what was wrong with it.
        return render(request, "catalogue/edit.html", {"form": form, "item": item})

    form.save()
    messages.success(request, f"{form.instance.name} is saved.")
    return redirect("item_detail", pk=pk)
