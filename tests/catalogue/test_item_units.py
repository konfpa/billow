from decimal import Decimal

import pytest
from django.urls import reverse

from apps.catalogue.models import Item, ItemUnit
from tests.catalogue.conftest import record, submitted

RECORD = reverse("record_item")
DIRECTORY = reverse("item_directory")

PIPE = {
    "name": "Astral PVC pipe, 110 mm",
    "hsn_sac": "3917",
    "stock_unit": "ft",
    "selling_price": "12",
}
PIECE = {"code": "PCS", "rate": "20", "selling_price": "220"}


def edit_url(item):
    return reverse("edit_item", args=[item.pk])


def detail_url(item):
    return reverse("item_detail", args=[item.pk])


def pipe_on_file():
    """The worked example from #58, as recording it leaves it."""
    item = record(name="Astral PVC pipe, 110 mm", price="12", hsn_sac="3917")
    item.units.update(code="ft")
    pcs = ItemUnit.objects.create(
        item=item, code="PCS", rate=Decimal(20), selling_price=Decimal(220)
    )
    return item, pcs


def on_file(pcs, **changes):
    """A unit on file as the edit form posts it back."""
    return {
        "id": str(pcs.pk),
        "code": pcs.code,
        "rate": str(pcs.rate),
        "selling_price": str(pcs.selling_price or ""),
        **changes,
    }


def further_units(item):
    return {
        unit.code: (unit.rate, unit.selling_price)
        for unit in item.units.filter(is_stock_unit=False)
    }


@pytest.mark.django_db
def test_a_goods_item_is_recorded_with_further_units(client, signed_in):
    client.post(
        RECORD,
        submitted(PIECE, {"code": "BDL", "rate": "200", "selling_price": ""}, **PIPE),
    )

    item = Item.objects.get()
    assert item.stock_unit.code == "ft"
    assert further_units(item) == {
        "PCS": (Decimal(20), Decimal(220)),
        "BDL": (Decimal(200), None),
    }


@pytest.mark.django_db
def test_a_rate_takes_decimals(client, signed_in):
    client.post(RECORD, submitted({"code": "PCS", "rate": "9.8425"}, **PIPE))

    assert further_units(Item.objects.get())["PCS"][0] == Decimal("9.8425")


@pytest.mark.django_db
def test_a_rate_beyond_six_places_is_refused(client, signed_in):
    response = client.post(
        RECORD, submitted({"code": "PCS", "rate": "0.0833333"}, **PIPE)
    )

    assert not Item.objects.exists()
    assert "rate" in response.context["form"].units.forms[0].errors


@pytest.mark.django_db
@pytest.mark.parametrize("rate", ["0", "-20"])
def test_a_rate_of_zero_or_less_is_refused(client, signed_in, rate):
    response = client.post(RECORD, submitted({"code": "PCS", "rate": rate}, **PIPE))

    assert not Item.objects.exists()
    errors = response.context["form"].units.forms[0].errors
    assert errors["rate"] == ["One unit holds more than zero of the stock unit."]


@pytest.mark.django_db
def test_a_unit_needs_a_rate(client, signed_in):
    response = client.post(RECORD, submitted({"code": "PCS", "rate": ""}, **PIPE))

    assert not Item.objects.exists()
    assert "rate" in response.context["form"].units.forms[0].errors


@pytest.mark.django_db
def test_the_same_unit_twice_is_refused(client, signed_in):
    response = client.post(
        RECORD, submitted(PIECE, {"code": "PCS", "rate": "10"}, **PIPE)
    )

    assert not Item.objects.exists()
    errors = response.context["form"].units.forms[1].errors
    assert errors["code"] == ["This Item already has this unit."]


@pytest.mark.django_db
def test_the_stock_unit_again_is_refused(client, signed_in):
    response = client.post(RECORD, submitted({"code": "ft", "rate": "2"}, **PIPE))

    assert not Item.objects.exists()
    errors = response.context["form"].units.forms[0].errors
    assert errors["code"] == ["This Item already has this unit."]


@pytest.mark.django_db
def test_a_service_with_more_than_one_unit_is_refused(client, signed_in):
    response = client.post(
        RECORD,
        submitted(
            {"code": "NOS", "rate": "2"},
            name="Tap fitting",
            kind="service",
            hsn_sac="995461",
            stock_unit="OTH",
        ),
    )

    assert not Item.objects.exists()
    page = response.content.decode()
    assert "A Service is sold in one unit, so it has no further units." in page


@pytest.mark.django_db
def test_a_blank_unit_row_is_ignored(client, signed_in):
    response = client.post(
        RECORD, submitted({"code": "", "rate": "", "selling_price": ""}, **PIPE)
    )

    assert response.status_code == 302
    assert further_units(Item.objects.get()) == {}


@pytest.mark.django_db
def test_a_refused_unit_is_named_in_the_summary(client, signed_in):
    page = client.post(
        RECORD, submitted({"code": "PCS", "rate": "0"}, **PIPE)
    ).content.decode()

    assert 'href="#id_units-0-rate"' in page
    assert "One unit holds more than zero of the stock unit." in page


