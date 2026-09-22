from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.catalogue.models import Brand, Category, Item, ItemUnit
from tests.catalogue.conftest import record, submitted
from tests.conftest import PASSWORD, role

User = get_user_model()


def duplicate_url(item):
    return reverse("duplicate_item", args=[item.pk])


def detail_url(item):
    return reverse("item_detail", args=[item.pk])


@pytest.fixture
def chrome(db):
    """A tap on file with a Brand, a Category, an MRP and another unit."""
    fittings = Category.objects.create(name="Fittings")
    item = record(
        brand=Brand.objects.create(name="Jaquar"),
        category=Category.objects.create(name="Taps", parent=fittings),
    )
    item.units.update(mrp=Decimal("1600.00"))
    ItemUnit.objects.create(
        item=item,
        code="BOX",
        rate=Decimal(6),
        selling_price=Decimal("8400.00"),
        mrp=Decimal("9000.00"),
    )
    return item


@pytest.fixture
def cannot_add(db):
    """An Operator who may look up and edit Items, but not record them."""
    user = User.objects.create_user(
        email="ravi@example.com", name="Ravi Kumar", password=PASSWORD
    )
    user.groups.add(role("Clerk", "catalogue.view_item", "catalogue.change_item"))
    return user


@pytest.mark.django_db
def test_the_form_arrives_filled_from_the_source(client, signed_in, chrome):
    form = client.get(duplicate_url(chrome)).context["form"]

    assert form["name"].value() == chrome.name
    assert form["kind"].value() == "goods"
    assert form["hsn_sac"].value() == "848180"
    assert form["gst_rate"].value() == chrome.gst_rate
    assert form["brand"].value() == chrome.brand_id
    assert form["category"].value() == chrome.category_id
    assert form["stock_unit"].value() == "NOS"
    assert form["selling_price"].value() == Decimal("1450.00")
    assert form["mrp"].value() == Decimal("1600.00")
    [box] = form.units.forms
    assert box["code"].value() == "BOX"
    assert box["rate"].value() == Decimal(6)
    assert box["selling_price"].value() == Decimal("8400.00")
    assert box["mrp"].value() == Decimal("9000.00")


@pytest.mark.django_db
def test_the_item_code_is_blank(client, signed_in, chrome):
    form = client.get(duplicate_url(chrome)).context["form"]

    assert not form["code"].value()


@pytest.mark.django_db
def test_opening_the_form_saves_nothing(client, signed_in, chrome):
    client.get(duplicate_url(chrome))

    assert Item.objects.count() == 1
    assert ItemUnit.objects.count() == 2


@pytest.mark.django_db
def test_submitting_records_a_new_item_and_leaves_the_source(client, signed_in, chrome):
    code = chrome.code
    posted = submitted(
        {"code": "BOX", "rate": "6", "selling_price": "8400.00"},
        name="Jaquar Florentine tap, black",
        brand=str(chrome.brand_id),
        category=str(chrome.category_id),
    )

    response = client.post(duplicate_url(chrome), posted)

    black = Item.objects.get(name="Jaquar Florentine tap, black")
    assert response.url == detail_url(black)
    assert black.code != code
    assert black.brand == chrome.brand
    assert black.category == chrome.category
    assert black.units.get(code="BOX").rate == Decimal(6)
    chrome.refresh_from_db()
    assert chrome.name == "Jaquar Florentine tap, chrome"
    assert chrome.code == code
    assert chrome.units.count() == 2


@pytest.mark.django_db
def test_a_typed_item_code_is_taken(client, signed_in, chrome):
    client.post(duplicate_url(chrome), submitted(name="Black tap", code="TAP-BLK"))

    assert Item.objects.get(name="Black tap").code == "TAP-BLK"


@pytest.mark.django_db
def test_a_refused_duplicate_stays_on_the_form(client, signed_in, chrome):
    response = client.post(duplicate_url(chrome), submitted(name=""))

    assert response.status_code == 200
    assert Item.objects.count() == 1


@pytest.mark.django_db
def test_the_detail_page_offers_duplicating(client, signed_in, chrome):
    page = client.get(detail_url(chrome)).content.decode()

    assert duplicate_url(chrome) in page


@pytest.mark.django_db
def test_duplicating_needs_the_add_permission(client, business, cannot_add, chrome):
    client.force_login(cannot_add)

    assert duplicate_url(chrome) not in client.get(detail_url(chrome)).content.decode()
    assert client.get(duplicate_url(chrome)).status_code == 403
    assert client.post(duplicate_url(chrome), submitted()).status_code == 403
    assert Item.objects.count() == 1


@pytest.mark.django_db
def test_duplicating_an_item_not_on_file_is_not_found(client, signed_in):
    assert client.get(reverse("duplicate_item", args=[999])).status_code == 404


def as_posted(form):
    """What the rendered form posts back when the Operator changes nothing."""
    posted = {name: form[name].value() or "" for name in form.fields}
    management = form.units.management_form
    posted |= {
        management.add_prefix(name): management[name].value()
        for name in management.fields
    }
    for unit_form in form.units.forms:
        for name in unit_form.fields:
            posted[unit_form.add_prefix(name)] = unit_form[name].value() or ""
    return posted


@pytest.mark.django_db
def test_the_copied_units_are_saved_as_they_arrive(client, signed_in, chrome):
    form = client.get(duplicate_url(chrome)).context["form"]
    posted = as_posted(form) | {"name": "Jaquar Florentine tap, black"}

    client.post(duplicate_url(chrome), posted)

    black = Item.objects.get(name="Jaquar Florentine tap, black")
    assert black.stock_unit.mrp == Decimal("1600.00")
    box = black.units.get(code="BOX")
    assert (box.rate, box.selling_price, box.mrp) == (
        Decimal(6),
        Decimal("8400.00"),
        Decimal("9000.00"),
    )
    assert chrome.units.count() == 2
