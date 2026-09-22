from decimal import Decimal

import pytest

from apps.catalogue.models import Item, ItemUnit, gst_quantity
from tests.catalogue.conftest import record


def pipe(stock_price="12", pcs_price="220"):
    """The worked example from #58: PVC pipe stocked by the foot, sold by the piece."""
    item = Item.objects.create(
        name="PVC pipe, 110 mm", kind=Item.Kind.GOODS, hsn_sac="3917", gst_rate="18.00"
    )
    ft = ItemUnit.objects.create(
        item=item,
        code="ft",
        is_stock_unit=True,
        selling_price=Decimal(stock_price) if stock_price else None,
    )
    pcs = ItemUnit.objects.create(
        item=item,
        code="PCS",
        rate=Decimal(20),
        selling_price=Decimal(pcs_price) if pcs_price else None,
    )
    return item, ft, pcs


@pytest.mark.django_db
def test_a_piece_is_twenty_feet_at_its_own_price():
    item, _, pcs = pipe()

    quote = item.quote(Decimal(1), pcs)

    assert quote.stock_quantity == Decimal("20.000")
    assert quote.unit_price == Decimal("220.00")
    assert not quote.derived


@pytest.mark.django_db
def test_feet_are_sold_at_the_stock_unit_price():
    item, ft, _ = pipe()

    quote = item.quote(Decimal(5), ft)

    assert quote.stock_quantity == Decimal("5.000")
    assert quote.unit_price == Decimal("12.00")
    assert not quote.derived


@pytest.mark.django_db
def test_a_piece_without_a_price_derives_one_from_the_foot():
    item, _, pcs = pipe(pcs_price=None)

    quote = item.quote(Decimal(1), pcs)

    assert quote.unit_price == Decimal("240.00")
    assert quote.derived


@pytest.mark.django_db
def test_without_a_stock_unit_price_a_derived_unit_has_no_price():
    item, _, pcs = pipe(stock_price=None, pcs_price=None)

    quote = item.quote(Decimal(1), pcs)

    assert quote.unit_price is None


@pytest.mark.django_db
def test_a_services_single_unit_converts_one_for_one():
    service = record(
        name="Tap fitting", kind=Item.Kind.SERVICE, hsn_sac="995461", price="300"
    )

    quote = service.quote(Decimal(2), service.stock_unit)

    assert quote.stock_quantity == Decimal("2.000")
    assert quote.unit_price == Decimal("300.00")


@pytest.mark.django_db
def test_a_decimal_rate_converts_to_three_places():
    item, _, pcs = pipe()
    pcs.rate = Decimal("9.8425")
    pcs.save()

    quote = item.quote(Decimal(3), pcs)

    assert quote.stock_quantity == Decimal("29.528")


@pytest.mark.django_db
def test_a_derived_price_is_rounded_half_up_to_two_places():
    item, _, pcs = pipe(stock_price="0.25", pcs_price=None)
    pcs.rate = Decimal("0.5")
    pcs.save()

    assert item.quote(Decimal(1), pcs).unit_price == Decimal("0.13")


@pytest.mark.django_db
def test_a_unit_of_another_item_is_refused():
    item, _, _ = pipe()
    other = record(name="Jaquar tap")

    with pytest.raises(ValueError, match="not a unit of"):
        item.quote(Decimal(1), other.stock_unit)


def test_feet_report_as_metres():
    assert gst_quantity(Decimal(1000), "ft") == (Decimal("304.800"), "MTR")


def test_inches_report_as_centimetres():
    assert gst_quantity(Decimal(100), "in") == (Decimal("254.000"), "CMS")


@pytest.mark.parametrize("code", ["SQF", "NOS"])
def test_a_gst_unit_code_reports_as_it_is(code):
    assert gst_quantity(Decimal("12.5"), code) == (Decimal("12.500"), code)


@pytest.mark.django_db
def test_a_sheet_sold_by_area_reports_square_feet_unconverted():
    item = Item.objects.create(
        name="Plywood sheet, 2 x 4 ft", kind=Item.Kind.GOODS, hsn_sac="4412"
    )
    ItemUnit.objects.create(item=item, code="PCS", is_stock_unit=True)
    sqf = ItemUnit.objects.create(item=item, code="SQF", rate=Decimal("0.125"))

    assert item.quote(Decimal(16), sqf).stock_quantity == Decimal("2.000")
    assert gst_quantity(Decimal(16), sqf.code) == (Decimal("16.000"), "SQF")