@pytest.mark.django_db
def test_feet_and_inches_are_offered_for_every_unit(client, signed_in):
    form = client.get(RECORD).context["form"]

    for choices in (
        form.fields["stock_unit"].choices,
        form.units.empty_form.fields["code"].choices,
    ):
        assert ("ft", "ft · Feet") in choices
        assert ("in", "in · Inches") in choices


@pytest.mark.django_db
def test_an_item_stocked_in_feet_reads_ft(client, signed_in):
    item, _ = pipe_on_file()

    directory = client.get(DIRECTORY).content.decode()
    detail = client.get(detail_url(item)).content.decode()

    assert "Per ft" in directory
    assert "ft · Feet" in detail
    assert "₹12.00 per ft" in detail


@pytest.mark.django_db
def test_the_detail_page_shows_every_unit_its_rate_and_own_price(client, signed_in):
    item, _ = pipe_on_file()

    page = client.get(detail_url(item)).content.decode()

    assert "1 PCS = 20 ft" in page
    assert "₹220.00" in page
    assert "Own price" in page


@pytest.mark.django_db
def test_the_detail_page_marks_a_derived_price(client, signed_in):
    item, pcs = pipe_on_file()
    pcs.selling_price = None
    pcs.rate = Decimal("9.8425")
    pcs.save()

    page = client.get(detail_url(item)).content.decode()

    assert "1 PCS = 9.8425 ft" in page
    assert "₹118.11" in page
    assert "Derived" in page


@pytest.mark.django_db
def test_the_edit_form_arrives_with_the_further_units(client, signed_in):
    item, pcs = pipe_on_file()

    units = client.get(edit_url(item)).context["form"].units

    assert [form.instance for form in units.initial_forms] == [pcs]


@pytest.mark.django_db
def test_a_unit_is_changed(client, signed_in):
    item, pcs = pipe_on_file()

    client.post(
        edit_url(item),
        submitted(on_file(pcs, rate="19.5", selling_price=""), **PIPE),
    )

    assert further_units(item) == {"PCS": (Decimal("19.5"), None)}
    latest = pcs.history.latest()
    assert latest.history_type == "~"
    assert latest.history_user == signed_in


@pytest.mark.django_db
def test_a_unit_is_removed(client, signed_in):
    item, pcs = pipe_on_file()

    client.post(edit_url(item), submitted(on_file(pcs, DELETE="on"), **PIPE))

    assert further_units(item) == {}
    latest = ItemUnit.history.filter(id=pcs.pk).latest()
    assert latest.history_type == "-"
    assert latest.history_user == signed_in


@pytest.mark.django_db
def test_a_unit_is_added(client, signed_in):
    item, pcs = pipe_on_file()

    client.post(
        edit_url(item),
        submitted(on_file(pcs), {"code": "BDL", "rate": "200"}, **PIPE),
    )

    bundle = item.units.get(code="BDL")
    assert bundle.rate == Decimal(200)
    latest = bundle.history.latest()
    assert latest.history_type == "+"
    assert latest.history_user == signed_in


@pytest.mark.django_db
def test_an_unchanged_unit_gains_no_history(client, signed_in):
    item, pcs = pipe_on_file()

    client.post(edit_url(item), submitted(on_file(pcs), **{**PIPE, "name": "Pipe"}))

    assert pcs.history.count() == 1


@pytest.mark.django_db
def test_a_removed_unit_may_be_chosen_again(client, signed_in):
    item, pcs = pipe_on_file()

    response = client.post(
        edit_url(item),
        submitted(on_file(pcs, DELETE="on"), {"code": "PCS", "rate": "10"}, **PIPE),
    )

    assert response.status_code == 302
    assert further_units(item) == {"PCS": (Decimal(10), None)}


@pytest.mark.django_db
def test_the_stock_unit_and_a_further_unit_trade_places(client, signed_in):
    item, pcs = pipe_on_file()

    response = client.post(
        edit_url(item),
        submitted(
            on_file(pcs, code="ft", rate="0.05", selling_price="12"),
            **{**PIPE, "stock_unit": "PCS", "selling_price": "220"},
        ),
    )

    assert response.status_code == 302
    assert item.stock_unit.code == "PCS"
    assert further_units(item) == {"ft": (Decimal("0.05"), Decimal(12))}


@pytest.mark.django_db
def test_a_refused_edit_leaves_the_units_alone(client, signed_in):
    item, pcs = pipe_on_file()

    client.post(
        edit_url(item),
        submitted(on_file(pcs, rate="5"), {"code": "PCS", "rate": "1"}, **PIPE),
    )

    assert further_units(item) == {"PCS": (Decimal(20), Decimal(220))}


@pytest.mark.django_db
def test_a_goods_item_turned_service_with_further_units_is_refused(client, signed_in):
    item, pcs = pipe_on_file()

    response = client.post(
        edit_url(item),
        submitted(on_file(pcs), **{**PIPE, "kind": "service", "hsn_sac": "995461"}),
    )

    item.refresh_from_db()
    assert item.kind == Item.Kind.GOODS
    assert response.context["form"].units.non_form_errors()
