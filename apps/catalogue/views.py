from decimal import Decimal
from typing import TYPE_CHECKING

from django.contrib import messages
from django.db.models import Count, Model, Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.catalogue.forms import BrandForm, CategoryForm, ItemForm
from apps.catalogue.models import Brand, Category, Item
from apps.core.access import requires

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http import HttpRequest, HttpResponse


def warn_above_mrp(request: HttpRequest, item: Item) -> None:
    for unit, price in item.above_mrp():
        messages.warning(
            request, f"{unit.code} sells at ₹{price}, above its MRP of ₹{unit.mrp}."
        )


def on_file[M: Model](choices: QuerySet[M], raw: str) -> M | None:
    """The choice `raw` names, or None for one not on file or not a number.

    A filter link somebody kept filters nothing rather than failing: it is
    not a mistake to report.
    """
    return choices.filter(pk=raw).first() if raw.isdigit() else None


@requires("catalogue.view_item")
def item_directory(request: HttpRequest) -> HttpResponse:
    """Every Item on file, by name, with its code, stock unit, price and GST rate.

    Narrowed, when asked, to the Items of one Brand, one Category, or both,
    and to those matching every word typed into the search. A top-level
    Category takes in the Items of those under it.
    """
    everything = Item.objects.select_related(
        "brand", "category__parent"
    ).prefetch_related("units")
    brands = Brand.objects.all()
    categories = Category.objects.by_path()

    brand = on_file(brands, request.GET.get("brand", ""))
    category = on_file(categories, request.GET.get("category", ""))
    query = request.GET.get("q", "").strip()

    items = everything.matching(query)
    if brand:
        items = items.filter(brand=brand)
    if category:
        items = items.filter(Q(category=category) | Q(category__parent=category))

    # Which nothing this is gets decided here rather than in the template,
    # where every one of them is just an empty list. A search that matches
    # nothing is a no-match even inside a filter, since the Item may be on
    # file under another Brand or Category.
    if items:
        empty = None
    elif query:
        empty = "catalogue/empty/no_match.html"
    elif brand or category:
        empty = "catalogue/empty/nothing_filtered.html"
    else:
        empty = "catalogue/empty/nothing_on_file.html"

    return render(
        request,
        "catalogue/directory.html",
        {
            "items": items,
            "total": everything.count(),
            "empty": empty,
            "brands": brands,
            "brand": brand,
            "categories": categories,
            "category": category,
            "query": query,
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
        Item.objects.select_related("brand", "category__parent").prefetch_related(
            "units"
        ),
        pk=pk,
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


@requires("catalogue.view_category")
def category_directory(request: HttpRequest) -> HttpResponse:
    """Every Category on file, each under its parent, with how many Items it holds.

    A top-level Category's count takes in the Items of those under it, as
    filtering the Item directory by it does.
    """
    categories = list(Category.objects.by_path().annotate(item_count=Count("items")))
    by_pk = {category.pk: category for category in categories}
    for category in categories:
        if category.parent_id is not None:
            by_pk[category.parent_id].item_count += category.item_count
    return render(
        request, "catalogue/categories/directory.html", {"categories": categories}
    )


@requires("catalogue.add_category")
def record_category(request: HttpRequest) -> HttpResponse:
    """Put a Category on file before any Item sits in it."""
    form = CategoryForm(request.POST or None)

    if request.method != "POST" or not form.is_valid():
        return render(request, "catalogue/categories/form.html", {"form": form})

    category = form.save()
    messages.success(request, f"{category} is saved.")
    return redirect("category_directory")


@requires("catalogue.change_category")
def edit_category(request: HttpRequest, pk: int) -> HttpResponse:
    """Rename a Category, or move it under another, for every Item in it."""
    category = get_object_or_404(Category.objects.select_related("parent"), pk=pk)
    # Bound to its own instance, so the page shows the Category on file above
    # a refused change.
    form = CategoryForm(request.POST or None, instance=Category.objects.get(pk=pk))

    if request.method != "POST" or not form.is_valid():
        return render(
            request,
            "catalogue/categories/form.html",
            {"form": form, "category": category},
        )

    form.save()
    messages.success(request, f"{form.instance} is saved.")
    return redirect("category_directory")
