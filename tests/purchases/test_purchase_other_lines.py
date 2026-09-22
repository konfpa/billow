"""Lines for a Service Item, and One-off lines for what the catalogue does not hold."""

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.catalogue.models import Item
from apps.purchases.models import Purchase
from tests.purchases.conftest import goods, line, submitted

RECORD = reverse("record_purchase")


def one_off(name="Freight", hsn_sac="996511", gst_rate="5.00", **fields):
    return {
        "name": name,
        "hsn_sac": hsn_sac,
        "gst_rate": gst_rate,
        "quantity": "1",
        "rate": "200.00",
        **fields,
    }


@pytest.fixture
def fitting(db):
    return goods("Fitting", "SVC-FIT", kind=Item.Kind.SERVICE)


def refused(response, message):
    assert response.status_code == 200
    assert message in response.content.decode()
    assert not Purchase.objects.exists()


@pytest.mark.django_db
def test_a_service_is_offered_as_a_line(client, signed_in, fitting):
    page = client.get(RECORD).content.decode()

    assert '"code": "SVC-FIT"' in page


@pytest.mark.django_db
def test_a_service_is_recorded_as_a_line(client, signed_in, supplier, fitting):
    response = client.post(RECORD, submitted(supplier, line(fitting)))

    assert response.status_code == 302
    assert Purchase.objects.get().lines.get().item == fitting


@pytest.mark.django_db
def test_a_one_off_line_is_recorded(client, signed_in, supplier, elbow):
    response = client.post(
        RECORD, submitted(supplier, line(elbow), one_off(), billed_total="1390")
    )

    assert response.status_code == 302
    freight = Purchase.objects.get().lines.get(item=None)
    assert (freight.name, freight.hsn_sac, freight.gst_rate) == (
        "Freight",
        "996511",
        Decimal("5.00"),
    )
    assert (freight.quantity, freight.rate) == (Decimal("1.000"), Decimal("200.00"))


@pytest.mark.django_db
def test_a_one_off_line_creates_no_item(client, signed_in, supplier, elbow):
    client.post(
        RECORD, submitted(supplier, line(elbow), one_off(), billed_total="1390")
    )

    assert list(Item.objects.all()) == [elbow]


@pytest.mark.django_db
def test_a_one_off_line_may_carry_an_hsn_code(client, signed_in, supplier):
    response = client.post(
        RECORD,
        submitted(
            supplier,
            one_off(name="Solvent cement", hsn_sac="35061000", gst_rate="18.00"),
            billed_total="236",
        ),
    )

    assert response.status_code == 302


@pytest.mark.django_db
def test_a_one_off_line_needs_a_name_a_code_and_a_gst_rate(client, signed_in, supplier):
    response = client.post(
        RECORD, submitted(supplier, one_off(name="", hsn_sac="", gst_rate=""))
    )

    page = response.content.decode()
    assert "Line 1, name" in page
    assert "Line 1, hsn or sac" in page
    assert "Line 1, gst" in page
    assert not Purchase.objects.exists()


@pytest.mark.django_db
def test_a_one_off_line_code_is_validated_as_for_items(client, signed_in, supplier):
    response = client.post(RECORD, submitted(supplier, one_off(hsn_sac="12345")))

    refused(response, "An HSN code is 4, 6 or 8 digits, and a SAC is 6 digits")


@pytest.mark.django_db
def test_a_line_is_never_both_an_item_and_a_one_off(client, signed_in, supplier, elbow):
    response = client.post(
        RECORD, submitted(supplier, {**line(elbow), "name": "Freight"})
    )

    refused(response, "A line is either an Item or a One-off line, never both.")


@pytest.mark.django_db
def test_service_and_one_off_lines_are_taxed_by_gst_rate(
    client, signed_in, supplier, elbow, fitting
):
    # Elbows 1,000 and fitting 500 at 18%, freight 200 at 5%.
    client.post(
        RECORD,
        submitted(
            supplier,
            line(elbow),
            line(fitting, quantity="1", rate="500.00"),
            one_off(),
            billed_total="1980",
        ),
    )

    purchase = Purchase.objects.get()
    totals = purchase.totals()
    assert [(rate.gst_rate, rate.taxable_value) for rate in totals.by_rate] == [
        (Decimal("5.00"), Decimal("200.00")),
        (Decimal("18.00"), Decimal("1500.00")),
    ]
    assert totals.grand_total == Decimal("1980.00")
    assert purchase.billed_total == totals.grand_total


@pytest.mark.django_db
def test_only_goods_lines_move_stock(client, signed_in, supplier, elbow, fitting):
    client.post(
        RECORD,
        submitted(
            supplier,
            line(elbow),
            line(fitting, quantity="1", rate="500.00"),
            one_off(),
            billed_total="1980",
        ),
    )

    lines = Purchase.objects.get().totals().lines
    assert [line.moves_stock for line in lines] == [True, False, False]


@pytest.mark.django_db
def test_the_detail_page_shows_a_one_off_line(client, signed_in, supplier, elbow):
    client.post(
        RECORD, submitted(supplier, line(elbow), one_off(), billed_total="1390")
    )

    purchase = Purchase.objects.get()
    page = client.get(reverse("purchase_detail", args=[purchase.pk])).content.decode()

    assert "Freight" in page
    assert "996511" in page
    assert "₹1,390.00" in page


@pytest.mark.django_db
def test_a_refused_one_off_line_keeps_what_was_typed(client, signed_in, supplier):
    response = client.post(
        RECORD, submitted(supplier, one_off(name="Loading", quantity="0"))
    )

    page = response.content.decode()
    assert 'value="Loading"' in page
    assert 'value="996511"' in page


@pytest.mark.django_db
def test_an_item_with_a_code_of_its_own_is_never_both(
    client, signed_in, supplier, elbow
):
    response = client.post(
        RECORD, submitted(supplier, {**line(elbow), "hsn_sac": "996511"})
    )

    refused(response, "A line is either an Item or a One-off line, never both.")
