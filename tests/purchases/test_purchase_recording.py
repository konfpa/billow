import datetime
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.purchases.models import Purchase
from tests.purchases.conftest import BILL_DATE, goods, line, submitted

RECORD = reverse("record_purchase")


def detail_url(purchase):
    return reverse("purchase_detail", args=[purchase.pk])


@pytest.mark.django_db
def test_a_purchase_is_recorded_and_lands_on_its_page(
    client, signed_in, supplier, elbow, pipe
):
    response = client.post(
        RECORD,
        submitted(supplier, line(elbow), line(pipe, quantity="3", rate="410.00")),
    )

    purchase = Purchase.objects.get()
    assert response.status_code == 302
    assert response.url == detail_url(purchase)
    assert purchase.supplier == supplier
    assert purchase.bill_number == "MP/2026-27/0412"
    assert purchase.bill_date == BILL_DATE
    assert [(line.item, line.quantity, line.rate) for line in purchase.lines.all()] == [
        (elbow, Decimal("10.000"), Decimal("100.00")),
        (pipe, Decimal("3.000"), Decimal("410.00")),
    ]


@pytest.mark.django_db
def test_the_new_purchase_page_offers_a_first_line(client, signed_in):
    page = client.get(RECORD).content.decode()

    assert 'name="lines-TOTAL_FORMS"' in page
    assert 'name="lines-0-item"' in page


@pytest.mark.django_db
def test_a_purchase_without_lines_is_refused(client, signed_in, supplier):
    response = client.post(RECORD, submitted(supplier))

    assert response.status_code == 200
    assert "Add at least one line" in response.content.decode()
    assert not Purchase.objects.exists()


@pytest.mark.django_db
def test_a_blank_line_is_passed_over(client, signed_in, supplier, elbow):
    client.post(RECORD, submitted(supplier, line(elbow), {}))

    assert Purchase.objects.get().lines.count() == 1


@pytest.mark.django_db
def test_a_removed_line_is_not_recorded(client, signed_in, supplier, elbow, pipe):
    client.post(RECORD, submitted(supplier, line(elbow), line(pipe, DELETE="on")))

    assert [line.item for line in Purchase.objects.get().lines.all()] == [elbow]


@pytest.mark.django_db
def test_the_supplier_bill_number_and_bill_date_are_required(
    client, signed_in, supplier, elbow
):
    response = client.post(
        RECORD,
        {
            **submitted(supplier, line(elbow)),
            "supplier": "",
            "bill_number": "",
            "bill_date": "",
        },
    )

    page = response.content.decode()
    assert response.status_code == 200
    assert ">3</span> fields need attention" in page
    assert not Purchase.objects.exists()


@pytest.mark.django_db
def test_the_received_date_defaults_to_the_bill_date(
    client, signed_in, supplier, elbow
):
    client.post(RECORD, submitted(supplier, line(elbow), received_date=""))

    assert Purchase.objects.get().received_date == BILL_DATE


@pytest.mark.django_db
def test_the_received_date_can_differ_from_the_bill_date(
    client, signed_in, supplier, elbow
):
    client.post(RECORD, submitted(supplier, line(elbow), received_date="2026-09-21"))

    assert Purchase.objects.get().received_date == datetime.date(2026, 9, 21)


@pytest.mark.django_db
def test_a_line_takes_the_item_gst_rate_by_default(client, signed_in, supplier, pipe):
    client.post(RECORD, submitted(supplier, line(pipe, gst_rate="")))

    assert Purchase.objects.get().lines.get().gst_rate == Decimal("5.00")


@pytest.mark.django_db
def test_a_line_gst_rate_can_be_changed(client, signed_in, supplier, pipe):
    client.post(RECORD, submitted(supplier, line(pipe, gst_rate="18.00")))

    assert Purchase.objects.get().lines.get().gst_rate == Decimal("18.00")


@pytest.mark.django_db
def test_a_line_may_be_in_any_unit_of_the_item(client, signed_in, supplier, pipe):
    client.post(RECORD, submitted(supplier, line(pipe, unit="BDL", quantity="2")))

    recorded = Purchase.objects.get().lines.get()
    assert recorded.unit == "BDL"
    assert recorded.stock_units_in_one == Decimal(20)


@pytest.mark.django_db
def test_a_unit_the_item_is_not_in_is_refused(client, signed_in, supplier, elbow):
    response = client.post(RECORD, submitted(supplier, line(elbow, unit="BDL")))

    assert "Choose one of the units CPVC elbow ¾ inch is in." in (
        response.content.decode()
    )
    assert not Purchase.objects.exists()


@pytest.mark.parametrize("quantity", ["0", "-2"])
@pytest.mark.django_db
def test_a_quantity_of_zero_or_less_is_refused(
    client, signed_in, supplier, elbow, quantity
):
    response = client.post(RECORD, submitted(supplier, line(elbow, quantity=quantity)))

    assert "A quantity is more than zero." in response.content.decode()
    assert not Purchase.objects.exists()


@pytest.mark.django_db
def test_a_line_at_no_charge_is_accepted(client, signed_in, supplier, elbow):
    client.post(RECORD, submitted(supplier, line(elbow, quantity="1", rate="0")))

    assert Purchase.objects.get().lines.get().rate == Decimal("0.00")


@pytest.mark.django_db
def test_an_archived_supplier_cannot_be_chosen(client, signed_in, supplier, elbow):
    supplier.archive()

    page = client.get(RECORD).content.decode()
    response = client.post(RECORD, submitted(supplier, line(elbow)))

    assert "Mehta Pipes" not in page
    assert response.status_code == 200
    assert not Purchase.objects.exists()


@pytest.mark.django_db
def test_an_archived_item_cannot_be_chosen(client, signed_in, supplier, elbow):
    elbow.archive()

    page = client.get(RECORD).content.decode()
    response = client.post(RECORD, submitted(supplier, line(elbow)))

    assert "ELB-075" not in page
    assert "Choose Goods on file from the list." in response.content.decode()
    assert not Purchase.objects.exists()


@pytest.mark.django_db
def test_a_service_cannot_be_chosen_as_goods(client, signed_in, supplier):
    fitting = goods("Fitting", "SVC-FIT", kind="service")

    page = client.get(RECORD).content.decode()
    client.post(RECORD, submitted(supplier, line(fitting)))

    assert "SVC-FIT" not in page
    assert not Purchase.objects.exists()


@pytest.mark.django_db
def test_the_item_picker_searches_name_code_and_brand(client, signed_in, elbow):
    page = client.get(RECORD).content.decode()

    for fragment in ('"name": "CPVC elbow', '"code": "ELB-075"', '"brand": "Astral"'):
        assert fragment in page


@pytest.mark.django_db
def test_the_supplier_gstin_and_state_are_copied_onto_the_purchase(
    client, signed_in, supplier, elbow
):
    client.post(RECORD, submitted(supplier, line(elbow)))

    purchase = Purchase.objects.get()
    assert purchase.supplier_gstin == "27AAACM1234K1ZN"
    assert purchase.supplier_state == "27"


@pytest.mark.django_db
def test_a_refused_purchase_keeps_what_was_typed(client, signed_in, supplier, elbow):
    response = client.post(
        RECORD, submitted(supplier, line(elbow, quantity="0"), bill_number="X-9")
    )

    page = response.content.decode()
    assert 'value="X-9"' in page
    assert "CPVC elbow ¾ inch" in page
