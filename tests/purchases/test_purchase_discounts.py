from decimal import Decimal

import pytest
from django.urls import reverse

from apps.purchases.models import Purchase
from tests.purchases.conftest import line, submitted

RECORD = reverse("record_purchase")


def detail(client, purchase):
    return client.get(reverse("purchase_detail", args=[purchase.pk])).content.decode()


@pytest.mark.django_db
def test_discounts_are_recorded_as_printed(client, signed_in, supplier, elbow, pipe):
    client.post(
        RECORD,
        submitted(
            supplier,
            line(elbow, quantity="1", rate="600"),
            line(pipe, quantity="1", rate="500", discount_percent="20"),
            bill_discount="100",
            billed_total="1015",
        ),
    )

    purchase = Purchase.objects.get()
    assert purchase.bill_discount == Decimal("100.00")
    assert [recorded.discount_percent for recorded in purchase.lines.all()] == [
        Decimal("0.00"),
        Decimal("20.00"),
    ]
    assert purchase.totals().grand_total == Decimal("1015.00")


@pytest.mark.django_db
def test_both_discounts_are_optional(client, signed_in, supplier, elbow):
    client.post(RECORD, submitted(supplier, line(elbow), bill_discount=""))

    purchase = Purchase.objects.get()
    assert purchase.bill_discount == Decimal("0.00")
    assert purchase.lines.get().discount_percent == Decimal("0.00")


@pytest.mark.django_db
@pytest.mark.parametrize("discount", ["-5", "100.01"])
def test_a_line_discount_is_between_nothing_and_all_of_it(
    client, signed_in, supplier, elbow, discount
):
    response = client.post(
        RECORD, submitted(supplier, line(elbow, discount_percent=discount))
    )

    assert response.status_code == 200
    assert not Purchase.objects.exists()


@pytest.mark.django_db
def test_a_negative_bill_discount_is_refused(client, signed_in, supplier, elbow):
    response = client.post(
        RECORD, submitted(supplier, line(elbow), bill_discount="-10")
    )

    assert response.status_code == 200
    assert not Purchase.objects.exists()


@pytest.mark.django_db
def test_a_bill_discount_beyond_the_lines_is_refused(
    client, signed_in, supplier, elbow
):
    response = client.post(
        RECORD,
        submitted(
            supplier,
            line(elbow, quantity="10", rate="100", discount_percent="10"),
            bill_discount="900.01",
        ),
    )

    assert response.status_code == 200
    assert "more than the lines come to after their own discounts, ₹900.00" in (
        response.content.decode()
    )
    assert not Purchase.objects.exists()


@pytest.mark.django_db
def test_the_page_shows_the_discounts(client, signed_in, supplier, elbow, pipe):
    client.post(
        RECORD,
        submitted(
            supplier,
            line(elbow, quantity="1", rate="600"),
            line(pipe, quantity="1", rate="500", discount_percent="20"),
            bill_discount="100",
            billed_total="1015",
        ),
    )

    page = detail(client, Purchase.objects.get())

    assert ">20%</td>" in page
    assert "Bill discount" in page
    assert "\N{MINUS SIGN}₹100.00" in page
    assert "₹900.00" in page
    assert "₹1,015.00" in page


@pytest.mark.django_db
def test_the_page_leaves_out_a_bill_discount_not_given(
    client, signed_in, supplier, elbow
):
    client.post(RECORD, submitted(supplier, line(elbow)))

    assert "Bill discount" not in detail(client, Purchase.objects.get())
