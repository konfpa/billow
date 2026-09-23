from decimal import Decimal
from typing import TYPE_CHECKING

from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.catalogue.forms import BrandForm, CategoryForm, ItemForm
from apps.catalogue.models import Brand, Category, Item
from apps.core.access import requires
from apps.core.filters import chosen
from apps.core.pagination import paged
from apps.core.redirects import back

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

    Or, asked for, every Item archived. Either is narrowed, when asked, to the
    Items of one Brand, one Category, or both, and to those matching every word
    typed into the search. A top-level Category takes in the Items of those
    under it.
    """
    showing_archived = request.GET.get("show") == "archived"
    everything = (
        (Item.including_archived.archived() if showing_archived else Item.objects)
        .select_related("brand", "category__parent")
        .prefetch_related("units")
    )
    brands = Brand.objects.all()
    categories = Category.objects.by_path()

    brand = chosen(brands, request.GET.get("brand", ""))
    category = chosen(categories, request.GET.get("category", ""))
    query = request.GET.get("q", "").strip()

    items = everything.matching(query)
    if brand:
        items = items.filter(brand=brand)
    if category:
        items = items.filter(Q(category=category) | Q(category__parent=category))

    page = paged(request, items)
    # The paginator's own count, not `if items:`. Asking a queryset whether it
    # is empty fetches every row it has and caches them, and the slice that
    # follows is then taken in Python: the page would be a page, and the
    # register behind it would still arrive whole.
    matched = page["page_obj"].paginator.count

    # Which nothing this is gets decided here rather than in the template,
    # where every one of them is just an empty list. A search that matches
    # nothing is a no-match even inside a filter, since the Item may be on
    # file under another Brand or Category.
    if matched:
        empty = None
    elif query:
        empty = "catalogue/empty/no_match.html"
    elif brand or category:
        empty = "catalogue/empty/nothing_filtered.html"
    elif showing_archived:
        empty = "catalogue/empty/nothing_archived.html"
    else:
        empty = "catalogue/empty/nothing_on_file.html"

    return render(
        request,
        "catalogue/directory.html",
        {
            # The page, not the whole register: see apps/core/pagination.py.
            "items": page["page_obj"],
            "matched": matched,
            "total": everything.count(),
            "empty": empty,
            "brands": brands,
            "brand": brand,
            "categories": categories,
            "category": category,
            "query": query,
            "showing_archived": showing_archived,
            **page,
        },
    )


@requires("catalogue.add_item")
def record_item(request: HttpRequest) -> HttpResponse:
    """Describe a new Item once, so it need never be retyped on an invoice."""
    if request.method != "POST":
        form = ItemForm(user=request.user)
        return render(request, "catalogue/record.html", {"form": form})

    return save_new_item(request)


@requires("catalogue.add_item")
def duplicate_item(request: HttpRequest, pk: int) -> HttpResponse:
    """Record a new Item starting from one on file, such as another finish of a tap.

    Nothing is saved until the form is submitted, and then only the new Item.
    """
    source = get_object_or_404(Item.including_archived.prefetch_related("units"), pk=pk)

    if request.method != "POST":
        form = ItemForm(user=request.user, copying=source)
        return render(
            request, "catalogue/record.html", {"form": form, "source": source}
        )

    return save_new_item(request, source)


def save_new_item(request: HttpRequest, source: Item | None = None) -> HttpResponse:
    form = ItemForm(request.POST, user=request.user)

    if not form.is_valid():
        # Rendered rather than redirected, so that everything already typed is
        # still on the page next to what was wrong with it.
        return render(
            request, "catalogue/record.html", {"form": form, "source": source}
        )

    item = form.save()
    messages.success(request, f"{item.name} is saved.")
    warn_above_mrp(request, item)
    return redirect("item_detail", pk=item.pk)


@requires("catalogue.view_item")
def item_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """What is on file about an Item, as an invoice line will copy it."""
    item = get_object_or_404(
        Item.including_archived.select_related(
            "brand", "category__parent"
        ).prefetch_related("units"),
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
    item = get_object_or_404(Item.including_archived.prefetch_related("units"), pk=pk)

    if request.method != "POST":
        form = ItemForm(instance=item, user=request.user)
        return render(request, "catalogue/edit.html", {"form": form, "item": item})

    # Bound to its own instance: a form that fails validation still writes what
    # it could clean onto the instance it holds, and `item` is what the page
    # shows as on file.
    form = ItemForm(
        request.POST, instance=Item.including_archived.get(pk=pk), user=request.user
    )

    if not form.is_valid():
        # Rendered rather than redirected, so that everything already typed is
        # still on the page next to what was wrong with it.
        return render(request, "catalogue/edit.html", {"form": form, "item": item})

    form.save()
    messages.success(request, f"{form.instance.name} is saved.")
    warn_above_mrp(request, form.instance)
    return redirect("item_detail", pk=pk)


@requires("catalogue.archive_item")
@require_POST
def archive_item(request: HttpRequest, pk: int) -> HttpResponse:
    """Withdraw an Item the Business no longer sells from the directory."""
    item = get_object_or_404(Item.including_archived, pk=pk)
    item.archive()

    messages.success(request, f"{item.name} is archived.")
    return back(request, "item_detail", pk=pk)


@requires("catalogue.archive_item")
@require_POST
def restore_item(request: HttpRequest, pk: int) -> HttpResponse:
    """Bring an Item back into sale, as the Item it always was."""
    item = get_object_or_404(Item.including_archived, pk=pk)
    item.restore()

    messages.success(request, f"{item.name} is back on file.")
    return back(request, "item_detail", pk=pk)


# The annotation joins past the default manager, so the archived are left out
# here as the Item directory leaves them out.
ITEMS_ON_FILE = Count("items", filter=Q(items__archived_at__isnull=True))


@requires("catalogue.view_brand")
def brand_directory(request: HttpRequest) -> HttpResponse:
    """Every Brand on file, by name, with how many Items are sold under it."""
    brands = Brand.objects.annotate(item_count=ITEMS_ON_FILE).order_by("name")
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
    categories = list(Category.objects.by_path().annotate(item_count=ITEMS_ON_FILE))
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
