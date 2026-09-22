from decimal import Decimal

import pytest
from django.urls import reverse

from apps.catalogue.models import Item, ItemUnit
from tests.catalogue.conftest import record, submitted

RECORD = reverse("record_item")

PIPE = {
    "name": "Astral PVC pipe, 110 mm",
    "hsn_sac": "3917",
    "stock_unit": "ft",
    "selling_price": "12",
}


def edit_url(item):
    return reverse("edit_item", args=[item.pk])


def detail_url(item):
    return reverse("item_detail", args=[item.pk])


def warnings(response):
    return [
        str(message)
        for message in response.context["messages"]
        if message.level_tag == "warning"
    ]


@pytest.mark.django_db
def test_each_unit_carries_an_mrp(client, signed_in):
    client.post(
        RECORD,
        submitted(
            {"code": "PCS", "rate": "20", "selling_price": "220", "mrp": "250"},
            mrp="15",
            **PIPE,
        ),
    )

    item = Item.objects.get()
    assert {unit.code: unit.mrp for unit in item.units.all()} == {
        "ft": Decimal(15),
        "PCS": Decimal(250),
    }


@pytest.mark.django_db
def test_an_mrp_is_optional(client, signed_in):
    client.post(
        RECORD, submitted({"code": "PCS", "rate": "20", "selling_price": "220"}, **PIPE)
    )

    assert all(unit.mrp is None for unit in Item.objects.get().units.all())


@pytest.mark.django_db
def test_a_negative_mrp_is_refused(client, signed_in):
    response = client.post(RECORD, submitted(mrp="-1"))

    assert "mrp" in response.context["form"].errors
    assert not Item.objects.exists()


@pytest.mark.django_db
def test_a_price_above_the_mrp_saves_with_a_warning(client, signed_in):
    response = client.post(
        RECORD,
        submitted(
            {"code": "PCS", "rate": "20", "selling_price": "260", "mrp": "250"},
            **PIPE,
        ),
        follow=True,
    )

    assert Item.objects.get().units.get(code="PCS").selling_price == Decimal(260)
    assert warnings(response) == ["PCS sells at ₹260.00, above its MRP of ₹250.00."]


@pytest.mark.django_db
def test_a_stock_unit_price_above_its_mrp_warns_on_edit(client, signed_in, item):
    response = client.post(
        edit_url(item), submitted(selling_price="1500", mrp="1450"), follow=True
    )

    assert item.stock_unit.selling_price == Decimal(1500)
    assert warnings(response) == ["NOS sells at ₹1500.00, above its MRP of ₹1450.00."]


@pytest.mark.django_db
def test_a_worked_out_price_above_the_mrp_warns(client, signed_in):
    response = client.post(
        RECORD,
        submitted({"code": "PCS", "rate": "20", "mrp": "230"}, **PIPE),
        follow=True,
    )

    assert warnings(response) == ["PCS sells at ₹240.00, above its MRP of ₹230.00."]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("price", "mrp"), [("1450", "1450"), ("1400", "1450"), ("1450", "")]
)
def test_a_price_at_or_below_the_mrp_or_without_one_gives_no_warning(
    client, signed_in, price, mrp
):
    response = client.post(RECORD, submitted(selling_price=price, mrp=mrp), follow=True)

    assert Item.objects.exists()
    assert warnings(response) == []


@pytest.mark.django_db
def test_an_mrp_without_a_price_gives_no_warning(client, signed_in):
    response = client.post(RECORD, submitted(selling_price="", mrp="10"), follow=True)

    assert warnings(response) == []


@pytest.mark.django_db
def test_the_edit_form_shows_the_mrp_on_file(client, signed_in, item):
    item.units.update(mrp=Decimal(1500))

    form = client.get(edit_url(item)).context["form"]

    assert form["mrp"].value() == Decimal(1500)


@pytest.mark.django_db
def test_the_detail_page_shows_each_units_mrp(client, signed_in, item):
    item.units.update(mrp=Decimal(1500))
    ItemUnit.objects.create(
        item=item, code="BOX", rate=Decimal(10), mrp=Decimal("15000.00")
    )

    page = client.get(detail_url(item)).content.decode()

    assert "MRP" in page
    assert "₹1500.00 per NOS" in page
    assert "₹15000.00 per BOX" in page


@pytest.mark.django_db
def test_the_detail_page_says_when_a_unit_has_no_mrp(client, signed_in, item):
    page = client.get(detail_url(item)).content.decode()

    assert "No MRP" in page


@pytest.mark.django_db
def test_a_change_to_an_mrp_is_in_the_history(client, signed_in, item):
    client.post(edit_url(item), submitted(mrp="1500"))

    latest = item.stock_unit.history.first()
    assert latest.mrp == Decimal(1500)
    assert latest.history_user == signed_in


@pytest.mark.django_db
def test_a_service_with_an_mrp_is_refused(client, signed_in):
    response = client.post(
        RECORD, submitted(kind="service", hsn_sac="995461", mrp="300")
    )

    assert "mrp" in response.context["form"].errors
    assert not Item.objects.exists()


@pytest.mark.django_db
def test_a_service_starts_with_the_mrp_hidden(client, signed_in):
    service = record(
        name="Tap fitting", kind=Item.Kind.SERVICE, hsn_sac="995461", price="300"
    )

    page = client.get(edit_url(service)).content.decode()

    assert '<div x-data="goodsOnly" x-show="applies" x-cloak' in page
