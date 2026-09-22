from decimal import Decimal
from typing import TYPE_CHECKING

from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from apps.catalogue.forms import BrandForm, ItemForm
from apps.catalogue.models import Brand, Item
from apps.core.access import requires

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


def warn_above_mrp(request: HttpRequest, item: Item) -> None:
    for unit, price in item.above_mrp():
        messages.warning(
            request, f"{unit.code} sells at ₹{price}, above its MRP of ₹{unit.mrp}."
        )


@requires("catalogue.view_item")
def item_directory(request: HttpRequest) -> HttpResponse:
    """Every Item on file, by name, with its code, stock unit, price and GST rate.

    Narrowed, when asked, to the Items of one Brand.
    """
    everything = Item.objects.select_related("brand").prefetch_related("units")
    brands = Brand.objects.all()

    # A Brand that is not on file, or not a number, filters nothing rather
    # than failing: it is a link somebody kept, not a mistake to report.
    raw = request.GET.get("brand", "")
    brand = brands.filter(pk=raw).first() if raw.isdigit() else None
    items = everything.filter(brand=brand) if brand else everything

    return render(
        request,
        "catalogue/directory.html",
        {
            "items": items,
            "total": everything.count(),
            "brands": brands,
            "brand": brand,
        },
    )


@requires("catalogue.add_item")
def record_item(request: HttpRequest) -> HttpResponse:
    """Describe a new Item once, so it need never be retyped on an invoice."""
    if request.method != "POST":
        form = ItemForm(user=request.user)
        return render(request, "catalogue/record.html", {"form": form})

    form = ItemForm(request.POST, user=request.user)

    if not form.is_valid():
        # Rendered rather than redirected, so that everything already typed is
        # still on the page next to what was wrong with it.
        return render(request, "catalogue/record.html", {"form": form})

    item = form.save()
    messages.success(request, f"{item.name} is saved.")
    warn_above_mrp(request, item)
    return redirect("item_detail", pk=item.pk)


@requires("catalogue.view_item")
def item_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """What is on file about an Item, as an invoice line will copy it."""
    item = get_object_or_404(
        Item.objects.select_related("brand").prefetch_related("units"), pk=pk
    )
    other_units = [
        (unit, item.quote(Decimal(1), unit))
        for unit in sorted(item.units.all(), key=lambda unit: unit.pk)
        if not unit.is_stock_unit
    ]
    return render(
        request,
        "catalogue/detail.html",
        {"item": item, "other_units": other_units},
    )


@requires("catalogue.change_item")
def edit_item(request: HttpRequest, pk: int) -> HttpResponse:
    """Correct an Item's details, its stock unit or its price."""
    item = get_object_or_404(Item.objects.prefetch_related("units"), pk=pk)

    if request.method != "POST":
        form = ItemForm(instance=item, user=request.user)
        return render(request, "catalogue/edit.html", {"form": form, "item": item})

    # Bound to its own instance: a form that fails validation still writes what
    # it could clean onto the instance it holds, and `item` is what the page
    # shows as on file.
    form = ItemForm(request.POST, instance=Item.objects.get(pk=pk), user=request.user)

    if not form.is_valid():
        # Rendered rather than redirected, so that everything already typed is
        # still on the page next to what was wrong with it.
        return render(request, "catalogue/edit.html", {"form": form, "item": item})

    form.save()
    messages.success(request, f"{form.instance.name} is saved.")
    warn_above_mrp(request, form.instance)
    return redirect("item_detail", pk=pk)


@requires("catalogue.view_brand")
def brand_directory(request: HttpRequest) -> HttpResponse:
    """Every Brand on file, by name, with how many Items are sold under it."""
    brands = Brand.objects.annotate(item_count=Count("items")).order_by("name")
    return render(request, "catalogue/brands/directory.html", {"brands": brands})


@requires("catalogue.add_brand")
def record_brand(request: HttpRequest) -> HttpResponse:
    """Put a Brand on file before any Item is sold under it."""
    form = BrandForm(request.POST or None)

    if request.method != "POST" or not form.is_valid():
        return render(request, "catalogue/brands/form.html", {"form": form})

    brand = form.save()
    messages.success(request, f"{brand.name} is saved.")
    return redirect("brand_directory")


@requires("catalogue.change_brand")
def edit_brand(request: HttpRequest, pk: int) -> HttpResponse:
    """Correct how a Brand's name is written, for every Item sold under it."""
    brand = get_object_or_404(Brand, pk=pk)
    # Bound to its own instance, so the page shows the name on file above a
    # refused rename.
    form = BrandForm(request.POST or None, instance=Brand.objects.get(pk=pk))

    if request.method != "POST" or not form.is_valid():
        return render(
            request, "catalogue/brands/form.html", {"form": form, "brand": brand}
        )

    form.save()
    messages.success(request, f"{form.instance.name} is saved.")
    return redirect("brand_directory")
