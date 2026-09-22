from decimal import Decimal

import pytest
from django.urls import reverse

from apps.purchases.models import Purchase
from tests.purchases.conftest import line, submitted

RECORD = reverse("record_purchase")


def bill(supplier, elbow, **changes):
    """One elbow at ₹860 and 18% GST, which billow totals to ₹1,014.80."""
    return submitted(supplier, line(elbow, quantity="1", rate="860"), **changes)


def detail(client, purchase):
    return client.get(reverse("purchase_detail", args=[purchase.pk])).content.decode()


@pytest.mark.django_db
def test_a_blank_round_off_takes_the_one_that_makes_a_whole_rupee(
    client, signed_in, supplier, elbow
):
    client.post(RECORD, bill(supplier, elbow, round_off="", billed_total="1015"))

    purchase = Purchase.objects.get()
    assert purchase.round_off == Decimal("0.20")
    assert purchase.totals().grand_total == Decimal("1015.00")


@pytest.mark.django_db
def test_the_round_off_is_recorded_as_the_supplier_rounded(
    client, signed_in, supplier, elbow
):
    client.post(RECORD, bill(supplier, elbow, round_off="-0.80", billed_total="1014"))

    purchase = Purchase.objects.get()
    assert purchase.round_off == Decimal("-0.80")
    assert purchase.totals().grand_total == Decimal("1014.00")


@pytest.mark.django_db
@pytest.mark.parametrize("round_off", ["1.01", "-1.01"])
def test_a_round_off_beyond_a_rupee_is_refused(
    client, signed_in, supplier, elbow, round_off
):
    response = client.post(RECORD, bill(supplier, elbow, round_off=round_off))

    assert response.status_code == 200
    assert "no more than ₹1.00 either way" in response.content.decode()
    assert not Purchase.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("round_off", ["1.00", "-1.00"])
def test_a_round_off_of_a_rupee_is_accepted(
    client, signed_in, supplier, elbow, round_off
):
    billed_total = Decimal("1014.80") + Decimal(round_off)
    client.post(
        RECORD,
        bill(supplier, elbow, round_off=round_off, billed_total=str(billed_total)),
    )

    assert Purchase.objects.get().round_off == Decimal(round_off)


@pytest.mark.django_db
def test_the_grand_total_on_the_bill_is_stored(client, signed_in, supplier, elbow):
    client.post(RECORD, bill(supplier, elbow, billed_total="1015.00"))

    assert Purchase.objects.get().billed_total == Decimal("1015.00")


@pytest.mark.django_db
def test_the_grand_total_on_the_bill_is_required(client, signed_in, supplier, elbow):
    response = client.post(RECORD, bill(supplier, elbow, billed_total=""))

    assert response.status_code == 200
    assert not Purchase.objects.exists()


@pytest.mark.django_db
def test_a_total_that_matches_saves_without_a_warning(
    client, signed_in, supplier, elbow
):
    response = client.post(RECORD, bill(supplier, elbow, billed_total="1015.00"))

    assert response.status_code == 302
    assert Purchase.objects.exists()


@pytest.mark.django_db
def test_a_total_that_differs_is_shown_and_not_yet_saved(
    client, signed_in, supplier, elbow
):
    response = client.post(RECORD, bill(supplier, elbow, billed_total="1000"))

    page = response.content.decode()
    assert response.status_code == 200
    assert "billow totals this bill to ₹1,015.00" in page
    assert "the bill says ₹1,000.00" in page
    assert "a difference of ₹15.00" in page
    assert not Purchase.objects.exists()


@pytest.mark.django_db
def test_a_total_that_differs_saves_once_confirmed(client, signed_in, supplier, elbow):
    response = client.post(
        RECORD,
        bill(supplier, elbow, billed_total="1000", confirmed_total="1000.00|1015.00"),
    )

    assert response.status_code == 302
    purchase = Purchase.objects.get()
    assert purchase.billed_total == Decimal("1000.00")
    assert purchase.totals().grand_total == Decimal("1015.00")


@pytest.mark.django_db
def test_a_confirmation_lapses_when_the_totals_change(
    client, signed_in, supplier, elbow
):
    response = client.post(
        RECORD,
        submitted(
            supplier,
            line(elbow, quantity="2", rate="860"),
            billed_total="1000",
            confirmed_total="1000.00|1015.00",
        ),
    )

    assert response.status_code == 200
    assert "billow totals this bill to ₹2,030.00" in response.content.decode()
    assert not Purchase.objects.exists()


@pytest.mark.django_db
def test_the_page_shows_the_round_off(client, signed_in, supplier, elbow):
    client.post(RECORD, bill(supplier, elbow, billed_total="1015"))

    page = detail(client, Purchase.objects.get())
    assert "Round-off" in page
    assert "₹0.20" in page
    assert "₹1,015.00" in page


@pytest.mark.django_db
def test_the_page_shows_a_bill_total_that_differs(client, signed_in, supplier, elbow):
    client.post(
        RECORD,
        bill(supplier, elbow, billed_total="1000", confirmed_total="1000.00|1015.00"),
    )

    page = detail(client, Purchase.objects.get())
    assert "Grand total on the bill" in page
    assert "₹1,000.00" in page


@pytest.mark.django_db
def test_the_page_leaves_out_a_bill_total_that_matches(
    client, signed_in, supplier, elbow
):
    client.post(RECORD, bill(supplier, elbow, billed_total="1015"))

    assert "Grand total on the bill" not in detail(client, Purchase.objects.get())
